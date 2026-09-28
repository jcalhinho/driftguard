"""DriftGuard CLI.

Usage:
  driftguard scan ./my-repo [--format text|json|github] [--min-severity warning]
                  [--only Stripe] [--ignore 'tests/**'] [--no-fail]
  driftguard rules
"""

import argparse
import sys
from pathlib import Path

from .config import SEVERITY_RANK, filter_findings, load_repo_config
from .report import to_github, to_json, to_text
from .rules import DEFAULT_RULES_FILE, RulesError, load_rules
from .scanner import scan_repo

ICONS = {"critical": "🔴 critical", "warning": "🟠 warning", "info": "🔵 info"}


def rules_markdown(rules) -> str:
    """Rules table for the README (regenerate with `driftguard rules --format markdown`)."""
    lines = ["| Provider | Breaking change | Severity | Effective |", "|---|---|---|---|"]
    for r in sorted(rules, key=lambda r: (r.provider.lower(), -SEVERITY_RANK[r.severity], r.id)):
        title = r.title.replace("|", "\\|")
        lines.append(
            f"| {r.provider} | [{title}]({r.migration}) | {ICONS[r.severity]} "
            f"| {r.effective or '—'} |"
        )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="driftguard",
        description="Detect breaking API usage in your code — the Dependabot for APIs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Scan a codebase")
    scan.add_argument("path", help="Path to the directory to scan")
    scan.add_argument("--rules", default=str(DEFAULT_RULES_FILE), help="YAML rules file")
    scan.add_argument("--format", choices=["text", "json", "github"], default="text")
    scan.add_argument(
        "--min-severity", choices=list(SEVERITY_RANK),
        help="Lowest severity to report (default: .driftguard.yml, else info)",
    )
    scan.add_argument("--only", action="append", default=[], help="Filter by provider (repeatable)")
    scan.add_argument(
        "--ignore", action="append", default=[], metavar="GLOB",
        help="Skip matching paths, e.g. 'tests/**' (repeatable)",
    )
    scan.add_argument(
        "--no-fail", action="store_true", help="Always exit 0 (report only)",
    )

    rules_cmd = sub.add_parser("rules", help="List the loaded rules")
    rules_cmd.add_argument("--rules", default=str(DEFAULT_RULES_FILE), help="YAML rules file")
    rules_cmd.add_argument("--format", choices=["text", "markdown"], default="text")

    args = parser.parse_args(argv)

    try:
        rules = load_rules(getattr(args, "rules", str(DEFAULT_RULES_FILE)))
    except RulesError as e:
        print(f"❌ Rules error: {e}", file=sys.stderr)
        return 2

    if args.command == "rules":
        if args.format == "markdown":
            print(rules_markdown(rules))
            return 0
        for r in rules:
            print(f"[{r.severity:8}] {r.id} ({r.provider}) — {r.title}")
        return 0

    path = Path(args.path)
    if not path.is_dir():
        print(f"❌ Path not found: {path}", file=sys.stderr)
        return 2

    # .driftguard.yml in the scanned repo applies; command-line flags take precedence.
    config = load_repo_config(path)
    config.min_severity = args.min_severity or (
        config.min_severity if (path / ".driftguard.yml").is_file() else "info"
    )
    config.only_providers = args.only or config.only_providers
    config.ignore_paths = [*config.ignore_paths, *args.ignore]

    findings, files_scanned = scan_repo(path, rules)
    findings = filter_findings(findings, config)

    if args.format == "json":
        print(to_json(path, findings, files_scanned))
    elif args.format == "github":
        print(to_github(path, findings, files_scanned))
    else:
        print(to_text(path, findings, files_scanned))

    # CI-friendly exit code: 1 when at least one usage was found.
    return 1 if findings and not args.no_fail else 0


if __name__ == "__main__":
    sys.exit(main())
