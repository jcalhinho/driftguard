"""Loading and validation of API breaking-change rules (YAML)."""

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

DEFAULT_RULES_FILE = Path(__file__).resolve().parent / "data" / "rules.yaml"

REQUIRED_FIELDS = ("id", "provider", "title", "severity", "patterns")
VALID_SEVERITIES = ("info", "warning", "critical")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class Rule:
    id: str
    provider: str
    title: str
    severity: str
    patterns: list[str]
    fix_hint: str = ""
    migration: str = ""
    since: str = ""
    effective: str = ""  # date the change took (or takes) effect upstream
    shutdown: str = ""  # date requests start failing: severity becomes critical from then
    files: list[str] = field(default_factory=list)  # optional path globs the rule applies to
    examples: list[str] = field(default_factory=list)  # must match (checked by the tests)
    counter_examples: list[str] = field(default_factory=list)  # must NOT match
    replace: dict = field(default_factory=dict)
    compiled: list = field(default_factory=list)


class RulesError(Exception):
    pass


def load_rules(path, today: date | None = None) -> list[Rule]:
    """Load and validate a YAML rules file. Raises RulesError when invalid.

    Rules with a `shutdown` date on or before `today` are reported as critical.
    """
    today = today or datetime.now(timezone.utc).date()
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    rules: list[Rule] = []
    seen_ids: set[str] = set()

    for entry in (data or {}).get("rules", []):
        rule_id = entry.get("id", "?")
        missing = [f for f in REQUIRED_FIELDS if f not in entry]
        if missing:
            raise RulesError(f"Rule '{rule_id}' is incomplete — missing fields: {missing}")
        if rule_id in seen_ids:
            raise RulesError(f"Duplicate id: {rule_id}")
        if entry["severity"] not in VALID_SEVERITIES:
            raise RulesError(
                f"Invalid severity for '{rule_id}': {entry['severity']} "
                f"(expected one of: {', '.join(VALID_SEVERITIES)})"
            )
        effective = str(entry.get("effective", ""))
        if effective and not DATE_RE.match(effective):
            raise RulesError(f"Invalid effective date for '{rule_id}': {effective} (YYYY-MM-DD)")
        shutdown = str(entry.get("shutdown", ""))
        if shutdown and not DATE_RE.match(shutdown):
            raise RulesError(f"Invalid shutdown date for '{rule_id}': {shutdown} (YYYY-MM-DD)")
        severity = entry["severity"]
        if shutdown and date.fromisoformat(shutdown) <= today:
            severity = "critical"
        seen_ids.add(rule_id)
        try:
            compiled = [re.compile(p) for p in entry["patterns"]]
        except re.error as e:
            raise RulesError(f"Invalid regex in '{rule_id}' ({e.pattern}): {e}")

        rules.append(
            Rule(
                id=rule_id,
                provider=entry.get("provider", "?"),
                title=entry.get("title", rule_id),
                severity=severity,
                patterns=list(entry["patterns"]),
                fix_hint=entry.get("fix_hint", ""),
                migration=entry.get("migration", ""),
                since=str(entry.get("since", "")),
                effective=effective,
                shutdown=shutdown,
                files=list(entry.get("files") or []),
                examples=list(entry.get("examples") or []),
                counter_examples=list(entry.get("counter_examples") or []),
                replace=entry.get("replace") or {},
                compiled=compiled,
            )
        )

    return rules
