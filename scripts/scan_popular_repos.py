#!/usr/bin/env python3
"""
Scan the top 1000 most popular public GitHub repos for breaking API changes.

Read-only: downloads tarballs, scans, deletes. Never opens issues or PRs.
Outputs a JSON report + a markdown summary with aggregate statistics.

Usage:
    python scripts/scan_popular_repos.py [--limit 100] [--workers 4]

Requires: GITHUB_TOKEN env var (a fine-grained PAT with public read access).
"""

import argparse
import json
import os
import sys
import tempfile
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

# Add parent dir to path so we can import driftguard
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from driftguard.rules import load_rules
from driftguard.scanner import scan_directory

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# File extensions worth scanning (skip binaries, assets, lock files)
SCAN_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".rb", ".php", ".go", ".rs",
    ".java", ".kt", ".swift", ".cs", ".scala", ".clj", ".ex", ".exs",
    ".sh", ".bash", ".zsh", ".yml", ".yaml", ".json", ".toml", ".xml",
    ".html", ".htm", ".css", ".scss", ".vue", ".svelte",
    ".c", ".cpp", ".h", ".hpp", ".m", ".mm",
    ".sql", ".graphql", ".proto", ".thrift",
    ".env", ".cfg", ".ini", ".conf",
    ".tf", ".tfvars",
    ".dart", ".lua", ".r", ".jl",
}

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache",
             ".ruff_cache", "dist", "build", ".next", ".nuxt", "vendor", "Pods",
             ".gradle", ".idea", ".vscode", "target", "deps", "_build", "coverage",
             ".cache", ".turbo", ".output"}


