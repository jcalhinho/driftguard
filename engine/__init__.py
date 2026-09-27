"""DriftGuard — le « Dependabot des API ».

Moteur de détection des usages d'API cassants dans une codebase.
"""

from .fixer import build_fix
from .report import to_json, to_text
from .rules import Rule, RulesError, load_rules
from .scanner import Finding, scan_repo

__all__ = [
    "Finding",
    "Rule",
    "RulesError",
    "build_fix",
    "load_rules",
    "scan_repo",
    "to_json",
    "to_text",
]
