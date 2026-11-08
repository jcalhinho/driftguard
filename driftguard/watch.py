"""Watch provider documentation: tell when a page or a source file your code depends on changes.

The scanner finds retired APIs in your code. This finds the other kind of drift: a pricing page, a
changelog, a log schema in a provider's source code that your code copies by hand. Declare them in
`.driftguard.yml`:

    watch:
      - id: anthropic-pricing
        url: https://platform.claude.com/docs/en/about-claude/pricing.md
        why: Claude prices in src/pricing.ts
      - id: continue-dev-data
        url: https://raw.githubusercontent.com/continuedev/continue/main/core/data/log.ts
        start: "export class DataLogger"   # optional: only watch the text from here…
        end: "export const"                # …up to here

`driftguard watch .` fetches each one, keeps the readable text (tags, scripts and styles removed
from HTML; Markdown and code as they are), and compares its SHA-256 with the fingerprint recorded in
`.driftguard.lock.json`. After reviewing a change and updating your code, record the new
fingerprints with `driftguard watch . --update` and commit the lock file.

Prefer a page's Markdown version when the site offers one (often the page URL plus `.md`): it has no
navigation around the content, so it only changes when the content does.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

LOCK_FILE = ".driftguard.lock.json"
CONFIG_FILE = ".driftguard.yml"
USER_AGENT = "driftguard-watch (+https://github.com/jcalhinho/driftguard)"
MAX_BYTES = 10 * 1024 * 1024
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")

# Statuses. Every one but "unchanged" asks for a look.
UNCHANGED = "unchanged"
CHANGED = "changed"
MOVED = "moved"            # the address now redirects somewhere else
NEW = "new"                # no fingerprint recorded yet
UNREACHABLE = "unreachable"
NO_SECTION = "no-section"  # the start/end markers are not in the page any more
EMPTY = "empty"            # nothing readable (a page drawn by JavaScript, for example)
UNREADABLE = (UNREACHABLE, NO_SECTION, EMPTY)


class WatchError(Exception):
    """A watch list or lock file that cannot be used."""


@dataclass
class Source:
    id: str
    url: str
    why: str = ""
    start: str | None = None
    end: str | None = None


@dataclass
class Fetched:
    final_url: str
    content_type: str
    body: bytes


@dataclass
class Result:
    source: Source
    status: str
    detail: str = ""
    sha256: str | None = None
    final_url: str | None = None
    recorded: dict = field(default_factory=dict)

    @property
    def needs_review(self) -> bool:
        return self.status != UNCHANGED


def load_sources(repo_dir: Path) -> list[Source]:
    """The `watch` list of .driftguard.yml (empty when there is none)."""
    config_file = Path(repo_dir) / CONFIG_FILE
    if not config_file.is_file():
        return []
    try:
        data = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as error:
        raise WatchError(f"{CONFIG_FILE} is not valid YAML: {error}") from error
    entries = data.get("watch", []) if isinstance(data, dict) else []
    if not isinstance(entries, list):
        raise WatchError("`watch` must be a list")
    sources, seen = [], set()
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            raise WatchError(f"watch entry {index} must be a mapping with `id` and `url`")
        source_id, url = str(entry.get("id", "")).strip(), str(entry.get("url", "")).strip()
        if not ID_PATTERN.match(source_id):
            raise WatchError(f"watch entry {index}: `id` must be letters, digits, '.', '_' or '-'")
        if source_id in seen:
            raise WatchError(f"watch entry {index}: the id `{source_id}` is used twice")
        if not url.startswith(("https://", "http://")):
            raise WatchError(f"watch entry `{source_id}`: `url` must start with https:// or http://")
        seen.add(source_id)
        start, end = entry.get("start"), entry.get("end")
        sources.append(Source(
            id=source_id,
            url=url,
            why=str(entry.get("why", "") or ""),
            start=str(start) if start not in (None, "") else None,
            end=str(end) if end not in (None, "") else None,
        ))
    return sources


def load_lock(repo_dir: Path) -> dict:
    lock_file = Path(repo_dir) / LOCK_FILE
    if not lock_file.is_file():
        return {}
    try:
        data = json.loads(lock_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise WatchError(f"{LOCK_FILE} is not valid JSON: {error}") from error
    sources = data.get("sources", {}) if isinstance(data, dict) else {}
    return sources if isinstance(sources, dict) else {}


def save_lock(repo_dir: Path, results: list[Result], today: str | None = None) -> None:
    """Record the fingerprint of every source that could be read; keep the others as they were."""
    previous = load_lock(repo_dir)
    current_ids = {result.source.id for result in results}
    sources = {}
    for result in results:
        if result.sha256 is None:
            if result.source.id in previous:
                sources[result.source.id] = previous[result.source.id]
            continue
        sources[result.source.id] = {
            "url": result.source.url,
            "final_url": result.final_url,
            "sha256": result.sha256,
            "checked": today or date.today().isoformat(),
        }
    # Entries removed from the watch list leave the lock file too.
    sources = {key: value for key, value in sources.items() if key in current_ids}
    text = json.dumps({"version": 1, "sources": dict(sorted(sources.items()))}, indent=2)
    (Path(repo_dir) / LOCK_FILE).write_text(text + "\n", encoding="utf-8")


def fetch(url: str, timeout: float = 20.0) -> Fetched:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise WatchError(f"larger than {MAX_BYTES // (1024 * 1024)} MB")
        return Fetched(
            final_url=response.geturl(),
            content_type=response.headers.get("Content-Type", ""),
            body=body,
        )


_DROPPED_BLOCKS = re.compile(r"(?is)<(script|style|noscript|svg|template)\b.*?</\1\s*>")
_COMMENTS = re.compile(r"(?s)<!--.*?-->")
_TAGS = re.compile(r"(?s)<[^>]+>")


def readable_text(body: bytes, content_type: str) -> str:
    """The text a reader sees: tags removed from HTML, line endings and blanks normalised."""
    text = body.decode(_charset(content_type), errors="replace")
    is_html = "html" in content_type.lower() or text.lstrip()[:15].lower().startswith(
        ("<!doctype html", "<html")
    )
    if is_html:
        text = _COMMENTS.sub(" ", _DROPPED_BLOCKS.sub(" ", text))
        text = html.unescape(_TAGS.sub(" ", text))
    lines = (" ".join(line.split()) for line in text.replace("\r\n", "\n").split("\n"))
    return "\n".join(line for line in lines if line)


def _charset(content_type: str) -> str:
    match = re.search(r"charset=([\w-]+)", content_type, re.IGNORECASE)
    if match:
        try:
            "".encode(match.group(1))
            return match.group(1)
        except LookupError:
            pass
    return "utf-8"


def section(text: str, start: str | None, end: str | None) -> str | None:
    """The text from `start` (included) to `end` (excluded); None when a marker is missing."""
    if start is not None:
        position = text.find(start)
        if position < 0:
            return None
        text = text[position:]
    if end is not None:
        position = text.find(end, len(start) if start else 0)
        if position < 0:
            return None
        text = text[:position]
    return text


def check(source: Source, recorded: dict | None, fetcher=fetch) -> Result:
    recorded = recorded or {}
    try:
        fetched = fetcher(source.url)
    except urllib.error.HTTPError as error:
        return Result(source, UNREACHABLE, f"HTTP {error.code}", recorded=recorded)
    except (urllib.error.URLError, TimeoutError, OSError, WatchError, ValueError) as error:
        reason = getattr(error, "reason", None) or error
        return Result(source, UNREACHABLE, str(reason), recorded=recorded)
    text = section(readable_text(fetched.body, fetched.content_type), source.start, source.end)
    if text is None:
        return Result(source, NO_SECTION, "the start or end marker is not in the page any more",
                      final_url=fetched.final_url, recorded=recorded)
    if not text.strip():
        return Result(source, EMPTY, "no readable text (a page drawn by JavaScript?)",
                      final_url=fetched.final_url, recorded=recorded)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    result = Result(source, UNCHANGED, sha256=digest, final_url=fetched.final_url, recorded=recorded)
    if not recorded.get("sha256"):
        result.status, result.detail = NEW, "no fingerprint recorded yet"
    elif recorded.get("url") and recorded["url"] != source.url:
        result.status, result.detail = NEW, f"the address changed in the watch list (was {recorded['url']})"
    elif recorded.get("final_url") and recorded["final_url"] != fetched.final_url:
        result.status = MOVED
        result.detail = f"now served from {fetched.final_url} (was {recorded['final_url']})"
    elif recorded["sha256"] != digest:
        result.status = CHANGED
        result.detail = f"content changed since {recorded.get('checked', 'the last check')}"
    return result


def run(repo_dir: Path, fetcher=fetch) -> list[Result]:
    lock = load_lock(repo_dir)
    return [check(source, lock.get(source.id), fetcher) for source in load_sources(repo_dir)]


ICONS = {
    UNCHANGED: "✅", CHANGED: "🟠", MOVED: "🟠", NEW: "🔵",
    UNREACHABLE: "🔴", NO_SECTION: "🔴", EMPTY: "🔴",
}


def to_text(results: list[Result]) -> str:
    review = sum(result.needs_review for result in results)
    lines = [f"🛡️ DriftGuard watch — {len(results)} source(s) · {review} to review", ""]
    for result in results:
        lines.append(f"{ICONS[result.status]} {result.status:11} {result.source.id}  {result.source.url}")
        if result.detail:
            lines.append(f"      ↳ {result.detail}")
        if result.needs_review and result.source.why:
            lines.append(f"      ⚙ {result.source.why}")
    if any(result.status in (NEW, CHANGED, MOVED) for result in results):
        lines += ["", "Review the changes, update your code, then: driftguard watch . --update"]
    lines.append("")
    return "\n".join(lines)


def to_json(results: list[Result]) -> str:
    return json.dumps([
        {
            "id": result.source.id,
            "url": result.source.url,
            "why": result.source.why,
            "status": result.status,
            "detail": result.detail,
            "sha256": result.sha256,
            "final_url": result.final_url,
            "recorded": result.recorded,
        }
        for result in results
    ], indent=2, ensure_ascii=False)


def _gh(value: str, prop: bool = False) -> str:
    value = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return value.replace(":", "%3A").replace(",", "%2C") if prop else value


def to_github(results: list[Result]) -> str:
    """One annotation per source to review, then the same table as the text report."""
    out = []
    for result in results:
        if not result.needs_review:
            continue
        level = "error" if result.status in UNREADABLE else "warning"
        message = f"{result.source.url}\n{result.detail}"
        if result.source.why:
            message += f"\n{result.source.why}"
        out.append(
            f"::{level} title={_gh('DriftGuard watch: ' + result.source.id + ' ' + result.status, True)}"
            f"::{_gh(message)}"
        )
    out.append(to_text(results))
    return "\n".join(out)


def summary_markdown(results: list[Result]) -> str:
    """For $GITHUB_STEP_SUMMARY."""
    lines = ["### DriftGuard watch", "", "| | Source | Status | Detail |", "|---|---|---|---|"]
    for result in results:
        detail = (result.detail or "").replace("|", "\\|")
        lines.append(
            f"| {ICONS[result.status]} | [{result.source.id}]({result.source.url}) "
            f"| {result.status} | {detail} |"
        )
    return "\n".join(lines) + "\n"
