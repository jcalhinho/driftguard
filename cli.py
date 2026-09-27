#!/usr/bin/env python3
"""DriftGuard CLI.

Usage:
  driftguard scan ./my-repo --format text|json [--min-severity warning] [--only Stripe]
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
        description="Detect breaking API usage in your code — the Dependabot for APIs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Scan a codebase")
    scan.add_argument("path", help="Path to the directory to scan")
    scan.add_argument("--rules", default=str(DEFAULT_RULES), help="YAML rules file")
    scan.add_argument("--format", choices=["text", "json"], default="text")
    scan.add_argument("--min-severity", choices=list(SEVERITY_RANK), default="info")
    scan.add_argument("--only", action="append", default=[], help="Filter by provider (repeatable)")

    sub.add_parser("rules", help="List the loaded rules")

    args = parser.parse_args(argv)

    try:
        rules = load_rules(getattr(args, "rules", str(DEFAULT_RULES)))
    except RulesError as e:
        print(f"❌ Rules error: {e}", file=sys.stderr)
        return 2

    if args.command == "rules":
        for r in rules:
            print(f"[{r.severity:8}] {r.id} ({r.provider}) — {r.title}")
        return 0

    path = Path(args.path)
    if not path.is_dir():
        print(f"❌ Path not found: {path}", file=sys.stderr)
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

    # CI-friendly exit code: 1 when at least one usage was found.
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
