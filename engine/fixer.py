"""Génération de correctifs suggérés à partir d'un finding."""


def build_fix(finding) -> dict:
    """Renvoie un correctif : remplacement mécanique si la règle le permet, sinon manuel."""
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
