"""Loading and validation of API breaking-change rules (YAML)."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_RULES_FILE = Path(__file__).resolve().parent / "data" / "rules.yaml"

REQUIRED_FIELDS = ("id", "provider", "title", "severity", "patterns")
VALID_SEVERITIES = ("info", "warning", "critical")


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
    replace: dict = field(default_factory=dict)
    compiled: list = field(default_factory=list)


class RulesError(Exception):
    pass


def load_rules(path) -> list[Rule]:
    """Load and validate a YAML rules file. Raises RulesError when invalid."""
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
                severity=entry["severity"],
                patterns=list(entry["patterns"]),
                fix_hint=entry.get("fix_hint", ""),
                migration=entry.get("migration", ""),
                since=str(entry.get("since", "")),
                replace=entry.get("replace") or {},
                compiled=compiled,
            )
        )

    return rules
