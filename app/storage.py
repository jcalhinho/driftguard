"""SQLite storage: installations, repos, already-reported findings (dedup)."""

import hashlib
import os
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(
    os.getenv("DRIFTGUARD_DB", str(Path(__file__).resolve().parent / "driftguard.sqlite"))
)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS installations ("
        "id INTEGER PRIMARY KEY, account TEXT, created_at REAL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS repos ("
        "full_name TEXT PRIMARY KEY, installation_id INTEGER, last_scan_at REAL)"
    )
    # Keyed on the full repo name and a fingerprint of the matched code, not the
    # line number: inserting lines above a finding must not re-report it.
    # (Replaces the legacy `reported` table, which was keyed on (name, line).)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS reported_findings ("
        "repo TEXT, rule_id TEXT, file TEXT, fingerprint TEXT, reported_at REAL, "
        "PRIMARY KEY (repo, rule_id, file, fingerprint))"
    )
    return conn


def fingerprint(context: str, match: str) -> str:
    """Stable identity of a finding, independent of its line number."""
    normalized = " ".join(context.split()) + "\0" + match
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


def save_installation(installation_id: int, account: str):
    conn = _conn()
    conn.execute(
        "INSERT OR REPLACE INTO installations (id, account, created_at) VALUES (?, ?, ?)",
        (installation_id, account, time.time()),
    )
    conn.commit()
    conn.close()


def delete_installation(installation_id: int):
    """App uninstalled: forget the installation, its repos and their history."""
    conn = _conn()
    repos = [
        r[0] for r in conn.execute(
            "SELECT full_name FROM repos WHERE installation_id = ?", (installation_id,)
        )
    ]
    conn.executemany("DELETE FROM reported_findings WHERE repo = ?", [(r,) for r in repos])
    conn.execute("DELETE FROM repos WHERE installation_id = ?", (installation_id,))
    conn.execute("DELETE FROM installations WHERE id = ?", (installation_id,))
    conn.commit()
    conn.close()


def touch_repo(full_name: str, installation_id: int):
    conn = _conn()
    conn.execute(
        "INSERT OR REPLACE INTO repos (full_name, installation_id, last_scan_at) "
        "VALUES (?, ?, ?)",
        (full_name, installation_id, time.time()),
    )
    conn.commit()
    conn.close()


def already_reported(repo: str, rule_id: str, file: str, fp: str) -> bool:
    """`repo` must be the full name (owner/repo)."""
    conn = _conn()
    row = conn.execute(
        "SELECT 1 FROM reported_findings "
        "WHERE repo = ? AND rule_id = ? AND file = ? AND fingerprint = ?",
        (repo, rule_id, file, fp),
    ).fetchone()
    conn.close()
    return row is not None


def mark_reported(repo: str, rule_id: str, file: str, fp: str):
    conn = _conn()
    conn.execute(
        "INSERT OR REPLACE INTO reported_findings "
        "(repo, rule_id, file, fingerprint, reported_at) VALUES (?, ?, ?, ?, ?)",
        (repo, rule_id, file, fp, time.time()),
    )
    conn.commit()
    conn.close()
