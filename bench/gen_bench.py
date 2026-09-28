"""Generate a synthetic corpus (fixture duplicated N times) + rules.json for the benchmark.

Usage: python3 bench/gen_bench.py <corpus_dir> <copies>
"""

import json
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "sample_repo"
RULES_YAML = ROOT / "driftguard" / "data" / "rules.yaml"


def main() -> int:
    corpus_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/driftguard-corpus")
    copies = int(sys.argv[2]) if len(sys.argv) > 2 else 300

    # Corpus : fixture dupliquée N fois dans des sous-dossiers.
    if corpus_dir.exists():
        shutil.rmtree(corpus_dir)
    corpus_dir.mkdir(parents=True)
    for i in range(copies):
        dest = corpus_dir / f"repo_{i:04d}"
        shutil.copytree(FIXTURE, dest)

    # rules.json : mêmes règles (id/patterns) pour le scanner Rust.
    data = yaml.safe_load(RULES_YAML.read_text(encoding="utf-8"))
    rules = [
        {
            "id": r["id"],
            "provider": r.get("provider", "?"),
            "title": r.get("title", r["id"]),
            "severity": r["severity"],
            "patterns": r["patterns"],
        }
        for r in data["rules"]
    ]
    out = ROOT / "bench" / "rules.json"
    out.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")

    files = sum(1 for _ in corpus_dir.rglob("*") if _.is_file())
    print(f"corpus: {corpus_dir} ({files} files, {copies} copies) · rules.json: {len(rules)} rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
