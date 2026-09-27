"""Stockage SQLite : installations, repos, findings déjà signalés (anti-doublons)."""

import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "driftguard.sqlite"


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
    conn.execute(
        "CREATE TABLE IF NOT EXISTS reported ("
        "repo TEXT, rule_id TEXT, file TEXT, line INTEGER, reported_at REAL, "
        "PRIMARY KEY (repo, rule_id, file, line))"
    )
    return conn


def save_installation(installation_id: int, account: str):
    conn = _conn()
    conn.execute(
        "INSERT OR REPLACE INTO installations (id, account, created_at) VALUES (?, ?, ?)",
        (installation_id, account, time.time()),
    )
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


def already_reported(repo: str, rule_id: str, file: str, line: int) -> bool:
    conn = _conn()
    row = conn.execute(
        "SELECT 1 FROM reported WHERE repo = ? AND rule_id = ? AND file = ? AND line = ?",
        (repo, rule_id, file, line),
    ).fetchone()
    conn.close()
    return row is not None


def mark_reported(repo: str, rule_id: str, file: str, line: int):
    conn = _conn()
    conn.execute(
        "INSERT OR REPLACE INTO reported (repo, rule_id, file, line, reported_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (repo, rule_id, file, line, time.time()),
    )
    conn.commit()
    conn.close()
