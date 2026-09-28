"""Tests du moteur DriftGuard : règles, scan, fixer, rapport, CLI."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from driftguard.fixer import build_fix
from driftguard.report import to_json, to_text
from driftguard.rules import RulesError, load_rules
from driftguard.scanner import scan_repo

ROOT = Path(__file__).resolve().parents[1]
RULES_FILE = ROOT / "driftguard" / "data" / "rules.yaml"
FIXTURE = ROOT / "tests" / "fixtures" / "sample_repo"


# ---------- Règles ----------

def test_load_rules():
    rules = load_rules(RULES_FILE)
    assert len(rules) >= 8
    ids = [r.id for r in rules]
    assert "stripe-charges-api-deprecated" in ids


def test_load_rules_missing_field(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("rules:\n  - id: x\n    provider: Stripe\n", encoding="utf-8")
    with pytest.raises(RulesError):
        load_rules(bad)


def test_load_rules_invalid_regex(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "rules:\n  - id: x\n    provider: Stripe\n    title: t\n"
        "    severity: info\n    patterns: ['([']\n",
        encoding="utf-8",
    )
    with pytest.raises(RulesError):
        load_rules(bad)


def test_load_rules_duplicate_id(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "rules:\n  - id: x\n    provider: Stripe\n    title: t\n    severity: info\n    patterns: ['a']\n"
        "  - id: x\n    provider: Stripe\n    title: t\n    severity: info\n    patterns: ['b']\n",
        encoding="utf-8",
    )
    with pytest.raises(RulesError):
        load_rules(bad)


# ---------- Scan ----------

@pytest.fixture(scope="module")
def scan_result():
    rules = load_rules(RULES_FILE)
    return scan_repo(FIXTURE, rules)


def test_scan_counts(scan_result):
    findings, files_scanned = scan_result
    assert files_scanned == 4
    # 4 (app.py) + 2 (payments.js) + 1 (config.py) + 1 (github_flow.py)
    assert len(findings) == 8


def test_scan_critical_count(scan_result):
    findings, _ = scan_result
    criticals = [f for f in findings if f.rule.severity == "critical"]
    assert len(criticals) == 6


def test_scan_comment_flag(scan_result):
    findings, _ = scan_result
    in_comments = [f for f in findings if f.in_comment]
    assert len(in_comments) == 1
    assert in_comments[0].rule.id == "stripe-sources-api-deprecated"


def test_scan_lines(scan_result):
    findings, _ = scan_result
    by_file_line = {(f.file, f.line) for f in findings}
    assert ("app.py", 8) in by_file_line  # stripe.charges.create
    assert ("payments.js", 4) in by_file_line  # stripe.charges.create
    assert ("config.py", 2) in by_file_line  # xoxp-
    assert ("github_flow.py", 3) in by_file_line  # OAuth password grant


def test_scan_skips_git_dir(tmp_path):
    rules = load_rules(RULES_FILE)
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / ".git" / "config").write_text("stripe.charges.create", encoding="utf-8")
    (repo / "real.py").write_text("stripe.charges.create", encoding="utf-8")
    findings, files = scan_repo(repo, rules)
    assert files == 1
    assert len(findings) == 1
    assert findings[0].file == "real.py"


# ---------- Fixer ----------

def test_fixer_replace(tmp_path):
    rules = load_rules(RULES_FILE)
    (tmp_path / "gh.py").write_text(
        "headers = {'Authorization': 'token ghp_x'}\n", encoding="utf-8"
    )
    findings, _ = scan_repo(tmp_path, rules)
    target = next(f for f in findings if f.rule.id == "github-auth-token-header")
    fix = build_fix(target)
    assert fix["action"] == "replace"
    assert "Bearer " in fix["new"]


def test_fixer_no_unsafe_replacement(scan_result):
    # Charges → PaymentIntents is not a drop-in change: it must stay manual.
    findings, _ = scan_result
    target = next(f for f in findings if f.rule.id == "stripe-charges-api-deprecated")
    assert build_fix(target)["action"] == "manual"


def test_fixer_manual(scan_result):
    findings, _ = scan_result
    target = next(f for f in findings if f.rule.id == "slack-legacy-tokens")
    fix = build_fix(target)
    assert fix["action"] == "manual"
    assert fix["migration"].startswith("https://")


# ---------- Rapports ----------

def test_json_report(scan_result):
    findings, files = scan_result
    data = json.loads(to_json(FIXTURE, findings, files))
    assert data["scanned_files"] == 4
    assert len(data["findings"]) == 8
    assert data["findings"][0]["rule_id"]
    assert "fix_hint" in data["findings"][0]


def test_text_report(scan_result):
    findings, files = scan_result
    text = to_text(FIXTURE, findings, files)
    assert "DriftGuard" in text
    assert "📄 app.py" in text
    assert "🔴" in text


# ---------- CLI ----------

def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "driftguard", *args],
        capture_output=True, text=True, cwd=ROOT, check=False,
    )


def test_cli_scan_text():
    result = run_cli("scan", str(FIXTURE))
    assert result.returncode == 1  # des findings → exit 1 (lisible en CI)
    assert "at-risk usage(s)" in result.stdout


def test_cli_scan_json():
    result = run_cli("scan", str(FIXTURE), "--format", "json")
    data = json.loads(result.stdout)
    assert len(data["findings"]) == 8


def test_cli_min_severity():
    result = run_cli("scan", str(FIXTURE), "--format", "json", "--min-severity", "critical")
    data = json.loads(result.stdout)
    assert len(data["findings"]) == 6


def test_cli_only_provider():
    result = run_cli("scan", str(FIXTURE), "--format", "json", "--only", "Slack")
    data = json.loads(result.stdout)
    assert len(data["findings"]) == 2
    assert all(f["provider"] == "Slack" for f in data["findings"])


def test_cli_clean_repo(tmp_path):
    clean = tmp_path / "clean"
    clean.mkdir()
    (clean / "ok.py").write_text("print('hello')\n", encoding="utf-8")
    result = run_cli("scan", str(clean))
    assert result.returncode == 0


def test_cli_rules_command():
    result = run_cli("rules")
    assert result.returncode == 0
    assert "stripe-charges-api-deprecated" in result.stdout


# ---------- Scanner options ----------

def test_scan_includes_github_workflows(tmp_path):
    rules = load_rules(RULES_FILE)
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("run: curl https://s3.amazonaws.com/b/k\n", encoding="utf-8")
    (tmp_path / ".cache").mkdir()
    (tmp_path / ".cache" / "x.py").write_text("https://s3.amazonaws.com/b/k\n", encoding="utf-8")
    findings, _ = scan_repo(tmp_path, rules)
    assert [f.file for f in findings] == [str(Path(".github/workflows/ci.yml"))]


def test_scan_inline_ignore(tmp_path):
    rules = load_rules(RULES_FILE)
    (tmp_path / "a.py").write_text(
        "stripe.charges.create(1)  # driftguard: ignore\nstripe.charges.create(2)\n",
        encoding="utf-8",
    )
    findings, _ = scan_repo(tmp_path, rules)
    assert [f.line for f in findings] == [2]


def test_scan_line_numbers_multiline_match(tmp_path):
    rules = load_rules(RULES_FILE)
    (tmp_path / "a.py").write_text("x = 1\n\n\ny = 'text-davinci-003'\n", encoding="utf-8")
    findings, _ = scan_repo(tmp_path, rules)
    assert findings[0].line == 4


def test_cli_ignore_and_repo_config(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "t.py").write_text("stripe.charges.create(1)\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("stripe.charges.create(1)\n", encoding="utf-8")
    data = json.loads(run_cli("scan", str(tmp_path), "--format", "json", "--ignore", "tests/**").stdout)
    assert [f["file"] for f in data["findings"]] == ["a.py"]
    (tmp_path / ".driftguard.yml").write_text("ignore_paths: [a.py]\n", encoding="utf-8")
    data = json.loads(run_cli("scan", str(tmp_path), "--format", "json").stdout)
    assert [f["file"] for f in data["findings"]] == [str(Path("tests/t.py"))]


def test_cli_no_fail(tmp_path):
    (tmp_path / "a.py").write_text("stripe.charges.create(1)\n", encoding="utf-8")
    assert run_cli("scan", str(tmp_path), "--no-fail").returncode == 0


def test_cli_github_format():
    result = run_cli("scan", str(FIXTURE), "--format", "github")
    first = result.stdout.splitlines()[0]
    assert first.startswith("::")
    assert "file=" in first and ",line=" in first
