# DriftGuard — Execution plan (v1)

> **The "Dependabot for APIs"**: an agent that watches breaking changes from major APIs,
> scans users' code, and automatically opens fix pull requests. Open source, free for
> public repos, paid for private repos.

Plan date: 2026-09-27 · Author: jcalhinho · Status: phases 0-1 code complete

---

## 1. The problem (with numbers)

- **30% of AWS outages** came from undetected API/package changes (source: YC RFS).
- Dependabot/Renovate have handled **dependencies** for 10 years — nobody does the
  equivalent for **APIs**.
- Today, an API breaking change is discovered **in production**, through customer errors.
- The demand is **explicit and written** in Y Combinator's Request for Startups
  (Fall 2026): "when a provider publishes a breaking change, an agent should scan client
  codebases and open a PR with the fix — a Dependabot for APIs".

## 2. The product

### Example user journey (Stripe, 2019, real case)

1. Stripe deprecates `stripe.charges.create()` → Payment Intents.
2. DriftGuard learns the change through its rules base, scans installed repos,
   finds `stripe.charges.create(` in 14 files.
3. DriftGuard opens **one PR per impact**: fix + migration guide link.
4. The team merges in 5 minutes. Zero production breakage.

### What DriftGuard is NOT

- Not a generic linter (Semgrep/CodeQL do that).
- Not a change-management tool for API providers (Optic/Bump.sh do that).
- It's the **consumer layer**: for teams that *use* APIs.

### Honest competitive positioning

| Player | Covers |
|---|---|
| Dependabot, Renovate | Dependency versions — not APIs |
| Optic, Bump.sh | API changes **on the provider side** |
| Semgrep, CodeQL | Generic scanning — no "API breaking changes" base |
| **DriftGuard** | **API breaking changes, consumer side — the empty niche** |

## 3. Business model (open core)

- **Free forever**: open-source engine (MIT), free GitHub App for public repos.
- **Paid (phase 3)**: private repos and teams — €49/month per team (~€19/repo/month).
- Reference: Renovate's model (free OSS + paid hosting) and Dependabot pricing.

### Honest revenue scenarios

| Scenario | Paying teams | MRR | Yearly |
|---|---|---|---|
| Adoption failure | 0–5 | ~€0 | €0 (the repo remains a portfolio asset) |
| Worked distribution (3 months) | 30–50 | €1,500–2,500 | €18–30k |
| Dev word-of-mouth | 200 | ~€10k | ~€120k |
| Niche leader | 1,000+ | €50k+ | €600k+ or acquisition (Snyk/GitHub/Datadog) |

## 4. Technical architecture

```
driftguard/
├── driftguard/          # Open-source engine + CLI (Python)
│   ├── scanner.py       # Codebase scan: API usage (regex + context)
│   ├── rules.py         # YAML rules loading/validation
│   ├── fixer.py         # Fix patch generation
│   └── tests/           # Fixture repos + unit tests
├── rules/               # THE moat: breaking-change rules base (YAML, contributable)
├── app/                 # FastAPI service + GitHub App (webhooks, scan, PR)
├── cli/                 # CLI: driftguard scan ./my-repo
├── bench/               # Rust scanner benchmark (performance experiment)
├── .github/workflows/   # CI: tests + lint on every push
├── PLAN.md
└── README.md
```

### Technical decisions

| Topic | Decision | Rationale |
|---|---|---|
| Engine language | Python 3.10+ | Dev speed, regex/AST ecosystem, already mastered |
| Rules format | YAML | Readable, contributable — the community can write rules (the moat) |
| Detection | Regex + context (no full AST) | 80% of API usage is detected by pattern + neighboring lines; simple and robust |
| GitHub App (not OAuth) | App with minimal permissions (Contents, Pull requests) | Per-repo install, per-installation tokens, 5,000 req/h |
| Anti-false-positive strategy | **Issue** mode by default, **PR** mode opt-in | Trust is the product: a PR is opened only with high confidence |
| Deployment | €5/month VPS + Docker | Mastered, enough for 10,000 repos |
| v1 rules | Stripe, GitHub, Slack (10–15 real rules) | Start narrow, expand later (OpenAI, Twilio, SendGrid, AWS) |

