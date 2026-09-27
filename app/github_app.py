"""Client GitHub App : JWT d'application, tokens d'installation, issues, PR (git data API)."""

import io
import tarfile
import time
from pathlib import Path

import httpx
import jwt

API = "https://api.github.com"


class GitHubAppError(Exception):
    pass


class GitHubApp:
    def __init__(self, app_id: int, private_key: str, transport: httpx.AsyncClient | None = None):
        self.app_id = int(app_id)
        self.private_key = private_key
        self.transport = transport or httpx.AsyncClient(timeout=30.0)

    # --- Auth ---

    def app_token(self) -> str:
        now = int(time.time())
        payload = {"iat": now - 60, "exp": now + 540, "iss": str(self.app_id)}
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    async def installation_token(self, installation_id: int) -> str:
        headers = {
            "Authorization": f"Bearer {self.app_token()}",
            "Accept": "application/vnd.github+json",
        }
        r = await self.transport.post(
            f"{API}/app/installations/{installation_id}/access_tokens", headers=headers
        )
        if r.status_code != 201:
            raise GitHubAppError(f"Échec du token d'installation : {r.status_code}")
        return r.json()["token"]

    async def _headers(self, installation_id: int) -> dict:
        token = await self.installation_token(installation_id)
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }

    # --- Contenu du repo ---

    async def download_repo(
        self, installation_id: int, owner: str, repo: str, branch: str, dest_dir: Path
    ):
        headers = await self._headers(installation_id)
        url = f"{API}/repos/{owner}/{repo}/tarball/{branch}"
        r = await self.transport.get(url, headers=headers, follow_redirects=True)
        if r.status_code != 200:
            raise GitHubAppError(f"Téléchargement du repo impossible : {r.status_code}")
        with tarfile.open(fileobj=io.BytesIO(r.content), mode="r:gz") as tar:
            members = [m for m in tar.getmembers() if m.isfile()]
            root_prefix = members[0].name.split("/")[0] + "/"
            for member in members:
                rel = member.name[len(root_prefix):]
                if not rel:
                    continue
                target = dest_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                fobj = tar.extractfile(member)
                if fobj is None:
                    continue
                target.write_bytes(fobj.read())
        return dest_dir

    async def get_default_branch(self, installation_id: int, owner: str, repo: str) -> str:
        headers = await self._headers(installation_id)
        r = await self.transport.get(f"{API}/repos/{owner}/{repo}", headers=headers)
        if r.status_code != 200:
            raise GitHubAppError(f"Repo introuvable : {r.status_code}")
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
            raise GitHubAppError(f"Création d'issue impossible : {r.status_code}")
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
            raise GitHubAppError(f"Branche introuvable : {ref.status_code}")
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
                raise GitHubAppError(f"Création de blob impossible : {blob.status_code}")
            blobs.append({"path": path, "sha": blob.json()["sha"], "mode": "100644", "type": "blob"})

        tree = await self.transport.post(
            f"{API}/repos/{owner}/{repo}/git/trees",
            headers=headers,
            json={"base_tree": tree_sha, "tree": blobs},
        )
        if tree.status_code != 201:
            raise GitHubAppError(f"Création d'arbre impossible : {tree.status_code}")

        commit = await self.transport.post(
            f"{API}/repos/{owner}/{repo}/git/commits",
            headers=headers,
            json={
                "message": f"🛡️ DriftGuard : {title}",
                "tree": tree.json()["sha"],
                "parents": [base_sha],
            },
        )
        if commit.status_code != 201:
            raise GitHubAppError(f"Création de commit impossible : {commit.status_code}")

        branch_name = f"driftguard/fixes-{int(time.time())}"
        new_ref = await self.transport.post(
            f"{API}/repos/{owner}/{repo}/git/refs",
            headers=headers,
            json={"ref": f"refs/heads/{branch_name}", "sha": commit.json()["sha"]},
        )
        if new_ref.status_code != 201:
            raise GitHubAppError(f"Création de branche impossible : {new_ref.status_code}")

        pr = await self.transport.post(
            f"{API}/repos/{owner}/{repo}/pulls",
            headers=headers,
            json={"title": f"🛡️ {title}", "body": body, "head": branch_name, "base": base_branch},
        )
        if pr.status_code != 201:
            raise GitHubAppError(f"Création de PR impossible : {pr.status_code}")
        return pr.json()
