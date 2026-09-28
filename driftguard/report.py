"""Scan reports: human-readable text and machine-readable JSON."""

import json

from .scanner import Finding

ICONS = {"critical": "🔴", "warning": "🟠", "info": "🔵"}


def to_json(root, findings: list[Finding], files_scanned: int) -> str:
    return json.dumps(
        {
            "path": str(root),
            "scanned_files": files_scanned,
            "findings": [
                {
                    "rule_id": f.rule.id,
                    "provider": f.rule.provider,
                    "title": f.rule.title,
                    "severity": f.rule.severity,
                    "file": f.file,
                    "line": f.line,
                    "context": f.context,
                    "in_comment": f.in_comment,
                    "match": f.match,
                    "fix_hint": f.rule.fix_hint,
                    "migration": f.rule.migration,
                }
                for f in findings
            ],
        },
        indent=2,
        ensure_ascii=False,
    )


def to_text(root, findings: list[Finding], files_scanned: int) -> str:
    lines = [
        f"🛡️ DriftGuard — {root}",
        f"{files_scanned} file(s) scanned · {len(findings)} at-risk usage(s)",
        "",
    ]
    current_file = None
    for f in findings:
        if f.file != current_file:
            lines.append(f"📄 {f.file}")
            current_file = f.file
        comment_note = " · inside a comment" if f.in_comment else ""
        lines.append(
            f"  {ICONS[f.rule.severity]} [{f.rule.severity:8}] L{f.line:<4} "
            f"{f.rule.title}{comment_note}"
        )
        lines.append(f"         ↳ {f.context[:160]}")
        if f.rule.fix_hint:
            lines.append(f"         💡 {f.rule.fix_hint}")
        if f.rule.migration:
            lines.append(f"         🔗 {f.rule.migration}")
    lines.append("")
    return "\n".join(lines)
