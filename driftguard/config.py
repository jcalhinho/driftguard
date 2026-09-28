"""Per-repo configuration: a .driftguard.yml file at the repo root."""

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

import yaml

DEFAULT_CONFIG = {
    "mode": "issue",            # issue | pr
    "min_severity": "warning",  # info | warning | critical
    "ignore_rules": [],
    "only_providers": [],
    "ignore_paths": [],         # glob patterns, e.g. "tests/**", "docs/*.md"
}

SEVERITY_RANK = {"info": 0, "warning": 1, "critical": 2}


@dataclass
class RepoConfig:
    mode: str = "issue"
    min_severity: str = "warning"
    ignore_rules: list = field(default_factory=list)
    only_providers: list = field(default_factory=list)
    ignore_paths: list = field(default_factory=list)


def load_repo_config(repo_dir: Path) -> RepoConfig:
    """Read .driftguard.yml when present, otherwise return the default config."""
    config_file = Path(repo_dir) / ".driftguard.yml"
    if not config_file.is_file():
        return RepoConfig(**DEFAULT_CONFIG)
    try:
        data = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    # Unknown keys are ignored rather than crashing the scan.
    merged = {**DEFAULT_CONFIG, **{k: v for k, v in data.items() if k in DEFAULT_CONFIG}}
    for key in ("ignore_rules", "only_providers", "ignore_paths"):
        if not isinstance(merged[key], list):
            merged[key] = [merged[key]] if merged[key] else []
    if merged["mode"] not in ("issue", "pr"):
        merged["mode"] = "issue"
    if merged["min_severity"] not in SEVERITY_RANK:
        merged["min_severity"] = "warning"
    return RepoConfig(**merged)


def filter_findings(findings: list, config: RepoConfig) -> list:
    """Apply min_severity, ignore_rules and only_providers."""
    out = []
    for f in findings:
        if SEVERITY_RANK[f.rule.severity] < SEVERITY_RANK[config.min_severity]:
            continue
        if f.rule.id in config.ignore_rules:
            continue
        if any(_path_matches(f.file, p) for p in config.ignore_paths):
            continue
        if config.only_providers and f.rule.provider.lower() not in {
            p.lower() for p in config.only_providers
        }:
            continue
        out.append(f)
    return out


def _path_matches(path: str, pattern: str) -> bool:
    path = path.replace("\\", "/")
    pattern = pattern.rstrip("/")
    # "tests" or "tests/**" ignores the whole directory.
    pattern = pattern.removesuffix("/**")
    return fnmatch(path, pattern) or path.startswith(pattern + "/")
