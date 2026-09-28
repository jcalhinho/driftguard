# 🚀 Public launch plan (Phase 2 — W4)

Goal: 30+ GitHub App installs, 100+ stars, first quality feedback.

## Pre-launch checklist

- [ ] GitHub App running in prod (VPS) and scanning 3-5 real repos with zero false positives
- [ ] Demo GIF (10 s): a push on a test repo → DriftGuard issue opened
- [ ] README with: badge, covered-rules table, 2-click install
- [ ] Public repo `jcalhinho/driftguard` with green CI
- [ ] **GitHub App set to "Any account"** (see [PRE-LAUNCH-CHECKLIST.md](./PRE-LAUNCH-CHECKLIST.md))
- [ ] **Stable webhook URL** (named Cloudflare tunnel or Caddy, not quick tunnel)
- [ ] **Landing page live** on GitHub Pages (`docs/index.html` → `jcalhinho.github.io/driftguard`)
- [ ] **Online scanner** working on the landing page
- [ ] **Scan of top 1000 repos** completed, stats integrated into launch posts

## Assets

- **Landing page + online scanner**: `docs/index.html` — deploy via GitHub Pages
- **Repo scan script**: `scripts/scan_popular_repos.py` — `GITHUB_TOKEN=xxx python scripts/scan_popular_repos.py --limit 1000`
- **Pre-launch checklist**: `docs/PRE-LAUNCH-CHECKLIST.md`

## Launch sequence (over 2 weeks)

| Day | Action | Target |
|---|---|---|
| D-2 | Private beta: install the app on 10 friend repos, fix false positives | 10 real repos |
| D1 | **r/webdev post**: "I built the Dependabot for APIs — it scans your code for breaking API changes and opens fix PRs" | First traffic + feedback |
| D3 | **Show HN**: "Show HN: DriftGuard — Dependabot for APIs (YC requested this, I built it)" | Hacker News |
| D5 | **Product Hunt** (free): tagline "Your code breaks when Stripe changes its API. DriftGuard finds it first." | Product visibility |
| D7 | **r/opensource + r/javascript post**: the contributable YAML rule format | Contributors |
| D14 | Review: installs, merged PRs, false positives → adjust | Phase 3 decision |

## Ready-to-paste titles & pitches

**Show HN:**
> Show HN: DriftGuard — the Dependabot for APIs. It watches breaking changes from
> OpenAI, Anthropic, Google, GitHub Actions, Stripe, Slack, AWS…, scans your repos, and
> opens an issue (or a fix PR) with the migration guide. Free for everyone, open source.

**r/webdev:**
> Dependabot handles packages, nothing handles the APIs your code calls — so I built
> DriftGuard: it finds retired models (gpt-4-32k, claude-3-opus…), removed endpoints
> (Slack files.upload, Assistants API) and dead CI runners, with the official migration
> link. One line in a workflow, free for everyone, 53 rules as open YAML.

**Product Hunt tagline:**
> Your code breaks when APIs change. DriftGuard finds it before your users do.

## Metrics to track

- GitHub App installs (Settings → Installations)
- PRs opened vs merged (the ratio = fix quality)
- User-reported false positives (the critical ratio = trust)
- Repo stars/forks
