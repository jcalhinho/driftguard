"""DriftGuard FastAPI service: GitHub webhook → scan → issue/PR."""

import asyncio
import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from driftguard.rules import DEFAULT_RULES_FILE, load_rules

from . import storage
from .github_app import GitHubApp, GitHubAppError
from .pipeline import run_scan_pipeline

logging.basicConfig(
    level=os.getenv("DRIFTGUARD_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("driftguard")

app = FastAPI(title="DriftGuard", version="0.2.0")

RULES_FILE = Path(os.getenv("DRIFTGUARD_RULES", str(DEFAULT_RULES_FILE)))

_rules = None
_rules_day = None
_gh_app: GitHubApp | None = None


def get_rules():
    """Reloaded once a day: rules whose shutdown date has passed escalate to critical."""
    global _rules, _rules_day
    today = datetime.now(timezone.utc).date()
    if _rules is None or _rules_day != today:
        _rules, _rules_day = load_rules(RULES_FILE, today=today), today
    return _rules


def get_github_app() -> GitHubApp:
    global _gh_app
    if _gh_app is None:
        app_id = os.getenv("GITHUB_APP_ID", "")
        key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH", "")
        if not app_id or not key_path:
            raise HTTPException(
                status_code=500,
                detail="GITHUB_APP_ID / GITHUB_APP_PRIVATE_KEY_PATH are not configured.",
            )
        _gh_app = GitHubApp(int(app_id), Path(key_path).read_text())
    return _gh_app


# One scan at a time per repo: two quick pushes must not open two identical issues.
_repo_locks: dict[str, asyncio.Lock] = {}


async def scan_in_background(
    installation_id: int, owner: str, repo: str, branch: str | None = None
):
    lock = _repo_locks.setdefault(f"{owner}/{repo}", asyncio.Lock())
    async with lock:
        try:
            result = await run_scan_pipeline(
                get_github_app(), get_rules(), installation_id, owner, repo, branch
            )
            log.info("scan %s/%s: %s", owner, repo, result)
        except GitHubAppError as e:
            log.warning("scan %s/%s failed: %s", owner, repo, e)
        except Exception:
            log.exception("scan %s/%s crashed", owner, repo)


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.removeprefix("sha256="))


@app.get("/health")
async def health():
    return {"status": "ok", "rules": len(get_rules())}


def _queued(scans: int) -> JSONResponse:
    return JSONResponse({"ok": True, "queued": scans}, status_code=202)


@app.post("/webhook")
async def webhook(request: Request, tasks: BackgroundTasks):
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if not secret:
        # Fail closed: without a secret, anyone could forge push events.
        raise HTTPException(status_code=503, detail="GITHUB_WEBHOOK_SECRET is not configured.")
    body = await request.body()
    if not verify_signature(
        body, request.headers.get("x-hub-signature-256", ""), secret
    ):
        raise HTTPException(status_code=401, detail="Invalid signature.")
    event = request.headers.get("x-github-event", "")
    if event == "ping":
        return {"ok": True}

    payload = await request.json()
    installation = payload.get("installation") or {}
    installation_id = int(installation.get("id", 0))
    action = payload.get("action", "")

    if event == "installation":
        account = (installation.get("account") or {}).get("login", "")
        if action == "deleted":
            storage.delete_installation(installation_id)
            return {"ok": True}
        if action != "created":
            return {"ok": True, "skipped": f"installation.{action}"}
        storage.save_installation(installation_id, account)
        # First impression: scan every repo right away instead of waiting for a push.
        return _schedule_repos(tasks, installation_id, payload.get("repositories") or [])

    if event == "installation_repositories":
        if action != "added":
            return {"ok": True, "skipped": f"installation_repositories.{action}"}
        return _schedule_repos(tasks, installation_id, payload.get("repositories_added") or [])

    if event == "push":
        repo_data = payload.get("repository") or {}
        owner = (repo_data.get("owner") or {}).get("login", "")
        repo = repo_data.get("name", "")
        branch = repo_data.get("default_branch", "")
        if not installation_id or not owner or not repo:
            return {"ok": True, "skipped": "missing repository info"}
        # Only the default branch is scanned; feature branches (and DriftGuard's own
        # fix branches) would only produce noise.
        if payload.get("deleted") or payload.get("ref") != f"refs/heads/{branch}":
            return {"ok": True, "skipped": "not the default branch"}
        get_github_app()  # surface misconfiguration in the webhook delivery log
        tasks.add_task(scan_in_background, installation_id, owner, repo, branch)
        return _queued(1)

    return {"ok": True, "skipped": event}


def _schedule_repos(tasks: BackgroundTasks, installation_id: int, repos: list) -> JSONResponse:
    get_github_app()
    count = 0
    for r in repos:
        owner, _, name = (r.get("full_name") or "").partition("/")
        if owner and name:
            tasks.add_task(scan_in_background, installation_id, owner, name)
            count += 1
    return _queued(count)
