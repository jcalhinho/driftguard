"""Service FastAPI DriftGuard : webhook GitHub → scan → issue/PR."""

import hashlib
import hmac
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from engine.rules import load_rules

from . import storage
from .github_app import GitHubApp, GitHubAppError
from .pipeline import run_scan_pipeline

app = FastAPI(title="DriftGuard", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RULES_FILE = Path(os.getenv("DRIFTGUARD_RULES", str(Path(__file__).resolve().parents[1] / "rules" / "rules.yaml")))

_rules = None
_gh_app: GitHubApp | None = None


def get_rules():
    global _rules
    if _rules is None:
        _rules = load_rules(RULES_FILE)
    return _rules


def get_github_app() -> GitHubApp:
    global _gh_app
    if _gh_app is None:
        app_id = os.getenv("GITHUB_APP_ID", "")
        key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH", "")
        if not app_id or not key_path:
            raise HTTPException(
                status_code=500,
                detail="GITHUB_APP_ID / GITHUB_APP_PRIVATE_KEY_PATH non configurés.",
            )
        _gh_app = GitHubApp(int(app_id), Path(key_path).read_text())
    return _gh_app


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.removeprefix("sha256="))


@app.get("/health")
async def health():
    return {"status": "ok", "rules": len(get_rules())}


@app.post("/webhook")
async def webhook(request: Request):
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    body = await request.body()
    if secret and not verify_signature(
        body, request.headers.get("x-hub-signature-256", ""), secret
    ):
        raise HTTPException(status_code=401, detail="Signature invalide.")
    if request.headers.get("x-github-event") == "ping":
        return {"ok": True}

    payload = await request.json()
    event = request.headers.get("x-github-event", "")

    if event == "installation":
        action = payload.get("action", "")
        installation = payload.get("installation", {})
        account = (installation.get("account") or {}).get("login", "?")
        if action in ("created", "suspend", "unsuspend"):
            storage.save_installation(int(installation.get("id", 0)), account)
        return {"ok": True}

    if event in ("push", "pull_request"):
        installation_id = int((payload.get("installation") or {}).get("id", 0))
        repo_data = payload.get("repository") or {}
        owner = (repo_data.get("owner") or {}).get("login", "")
        repo = repo_data.get("name", "")
        if not installation_id or not owner or not repo:
            return {"ok": True, "skipped": "infos manquantes"}
        gh = get_github_app()
        try:
            result = await run_scan_pipeline(
                gh, get_rules(), installation_id, owner, repo
            )
        except GitHubAppError as e:
            raise HTTPException(status_code=502, detail=str(e))
        return {"ok": True, **result}

    return {"ok": True, "skipped": event}