## 5. Roadmap (12 weeks)

### Phase 0 — Foundations (W1)
- [x] Open-source repo `driftguard` (MIT) + README + CI (tests + lint)
- [x] Engine: codebase scanner (API usage by pattern + context)
- [x] YAML rules format + real Stripe rules
- [x] CLI `driftguard scan ./repo` with JSON/report output
- [x] Unit tests on fixture repo (exact detections)

> ✅ **Phase 0 done 2026-09-27**: engine + CLI + fixer + text/JSON reports, 29 tests
> green, clean ruff lint, CI configured. The CLI detects 8/8 fixture usages with exact
> lines, comment flag, fix hints and migration links.

### Phase 1 — GitHub App (W2–3)
- [x] GitHub App: installation, webhooks (push, PR), automatic scan
- [x] Fix PR opening (fix + migration link)
- [x] Issue mode (default) / PR mode (opt-in)
- [x] SQLite: installations, repos, history
- [ ] VPS deployment + real tests on 3 repos

> ✅ **Phase 1 code done 2026-09-27**: `app/github_app.py` (RS256 JWT, installation
> tokens, tarball download, issues, PRs via git data API), `app/pipeline.py`
> (scan → SQLite dedup → issue or PR with mechanical fixes), `app/main.py` (HMAC-signed
> webhook, ping/installation/push/PR events), `app/config.py` (.driftguard.yml per repo),
> Docker + compose. Tested: 29 tests including the full pipeline with a mocked GitHub
> (issue, PR, dedup), local webhook simulation OK. **Remaining human actions**: create
> the GitHub App on github.com + deploy (SETUP.md, 30 min).

### Phase 2 — Public launch (W4)
- [ ] Beta on 10 friend repos → false-positive iteration
- [ ] Launch execution: r/webdev, Show HN, Product Hunt
- [ ] KPIs in place: installs, merged PRs, stars

> ✅ **Phase 2 material ready 2026-09-27**: `docs/LAUNCH.md` with D-2→D14 sequence,
> ready-to-paste pitches (Show HN, r/webdev, Product Hunt), beta checklist, launch
> README with rules table. Execution starts once the GitHub App runs in prod — these
> are actions on YOUR accounts (Reddit, HN, PH).

### Phase 3 — Growth & monetization (W5–12)
- [x] Paid tier groundwork: private repos, teams (€49/month)
- [x] Coverage: OpenAI, Twilio, SendGrid, AWS (the most-used ones)
- [x] Community rule contribution (the moat engine)
- [x] Self-hosted for enterprises

> ✅ **Phase 3 groundwork laid 2026-09-27**: 13 rules (Stripe, OpenAI, GitHub, Slack,
> Twilio, SendGrid, AWS), `CONTRIBUTING.md` (rule contribution process, acceptance
> criteria, CI), open-core model documented in the README. Billing itself (Stripe)
> activates after the first installs.

## 6. Success KPIs

| Milestone | KPI |
|---|---|
| End of W1 | CLI detects 100% of fixture usages |
| End of W3 | Auto PR opened and merged on a real repo |
| End of W4 | 30+ GitHub App installs |
| End of W8 | 500+ scanned repos, 10 merged PRs/week |
| End of W12 | First paying customers (3+) |

## 7. Risks & mitigations

| Risk | Mitigation |
|---|---|
| The rules base is the real work (changelog curation) | Contributable YAML format + community-verified rules; narrow coverage at first |
| False positives → lost trust | Issue mode by default, conservative thresholds, opt-in PRs |
| Competition (Snyk, GitHub, Sourcegraph) | Speed + rule community; the niche is declared empty by YC |
| Slow revenue (B2B dev tools) | Open core: adoption flows through the free tier; 6-month personal runway |

## 8. Why this is realistic for a solo builder

- Code scanning is **already mastered** (AegisScan repo mode, same technical family).
- The GitHub API is **already mastered** (GitVibe, jobs, webhooks).
- No audience required: **the GitHub Marketplace is the audience**.
- The growth loop is built into the product: every opened PR carries the DriftGuard name.
