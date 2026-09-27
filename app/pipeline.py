"""Pipeline de scan : téléchargement → scan → rapport → issue ou PR (anti-doublons)."""

import shutil
import tempfile
from pathlib import Path

from engine.fixer import build_fix
from engine.report import to_text
from engine.rules import Rule
from engine.scanner import Finding, scan_repo

from . import storage
from .config import filter_findings, load_repo_config
from .github_app import GitHubApp

DEFAULT_RULES = Path(__file__).resolve().parents[1] / "rules" / "rules.yaml"

BRANDING = "\n\n---\n🛡️ Détecté par [DriftGuard](https://github.com/jcalhinho/driftguard) — le Dependabot des API."


def build_issue_body(repo: str, findings: list[Finding], files_scanned: int) -> str:
    return to_text(repo, findings, files_scanned) + BRANDING


def build_pr_body(findings: list[Finding]) -> str:
    lines = ["## 🛡️ Corrections DriftGuard", ""]
    for f in findings:
        lines.append(f"- **[{f.rule.severity}] {f.rule.title}** — `{f.file}:{f.line}`")
        if f.rule.fix_hint:
            lines.append(f"  - {f.rule.fix_hint}")
        if f.rule.migration:
            lines.append(f"  - Guide : {f.rule.migration}")
    lines.append(BRANDING)
    return "\n".join(lines)


def apply_fixes(repo_dir: Path, findings: list[Finding]) -> list[tuple[str, str]]:
    """Applique les remplacements mécaniques et renvoie [(chemin, nouveau contenu)].

    Appliqué de bas en haut (lignes décroissantes) pour préserver les numéros de ligne.
    """
    by_file: dict[str, list[Finding]] = {}
    for f in findings:
        by_file.setdefault(f.file, []).append(f)

    changes: list[tuple[str, str]] = []
    for rel_path, file_findings in by_file.items():
        fixable = [f for f in file_findings if any(k in f.match for k in f.rule.replace)]
        if not fixable:
            continue
        full = Path(repo_dir) / rel_path
        text = full.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        for f in sorted(fixable, key=lambda x: -x.line):
            if 1 <= f.line <= len(lines):
                fix = build_fix(f)
                if fix["action"] == "replace" and fix["old"] in lines[f.line - 1]:
                    lines[f.line - 1] = lines[f.line - 1].replace(fix["old"], fix["new"], 1)
        changes.append((rel_path, "\n".join(lines) + ("\n" if text.endswith("\n") else "")))
    return changes


async def run_scan_pipeline(
    app: GitHubApp,
    rules: list[Rule],
    installation_id: int,
    owner: str,
    repo: str,
) -> dict:
    """Pipeline complet : télécharge, scanne, déduplique, ouvre issue ou PR."""
    branch = await app.get_default_branch(installation_id, owner, repo)
    tmp = Path(tempfile.mkdtemp(prefix="driftguard-"))
    try:
        await app.download_repo(installation_id, owner, repo, branch, tmp)
        config = load_repo_config(tmp)
        findings, files_scanned = scan_repo(tmp, rules)
        findings = filter_findings(findings, config)
        if not findings:
            return {"status": "clean", "scanned": files_scanned}

        new_findings = [
            f for f in findings
            if not storage.already_reported(repo, f.rule.id, f.file, f.line)
        ]
        if not new_findings:
            return {"status": "already_reported", "scanned": files_scanned}

        full_name = f"{owner}/{repo}"
        storage.touch_repo(full_name, installation_id)

        if config.mode == "pr":
            changes = apply_fixes(tmp, new_findings)
            if not changes:
                # Aucun correctif mécanique possible → repli sur l'issue.
                body = build_issue_body(full_name, new_findings, files_scanned)
                title = f"[DriftGuard] {len(new_findings)} usage(s) d'API à risque"
                await app.create_issue(installation_id, owner, repo, title, body)
                result = {"status": "issue_fallback", "findings": len(new_findings)}
            else:
                body = build_pr_body(new_findings)
                title = f"Corrections d'API cassantes ({len(new_findings)} usage(s))"
                await app.create_pr(
                    installation_id, owner, repo, branch, changes, title, body
                )
                result = {"status": "pr_opened", "findings": len(new_findings)}
        else:
            body = build_issue_body(full_name, new_findings, files_scanned)
            title = f"[DriftGuard] {len(new_findings)} usage(s) d'API à risque"
            await app.create_issue(installation_id, owner, repo, title, body)
            result = {"status": "issue_opened", "findings": len(new_findings)}

        for f in new_findings:
            storage.mark_reported(repo, f.rule.id, f.file, f.line)
        return result
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
