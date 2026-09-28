"""Suggested fix generation from a finding."""

import re


def _replaceable(match: str, old: str) -> bool:
    """`old` occurs in the match and is not the prefix of a longer token.

    Guards version bumps: "actions/cache@v2" must not turn "@v2.1.6" into "@v4.1.6".
    """
    return re.search(re.escape(old) + r"(?![\w.])", match) is not None


def build_fix(finding) -> dict:
    """Return a fix: mechanical replacement when the rule allows it, otherwise manual."""
    rule = finding.rule
    for old, new in rule.replace.items():
        if _replaceable(finding.match, old):
            return {
                "action": "replace",
                "old": finding.match,
                "new": re.sub(re.escape(old) + r"(?![\w.])", new, finding.match, count=1),
                "note": rule.fix_hint,
                "migration": rule.migration,
            }
    return {
        "action": "manual",
        "note": rule.fix_hint,
        "migration": rule.migration,
    }
