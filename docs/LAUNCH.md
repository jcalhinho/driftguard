# 🚀 Public launch plan (Phase 2 — W4)

Goal: 30+ GitHub App installs, 100+ stars, first quality feedback.

## Pre-launch checklist

- [ ] GitHub App running in prod (VPS) and scanning 3-5 real repos with zero false positives
- [ ] Demo GIF (10 s): a push on a test repo → DriftGuard issue opened
- [ ] README with: badge, covered-rules table, 2-click install
- [ ] Public repo `jcalhinho/driftguard` with green CI

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
> Stripe, GitHub, Slack & OpenAI, scans your repos, and opens fix PRs. Free for public
> repos. YC's latest RFS asked for exactly this — I built the open-source core.

**r/webdev:**
> 30% of AWS outages came from undetected API changes. Dependabot handles packages,
> nothing handles APIs — so I built DriftGuard: it scans your code for deprecated API
> usage (stripe.charges, text-davinci-003, legacy Slack tokens…) and opens a PR with
> the fix + migration link. Free for public repos, rules are open YAML.

**Product Hunt tagline:**
> Your code breaks when APIs change. DriftGuard finds it before your users do.

## Metrics to track

- GitHub App installs (Settings → Installations)
- PRs opened vs merged (the ratio = fix quality)
- User-reported false positives (the critical ratio = trust)
- Repo stars/forks