def fetch_top_repos(limit: int = 1000) -> list[dict]:
    """Fetch the most starred public repos from GitHub."""
    repos = []
    page = 1
    per_page = 100

    with httpx.Client(timeout=30, headers={"Authorization": f"Bearer {GITHUB_TOKEN}"}) as client:
        while len(repos) < limit:
            resp = client.get(
                f"{GITHUB_API}/search/repositories",
                params={
                    "q": "stars:>100 archived:false fork:false",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": per_page,
                    "page": page,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            if not items:
                break
            for item in items:
                repos.append({
                    "full_name": item["full_name"],
                    "stars": item["stargazers_count"],
                    "language": item.get("language"),
                    "default_branch": item.get("default_branch", "main"),
                })
            page += 1
            # GitHub search API: max 1000 results
            if len(items) < per_page:
                break

    return repos[:limit]


def download_and_scan(repo: dict, rules: list) -> dict:
    """Download a repo tarball, scan it, return findings."""
    full_name = repo["full_name"]
    result = {
        "repo": full_name,
        "stars": repo["stars"],
        "language": repo["language"],
        "findings": [],
        "files_scanned": 0,
        "error": None,
    }

    try:
        with httpx.Client(timeout=60, headers={"Authorization": f"Bearer {GITHUB_TOKEN}"}) as client:
            # Download tarball
            resp = client.get(
                f"{GITHUB_API}/repos/{full_name}/tarball/{repo['default_branch']}",
                follow_redirects=True,
            )
            if resp.status_code != 200:
                result["error"] = f"HTTP {resp.status_code}"
                return result

            with tempfile.TemporaryDirectory(prefix="driftguard_scan_") as tmpdir:
                tarball = Path(tmpdir) / "repo.tar.gz"
                tarball.write_bytes(resp.content)

                # Extract
                import tarfile
                with tarfile.open(tarball, "r:gz") as tar:
                    tar.extractall(tmpdir, filter="data")

                # Find the extracted dir (usually <repo-name>-<sha>)
                extracted = [d for d in Path(tmpdir).iterdir() if d.is_dir()]
                if not extracted:
                    result["error"] = "No directory after extraction"
                    return result

                scan_dir = extracted[0]
                findings, files_scanned = scan_directory(str(scan_dir), rules)
                result["findings"] = [
                    {
                        "rule_id": f.rule_id,
                        "provider": f.provider,
                        "title": f.title,
                        "severity": f.severity,
                        "file": f.file,
                        "line": f.line,
                        "match": f.match,
                    }
                    for f in findings
                ]
                result["files_scanned"] = files_scanned

    except Exception as e:
        result["error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(description="Scan top GitHub repos for breaking API changes")
    parser.add_argument("--limit", type=int, default=1000, help="Number of repos to scan")
    parser.add_argument("--workers", type=int, default=4, help="Parallel workers")
    parser.add_argument("--output", type=str, default="scan_results.json", help="Output JSON file")
    parser.add_argument("--markdown", type=str, default="scan_results.md", help="Output markdown summary")
    args = parser.parse_args()

    if not GITHUB_TOKEN:
        print("Error: set GITHUB_TOKEN env var (needs public repo read access)")
        sys.exit(1)

    print(f"Fetching top {args.limit} repos from GitHub…")
    repos = fetch_top_repos(args.limit)
    print(f"Got {len(repos)} repos. Loading rules…")

    rules = load_rules()
    print(f"Loaded {len(rules)} rules. Starting scan with {args.workers} workers…")

    all_results = []
    completed = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(download_and_scan, repo, rules): repo for repo in repos}

        for future in as_completed(futures):
            completed += 1
            repo = futures[future]
            try:
                result = future.result()
                all_results.append(result)
                n_findings = len(result["findings"])
                status = f"{n_findings} findings" if n_findings else "clean"
                if result["error"]:
                    status = f"ERROR: {result['error']}"
                print(f"  [{completed}/{len(repos)}] {repo['full_name']} — {status}")
            except Exception as e:
                print(f"  [{completed}/{len(repos)}] {repo['full_name']} — FAILED: {e}")
                all_results.append({
                    "repo": repo["full_name"],
                    "stars": repo["stars"],
                    "language": repo["language"],
                    "findings": [],
                    "files_scanned": 0,
                    "error": str(e),
                })

            # Rate limit: GitHub allows 5000 req/hour with token
            if completed % 50 == 0:
                print("  … pausing 2s for rate limit …")
                time.sleep(2)

    # Write JSON
    with open(args.output, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nJSON results: {args.output}")

    # Aggregate stats
    total_repos = len(all_results)
    repos_with_findings = sum(1 for r in all_results if r["findings"])
    repos_with_errors = sum(1 for r in all_results if r["error"])
    total_findings = sum(len(r["findings"]) for r in all_results)

    sev_counts = Counter()
    provider_counts = Counter()
    rule_counts = Counter()
    repos_by_provider = defaultdict(set)

    for r in all_results:
        for f in r["findings"]:
            sev_counts[f["severity"]] += 1
            provider_counts[f["provider"]] += 1
            rule_counts[f["rule_id"]] += 1
            repos_by_provider[f["provider"]].add(r["repo"])

    # Write markdown summary
    with open(args.markdown, "w") as f:
        f.write("# DriftGuard Scan: Top GitHub Repositories\n\n")
        f.write(f"Scanned **{total_repos}** repositories (most starred, non-archived, non-fork).\n\n")
        f.write("## Summary\n\n")
        f.write("| Metric | Value |\n|---|---|\n")
        f.write(f"| Repos scanned | {total_repos} |\n")
        f.write(f"| Repos with findings | {repos_with_findings} ({repos_with_findings/total_repos*100:.1f}%) |\n")
        f.write(f"| Repos with errors | {repos_with_errors} |\n")
        f.write(f"| Total findings | {total_findings} |\n")
        f.write(f"| Critical | {sev_counts['critical']} |\n")
        f.write(f"| Warning | {sev_counts['warning']} |\n")
        f.write(f"| Info | {sev_counts['info']} |\n\n")

        f.write("## Findings by provider\n\n")
        f.write("| Provider | Findings | Repos affected |\n|---|---|---|\n")
        f.writelines(f"| {provider} | {count} | {len(repos_by_provider[provider])} |\n" for provider, count in provider_counts.most_common())

        f.write("\n## Top 20 rules triggered\n\n")
        f.write("| Rule | Count |\n|---|---|\n")
        f.writelines(f"| {rule_id} | {count} |\n" for rule_id, count in rule_counts.most_common(20))

        f.write("\n## Top 20 affected repos\n\n")
        f.write("| Repo | Stars | Language | Findings |\n|---|---|---|---|\n")
        top_affected = sorted(
            [r for r in all_results if r["findings"]],
            key=lambda r: len(r["findings"]),
            reverse=True,
        )[:20]
        for r in top_affected:
            f.write(f"| [{r['repo']}](https://github.com/{r['repo']}) | {r['stars']} | {r['language']} | {len(r['findings'])} |\n")

    print(f"Markdown summary: {args.markdown}")
    print(f"\nDone. {repos_with_findings}/{total_repos} repos have findings ({repos_with_findings/total_repos*100:.1f}%).")


if __name__ == "__main__":
    main()
