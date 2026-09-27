"""Suggested fix generation from a finding."""


def build_fix(finding) -> dict:
    """Return a fix: mechanical replacement when the rule allows it, otherwise manual."""
    rule = finding.rule
    for old, new in rule.replace.items():
        if old in finding.match:
            return {
                "action": "replace",
                "old": finding.match,
                "new": finding.match.replace(old, new, 1),
                "note": rule.fix_hint,
                "migration": rule.migration,
            }
    return {
        "action": "manual",
        "note": rule.fix_hint,
        "migration": rule.migration,
    }
