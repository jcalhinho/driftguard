"""Chargement et validation des règles de breaking changes d'API (YAML)."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

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
    """Charge et valide un fichier de règles YAML. Lève RulesError si invalide."""
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    rules: list[Rule] = []
    seen_ids: set[str] = set()

    for entry in (data or {}).get("rules", []):
        rule_id = entry.get("id", "?")
        missing = [f for f in REQUIRED_FIELDS if f not in entry]
        if missing:
            raise RulesError(f"Règle « {rule_id} » incomplète — champs manquants : {missing}")
        if rule_id in seen_ids:
            raise RulesError(f"id dupliqué : {rule_id}")
        if entry["severity"] not in VALID_SEVERITIES:
            raise RulesError(
                f"Sévérité invalide pour « {rule_id} » : {entry['severity']} "
                f"(attendu : {', '.join(VALID_SEVERITIES)})"
            )
        seen_ids.add(rule_id)
        try:
            compiled = [re.compile(p) for p in entry["patterns"]]
        except re.error as e:
            raise RulesError(f"Regex invalide dans « {rule_id} » ({e.pattern}) : {e}")

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
