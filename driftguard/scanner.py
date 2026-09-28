"""Codebase scanning: detect API usage matching the loaded rules."""

import os
import re
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path

from .rules import Rule

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env", "dist", "build", "out",
    "__pycache__", ".idea", ".vscode", ".driftguard", ".next", "vendor", "target",
}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
COMMENT_MARKERS = ("#", "//", "*", "/*", "<!--", "REM ")
# Hidden dirs are skipped, except these (CI workflows use deprecated actions/runners).
SCANNED_DOT_DIRS = {".github", ".circleci", ".gitlab"}
# Inline suppression, e.g. `stripe.charges.create(...)  # driftguard: ignore`
NEWLINE = re.compile("\n")
IGNORE_MARKER = re.compile(r"driftguard:\s*ignore", re.IGNORECASE)


@dataclass
class Finding:
    rule: Rule
    file: str  # path relative to the scanned directory
    line: int
    context: str  # the matched line, stripped
    in_comment: bool
    match: str


def _is_comment_line(stripped: str) -> bool:
    up = stripped.upper()
    return any(up.startswith(m) for m in COMMENT_MARKERS)


def scan_repo(path, rules: list[Rule]) -> tuple[list[Finding], int]:
    """Walk the directory (read-only) and return (findings, scanned_files)."""
    root = Path(path)
    findings: list[Finding] = []
    files_scanned = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and (not d.startswith(".") or d in SCANNED_DOT_DIRS)
        ]
        for name in sorted(filenames):
            full = Path(dirpath) / name
            try:
                size = full.stat().st_size
            except OSError:
                continue
            if size == 0 or size > MAX_FILE_SIZE:
                continue
            try:
                with open(full, "rb") as fh:
                    head = fh.read(512)
            except OSError:
                continue
            if b"\x00" in head:
                continue  # binary file
            try:
                text = full.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            files_scanned += 1

            rel = str(full.relative_to(root))
            lines = newlines = None
            for rule in rules:
                for regex in rule.compiled:
                    for m in regex.finditer(text):
                        if newlines is None:  # only computed for files that match
                            lines = text.splitlines()
                            newlines = [nl.start() for nl in NEWLINE.finditer(text)]
                        line_no = bisect_right(newlines, m.start() - 1) + 1
                        line = lines[line_no - 1].strip() if 0 < line_no <= len(lines) else ""
                        if IGNORE_MARKER.search(line):
                            continue
                        findings.append(
                            Finding(
                                rule=rule,
                                file=rel,
                                line=line_no,
                                context=line[:200],
                                in_comment=_is_comment_line(line),
                                match=m.group(0)[:120],
                            )
                        )

    findings.sort(key=lambda f: (f.file, f.line))
    return findings, files_scanned
