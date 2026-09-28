"""GitHub App client: app JWT, installation tokens, issues, PRs (git data API)."""

import asyncio
import tarfile
import tempfile
import time
from datetime import datetime
from pathlib import Path

import httpx
import jwt

API = "https://api.github.com"

MAX_TARBALL_BYTES = 200 * 1024 * 1024  # compressed download
MAX_EXTRACTED_BYTES = 500 * 1024 * 1024  # uncompressed, guards against tar bombs
TOKEN_REFRESH_MARGIN = 300  # seconds before expiry


class GitHubAppError(Exception):
    pass


class GitHubApp:
    def __init__(self, app_id: int, private_key: str, transport: httpx.AsyncClient | None = None):
        self.app_id = int(app_id)
        self.private_key = private_key
        self.transport = transport or httpx.AsyncClient(timeout=60.0)
        self._tokens: dict[int, tuple[str, float]] = {}

    # --- Auth ---

    def app_token(self) -> str:
        now = int(time.time())
        payload = {"iat": now - 60, "exp": now + 540, "iss": str(self.app_id)}
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    async def installation_token(self, installation_id: int) -> str:
        """Installation tokens live 1 h: reuse them instead of minting one per call."""
        cached = self._tokens.get(installation_id)
        if cached and cached[1] - TOKEN_REFRESH_MARGIN > time.time():
            return cached[0]
        headers = {
            "Authorization": f"Bearer {self.app_token()}",
            "Accept": "application/vnd.github+json",
        }
        r = await self.transport.post(
            f"{API}/app/installations/{installation_id}/access_tokens", headers=headers
        )
        if r.status_code != 201:
            raise GitHubAppError(f"Failed to get installation token: {r.status_code}")
        data = r.json()
        try:
            expires = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00")).timestamp()
        except (KeyError, ValueError):
            expires = time.time() + 3600
        self._tokens[installation_id] = (data["token"], expires)
        return data["token"]

    async def _headers(self, installation_id: int) -> dict:
        token = await self.installation_token(installation_id)
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }

    # --- Repo content ---

    async def download_repo(
        self, installation_id: int, owner: str, repo: str, branch: str, dest_dir: Path
    ):
        headers = await self._headers(installation_id)
        url = f"{API}/repos/{owner}/{repo}/tarball/{branch}"
        with tempfile.TemporaryFile() as archive:
            size = 0
            async with self.transport.stream(
                "GET", url, headers=headers, follow_redirects=True
            ) as r:
                if r.status_code != 200:
                    raise GitHubAppError(f"Failed to download repo: {r.status_code}")
                async for chunk in r.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_TARBALL_BYTES:
                        raise GitHubAppError("Repository too large to scan")
                    archive.write(chunk)
            archive.seek(0)
            await asyncio.to_thread(_extract_tarball, archive, Path(dest_dir))
        return dest_dir

    async def get_default_branch(self, installation_id: int, owner: str, repo: str) -> str:
        headers = await self._headers(installation_id)
        r = await self.transport.get(f"{API}/repos/{owner}/{repo}", headers=headers)
        if r.status_code != 200:
            raise GitHubAppError(f"Repo not found: {r.status_code}")
        return r.json().get("default_branch", "main")

    # --- Issues ---

    async def create_issue(
        self, installation_id: int, owner: str, repo: str, title: str, body: str
    ) -> dict:
        headers = await self._headers(installation_id)
        r = await self.transport.post(
            f"{API}/repos/{owner}/{repo}/issues",
            headers=headers,
            json={"title": title, "body": body, "labels": ["driftguard"]},
        )
        if r.status_code not in (200, 201):
            raise GitHubAppError(f"Failed to create issue: {r.status_code}")
        return r.json()

    # --- Pull requests (via git data API) ---

    async def create_pr(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        base_branch: str,
        changes: list[tuple[str, str]],
        title: str,
        body: str,
    ) -> dict:
        headers = await self._headers(installation_id)

        ref = await self.transport.get(
            f"{API}/repos/{owner}/{repo}/git/ref/heads/{base_branch}", headers=headers
        )
        if ref.status_code != 200:
            raise GitHubAppError(f"Branch not found: {ref.status_code}")
        base_sha = ref.json()["object"]["sha"]
        tree_sha = base_sha

        blobs = []
        for path, content in changes:
            blob = await self.transport.post(
                f"{API}/repos/{owner}/{repo}/git/blobs",
                headers=headers,
                json={"content": content, "encoding": "utf-8"},
            )
            if blob.status_code != 201:
                raise GitHubAppError(f"Failed to create blob: {blob.status_code}")
            blobs.append({"path": path, "sha": blob.json()["sha"], "mode": "100644", "type": "blob"})

        tree = await self.transport.post(
            f"{API}/repos/{owner}/{repo}/git/trees",
            headers=headers,
            json={"base_tree": tree_sha, "tree": blobs},
        )
        if tree.status_code != 201:
            raise GitHubAppError(f"Failed to create tree: {tree.status_code}")

        commit = await self.transport.post(
            f"{API}/repos/{owner}/{repo}/git/commits",
            headers=headers,
            json={
                "message": f"🛡️ DriftGuard: {title}",
                "tree": tree.json()["sha"],
                "parents": [base_sha],
            },
        )
        if commit.status_code != 201:
            raise GitHubAppError(f"Failed to create commit: {commit.status_code}")

        branch_name = f"driftguard/fixes-{int(time.time())}"
        new_ref = await self.transport.post(
            f"{API}/repos/{owner}/{repo}/git/refs",
            headers=headers,
            json={"ref": f"refs/heads/{branch_name}", "sha": commit.json()["sha"]},
        )
        if new_ref.status_code != 201:
            raise GitHubAppError(f"Failed to create branch: {new_ref.status_code}")

        pr = await self.transport.post(
            f"{API}/repos/{owner}/{repo}/pulls",
            headers=headers,
            json={"title": f"🛡️ {title}", "body": body, "head": branch_name, "base": base_branch},
        )
        if pr.status_code != 201:
            raise GitHubAppError(f"Failed to create PR: {pr.status_code}")
        return pr.json()


def _extract_tarball(fileobj, dest_dir: Path):
    """Extract regular files only, stripping GitHub's top-level folder.

    Rejects paths escaping dest_dir and stops past MAX_EXTRACTED_BYTES.
    """
    dest_dir = dest_dir.resolve()
    total = 0
    with tarfile.open(fileobj=fileobj, mode="r:gz") as tar:
        for member in tar:
            if not member.isfile():
                continue  # symlinks, devices, dirs: never materialized
            _, _, rel = member.name.partition("/")
            if not rel:
                continue
            target = (dest_dir / rel).resolve()
            if not target.is_relative_to(dest_dir):
                continue
            total += member.size
            if total > MAX_EXTRACTED_BYTES:
                raise GitHubAppError("Repository too large to scan")
            fobj = tar.extractfile(member)
            if fobj is None:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with fobj, open(target, "wb") as out:
                while chunk := fobj.read(1024 * 1024):
                    out.write(chunk)
