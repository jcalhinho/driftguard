# 🛡️ DriftGuard

**The "Dependabot for APIs"** — watches breaking changes from major APIs, scans your code,
and automatically opens fix pull requests.

> 30% of AWS outages came from undetected API changes. Dependabot handles dependencies —
> DriftGuard handles the APIs your code consumes.

## How it works

1. Stripe deprecates an endpoint → the DriftGuard rules base learns about it
2. DriftGuard scans your repo and finds the affected usages (exact file + line)
3. DriftGuard opens an **issue** (default) or a **fix PR** (`.driftguard.yml` with
   `mode: pr`): fix + official migration guide
4. You merge in 5 minutes. Zero production breakage.

## Install

**GitHub App** (free for public repos): see [SETUP.md](./SETUP.md) — app creation,
VPS deployment, install on your repos in 2 clicks.

**CLI** (local scan in 2 minutes):

```bash
pip install -e .
driftguard scan ./my-repo           # text report
driftguard scan ./my-repo --format json --min-severity critical
driftguard rules                    # list the active rules
```

## Rules covered (13)

| Provider | Rule | Severity |
|---|---|---|
| Stripe | Charges API deprecated → Payment Intents | 🔴 critical |
| Stripe | Sources API deprecated → Payment Methods | 🟠 warning |
| Stripe | API version pinned to an old year | 🔵 info |
| OpenAI | `text-davinci-003` / `code-davinci-002` shut down | 🔴 critical |
| OpenAI | Legacy `/completions` endpoint phased out | 🟠 warning |
| GitHub | OAuth password grant disabled | 🔴 critical |
| GitHub | `Authorization: token` header → Bearer | 🔵 info |
| Slack | `rtm.start` deprecated → `rtm.connect` | 🟠 warning |
| Slack | Legacy tokens (`xoxp-`/`xoxo-`) retired | 🔴 critical |
| Twilio | Lookups v1 deprecated → v2 | 🟠 warning |
| Twilio | Plain-text credentials in the URL | 🟠 warning |
| SendGrid | v2 API (basic auth) retired → v3 Bearer | 🟠 warning |
| AWS | S3 path-style URLs deprecated | 🔵 info |

Rules are **contributable YAML**: see [CONTRIBUTING.md](./CONTRIBUTING.md) — 5 minutes per
rule, the community expands the coverage.

## Model

- **Open source (MIT)**: engine, rules, CLI
- **Free**: public repos, forever
- **Paid (coming)**: private repos / teams — €49/month per team

## Structure

```
engine/    # Engine: scanner, rules, fixer, reports (Python, tested)
rules/     # Breaking-change rules base (YAML, contributable)
app/       # GitHub App: webhooks, JWT, issues, PRs via the git data API
cli.py     # CLI: driftguard scan|rules
deploy/    # Docker + compose
docs/      # Launch plan (LAUNCH.md)
tests/     # 29 tests: engine + app + CLI
```

## Quality

- ✅ 29 tests (pytest): engine, webhook signature, JWT, issue/PR pipeline, dedup
- ✅ Ruff lint, GitHub Actions CI
- ✅ False-positive safety: issue mode by default, comment detection, SQLite dedup,
  per-repo severity thresholds

## Roadmap

- [x] **Phase 0** — Engine + CLI + rules (done)
- [x] **Phase 1** — GitHub App + automatic PRs (code done — app creation & deployment
  remain: see SETUP.md)
- [ ] **Phase 2** — Public launch (see docs/LAUNCH.md)
- [ ] **Phase 3** — Paid tier + expanded coverage
