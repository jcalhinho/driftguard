"""Tests de la GitHub App : signature webhook, config repo, pipeline complet (mocké)."""

from pathlib import Path

import pytest

from app.config import RepoConfig, filter_findings, load_repo_config
from app.github_app import GitHubApp
from app.main import verify_signature
from app.pipeline import apply_fixes, run_scan_pipeline
from driftguard.rules import load_rules
from driftguard.scanner import scan_repo

ROOT = Path(__file__).resolve().parents[1]
RULES_FILE = ROOT / "driftguard" / "data" / "rules.yaml"
FIXTURE = ROOT / "tests" / "fixtures" / "sample_repo"


# ---------- Signature webhook ----------

def test_verify_signature_ok():
    import hashlib
    import hmac
    secret = "top-secret"
    body = b'{"action": "created"}'
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_signature(body, sig, secret) is True


def test_verify_signature_bad():
    assert verify_signature(b"body", "sha256=deadbeef", "secret") is False
    assert verify_signature(b"body", "", "secret") is False


# ---------- JWT d'application ----------

def test_app_token_rs256(tmp_path):
    import jwt as pyjwt
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    app = GitHubApp(app_id=42, private_key=pem)
    token = app.app_token()
    payload = pyjwt.decode(token, key.public_key(), algorithms=["RS256"])
    assert payload["iss"] == "42"


# ---------- Configuration repo ----------

def test_default_config(tmp_path):
    cfg = load_repo_config(tmp_path)
    assert cfg.mode == "issue"
    assert cfg.min_severity == "warning"


def test_custom_config(tmp_path):
    (tmp_path / ".driftguard.yml").write_text(
        "mode: pr\nmin_severity: critical\nignore_rules: [slack-legacy-tokens]\n",
        encoding="utf-8",
    )
    cfg = load_repo_config(tmp_path)
    assert cfg.mode == "pr"
    assert cfg.min_severity == "critical"
    assert cfg.ignore_rules == ["slack-legacy-tokens"]


def test_filter_findings():
    rules = load_rules(RULES_FILE)
    findings, _ = scan_repo(FIXTURE, rules)
    cfg = RepoConfig(mode="issue", min_severity="critical")
    filtered = filter_findings(findings, cfg)
    assert all(f.rule.severity == "critical" for f in filtered)
    assert len(filtered) == 6


# ---------- Pipeline (GitHub mocké) ----------

class FakeGitHubApp:
    def __init__(self, repo_dir):
        self.repo_dir = repo_dir
        self.issues = []
        self.prs = []

    async def get_default_branch(self, *args):
        return "main"

    async def download_repo(self, installation_id, owner, repo, branch, dest_dir):
        import shutil
        shutil.copytree(self.repo_dir, dest_dir, dirs_exist_ok=True)
        return dest_dir

    async def create_issue(self, installation_id, owner, repo, title, body):
        self.issues.append({"title": title, "body": body})
        return {"number": len(self.issues)}

    async def create_pr(self, installation_id, owner, repo, base, changes, title, body):
        self.prs.append({"title": title, "body": body, "changes": changes})
        return {"number": len(self.prs)}


def test_pipeline_issue_mode(tmp_path, monkeypatch):
    from app import storage
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.sqlite")
    rules = load_rules(RULES_FILE)
    fake = FakeGitHubApp(FIXTURE)
    result = pytest.importorskip("asyncio").run(
        run_scan_pipeline(fake, rules, 1, "owner", "repo")
    )
    assert result["status"] == "issue_opened"
    assert result["findings"] == 8
    assert len(fake.issues) == 1
    assert "DriftGuard" in fake.issues[0]["body"]
    assert "stripe.charges.create" in fake.issues[0]["body"]


def test_pipeline_dedup(tmp_path, monkeypatch):
    from app import storage
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.sqlite")
    rules = load_rules(RULES_FILE)
    fake = FakeGitHubApp(FIXTURE)

    import asyncio
    asyncio.run(run_scan_pipeline(fake, rules, 1, "owner", "repo"))
    assert len(fake.issues) == 1
    # Deuxième passage : tout est déjà signalé → rien de nouveau.
    asyncio.run(run_scan_pipeline(fake, rules, 1, "owner", "repo"))
    assert len(fake.issues) == 1


