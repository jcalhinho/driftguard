#!/usr/bin/env python3
"""CLI DriftGuard.

Usage :
  driftguard scan ./mon-repo --format text|json [--min-severity warning] [--only Stripe]
  driftguard rules
"""

import argparse
import sys
from pathlib import Path

from engine.report import to_json, to_text
from engine.rules import RulesError, load_rules
from engine.scanner import scan_repo

DEFAULT_RULES = Path(__file__).resolve().parent / "rules" / "rules.yaml"
SEVERITY_RANK = {"info": 0, "warning": 1, "critical": 2}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="driftguard",
        description="Détecte les usages d'API cassants dans ton code — le Dependabot des API.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Scanner une codebase")
    scan.add_argument("path", help="Chemin du dossier à scanner")
    scan.add_argument("--rules", default=str(DEFAULT_RULES), help="Fichier de règles YAML")
    scan.add_argument("--format", choices=["text", "json"], default="text")
    scan.add_argument("--min-severity", choices=list(SEVERITY_RANK), default="info")
    scan.add_argument("--only", action="append", default=[], help="Filtrer par provider (répétable)")

    sub.add_parser("rules", help="Lister les règles chargées")

    args = parser.parse_args(argv)

    try:
        rules = load_rules(getattr(args, "rules", str(DEFAULT_RULES)))
    except RulesError as e:
        print(f"❌ Erreur de règles : {e}", file=sys.stderr)
        return 2

    if args.command == "rules":
        for r in rules:
            print(f"[{r.severity:8}] {r.id} ({r.provider}) — {r.title}")
        return 0

    path = Path(args.path)
    if not path.is_dir():
        print(f"❌ Chemin introuvable : {path}", file=sys.stderr)
        return 2

    findings, files_scanned = scan_repo(path, rules)
    findings = [
        f for f in findings
        if SEVERITY_RANK[f.rule.severity] >= SEVERITY_RANK[args.min_severity]
    ]
    if args.only:
        providers = {p.lower() for p in args.only}
        findings = [f for f in findings if f.rule.provider.lower() in providers]

    if args.format == "json":
        print(to_json(path, findings, files_scanned))
    else:
        print(to_text(path, findings, files_scanned))

    # Code de sortie lisible par une CI : 1 si au moins un usage trouvé.
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