def test_pipeline_dedup_survives_line_shift(tmp_path, monkeypatch):
    from app import storage
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.sqlite")
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "pay.py").write_text("stripe.charges.create(1)\n", encoding="utf-8")
    rules = load_rules(RULES_FILE)
    fake = FakeGitHubApp(repo_dir)

    import asyncio
    asyncio.run(run_scan_pipeline(fake, rules, 1, "owner", "repo"))
    # Lines inserted above the finding: same usage, must not be re-reported.
    (repo_dir / "pay.py").write_text(
        "import stripe\n\n\nstripe.charges.create(1)\n", encoding="utf-8"
    )
    result = asyncio.run(run_scan_pipeline(fake, rules, 1, "owner", "repo"))
    assert result["status"] == "already_reported"
    assert len(fake.issues) == 1


def test_pipeline_dedup_scoped_by_owner(tmp_path, monkeypatch):
    from app import storage
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.sqlite")
    rules = load_rules(RULES_FILE)
    fake = FakeGitHubApp(FIXTURE)

    import asyncio
    asyncio.run(run_scan_pipeline(fake, rules, 1, "alice", "api"))
    # Same repo name, different owner: must get its own issue.
    result = asyncio.run(run_scan_pipeline(fake, rules, 2, "bob", "api"))
    assert result["status"] == "issue_opened"
    assert len(fake.issues) == 2


def test_pipeline_pr_mode(tmp_path, monkeypatch):
    from app import storage
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.sqlite")
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "gh.py").write_text(
        "headers = {'Authorization': 'token ghp_x'}\n", encoding="utf-8"
    )
    (repo_dir / ".driftguard.yml").write_text("mode: pr\nmin_severity: info\n", encoding="utf-8")

    rules = load_rules(RULES_FILE)
    fake = FakeGitHubApp(repo_dir)
    import asyncio
    result = asyncio.run(run_scan_pipeline(fake, rules, 1, "owner", "repo"))
    assert result["status"] == "pr_opened"
    assert len(fake.prs) == 1
    assert fake.prs[0]["changes"] == [("gh.py", "headers = {'Authorization': 'Bearer ghp_x'}\n")]


def test_pipeline_pr_mode_falls_back_to_issue(tmp_path, monkeypatch):
    # Stripe Charges has no safe mechanical fix → an issue, never a broken PR.
    from app import storage
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.sqlite")
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "pay.py").write_text("stripe.charges.create(1)\n", encoding="utf-8")
    (repo_dir / ".driftguard.yml").write_text("mode: pr\n", encoding="utf-8")

    rules = load_rules(RULES_FILE)
    fake = FakeGitHubApp(repo_dir)
    import asyncio
    result = asyncio.run(run_scan_pipeline(fake, rules, 1, "owner", "repo"))
    assert result["status"] == "issue_fallback"
    assert fake.prs == []


def test_apply_fixes(tmp_path):
    rules = load_rules(RULES_FILE)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text(
        "a = {'Authorization': 'token x'}\nkeep = 1\nb = {'Authorization': 'token y'}\n",
        encoding="utf-8",
    )
    findings, _ = scan_repo(repo, rules)
    changes = apply_fixes(repo, findings)
    assert changes == [
        ("app.py", "a = {'Authorization': 'Bearer x'}\nkeep = 1\nb = {'Authorization': 'Bearer y'}\n")
    ]


def test_apply_fixes_preserves_crlf(tmp_path):
    rules = load_rules(RULES_FILE)
    (tmp_path / "app.py").write_bytes(b"keep = 1\r\nh = {'Authorization': 'token x'}\r\n")
    findings, _ = scan_repo(tmp_path, rules)
    [(_, content)] = apply_fixes(tmp_path, findings)
    assert content == "keep = 1\r\nh = {'Authorization': 'Bearer x'}\r\n"


def test_apply_fixes_skips_non_utf8(tmp_path):
    rules = load_rules(RULES_FILE)
    (tmp_path / "app.py").write_bytes(b"# caf\xe9\nh = {'Authorization': 'token x'}\n")
    findings, _ = scan_repo(tmp_path, rules)
    assert findings  # detected…
    assert apply_fixes(tmp_path, findings) == []  # …but never rewritten lossily


# ---------- Webhook endpoint ----------

def _client():
    from fastapi.testclient import TestClient

    from app.main import app
    return TestClient(app)


def test_webhook_refuses_when_secret_missing(monkeypatch):
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
    r = _client().post("/webhook", content=b"{}", headers={"x-github-event": "push"})
    assert r.status_code == 503


def test_webhook_rejects_unsigned_request(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "s3cret")
    r = _client().post("/webhook", content=b"{}", headers={"x-github-event": "push"})
    assert r.status_code == 401


def test_webhook_accepts_signed_ping(monkeypatch):
    import hashlib
    import hmac
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "s3cret")
    body = b"{}"
    sig = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    r = _client().post(
        "/webhook", content=body,
        headers={"x-github-event": "ping", "x-hub-signature-256": sig},
    )
    assert r.status_code == 200
