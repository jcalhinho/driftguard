# DriftGuard — Launch Posts

Based on a read-only scan of the 250 most-starred public GitHub repos (September 2026).

## LinkedIn

```
40% of the top 250 GitHub repositories contain broken API calls.

I know because I scanned them all.

When OpenAI shuts down gpt-4-32k, when Slack retires files.upload, when
GitHub Actions cache@v2 stops working — your code breaks silently. Users
hit the errors first. You find out from a bug report at 2am.

Dependabot keeps your dependencies fresh. But nobody watches the APIs
those dependencies call. So I built DriftGuard — the Dependabot for APIs.

It scans your code for breaking API changes: retired AI models, removed
endpoints, sunset SDKs, dead CI runners. 53 rules across 16 providers
(OpenAI, Anthropic, Google, Stripe, GitHub, Slack, AWS…). All in plain
YAML — anyone can contribute a rule in 10 minutes.

I ran it against the 250 most-starred repos on GitHub:

• 101 repos (40.4%) have broken API calls
• 8,065 total findings — 92% are critical (the calls fail today)
• Even openai/openai-cookbook has 513 broken calls
• microsoft/vscode has 121

The top 3 broken providers:
1. OpenAI — 2,844 findings (retired models, old SDK, Assistants API)
2. Anthropic — 2,423 findings (claude-3-opus, claude-3.5-sonnet)
3. Google — 2,264 findings (Gemini 1.x, PaLM, Universal Analytics)

DriftGuard is free, open source (MIT), and runs three ways:
→ GitHub App: installs on your repos, opens issues and fix PRs automatically
→ GitHub Action: inline annotations on your pull requests
→ CLI: scan locally in one command

There's also an online scanner — paste code, see what breaks, no install:
https://jcalhinho.github.io/driftguard/

Repo: https://github.com/jcalhinho/driftguard

If your team uses OpenAI, Anthropic, Google, Stripe, Slack, or AWS in
production — you probably have broken API calls right now. DriftGuard
finds them before your users do.

#opensource #developer #api #github #devtools #ai
```

## Key stats

- **40.4% of the top 250 GitHub repos contain broken API calls** (101/250)
- **8,065 total findings** — 7,459 critical (calls that fail today)
- Top 3 affected providers: OpenAI (2,844 findings / 47 repos), Anthropic (2,423 / 45), Google (2,264 / 55)
- Most triggered rule: retired Claude models (2,423 hits across 45 repos)
- Even `openai/openai-cookbook` has 513 findings

---

## Show HN

**Title:**

```
Show HN: DriftGuard – The Dependabot for APIs (40% of top GitHub repos have broken API calls)
```

**Body:**

```
Hi HN,

Dependabot keeps your dependencies up to date, but nothing watches the APIs your
code calls. When OpenAI shuts down gpt-4-32k, when Slack retires files.upload,
when actions/cache@v2 stops working — your code breaks silently. Users hit errors
first, you find out from a GitHub issue at 2am.

I built DriftGuard to fix this. It scans your code for breaking API changes —
retired AI models, removed endpoints, sunset SDKs, dead CI runners — and opens
a GitHub issue (or a fix PR when a safe mechanical fix exists) with the migration
guide. 53 rules across 16 providers, all in plain YAML.

I ran it against the 250 most-starred repos on GitHub. Results:

- 40.4% have broken API calls (101 repos)
- 8,065 total findings, 92% critical (calls that fail today)
- OpenAI is #1 (2,844 findings in 47 repos) — retired models like gpt-4-32k,
  o1-preview, dall-e-3, the old Assistants API
- Anthropic is #2 (2,423 findings in 45 repos) — claude-3-opus, claude-3.5-sonnet
  and other retired models
- Google is #3 (2,264 findings in 55 repos) — Gemini 1.x, PaLM, Universal Analytics
- Even openai/openai-cookbook has 513 findings

Three ways to use it:
1. GitHub App — install on your repos, it scans on every push and opens issues/PRs
2. GitHub Action — add it to a workflow, get inline PR annotations
3. CLI — `pip install` and scan locally

There's also an online scanner on the landing page — paste code, see what breaks:
https://jcalhinho.github.io/driftguard/

Free for everyone (public + private repos), MIT licensed, self-hostable on a GCP
free-tier VM. Rules are community-contributed YAML — adding a rule takes 10 minutes.

I'd love feedback on the rule coverage and false positive rate. What APIs would
you want covered?

https://github.com/jcalhinho/driftguard
```

---

## r/webdev

**Title:**

```
40% of the top 250 GitHub repos have broken API calls — I built a tool that finds them
```

**Body:**

```
Dependabot handles your npm/pip packages. But what about the APIs those packages
call? When Stripe changes its API, when OpenAI shuts down a model, when GitHub
retires a runner image — nothing tells you. Your code just breaks.

I built DriftGuard: it scans your code for breaking API changes and opens a GitHub
issue with the migration guide. Or a fix PR, when the fix is mechanical
(e.g. actions/cache@v2 → @v4).

I scanned the 250 most-starred GitHub repos. 40.4% have broken API calls:

- openai/openai-cookbook: 513 findings (retired models, old SDK, Assistants API)
- microsoft/vscode: 121 findings
- vercel/next.js: 25 findings
- n8n-io/n8n: 446 findings
- langflow-ai/langflow: 498 findings

Most common: retired AI models (gpt-4-32k, claude-3-opus, gemini-1.5) and
dead GitHub Actions (cache@v2, upload-artifact@v3, ubuntu-20.04 runners).

Try it now — paste code in the online scanner (no install):
https://jcalhinho.github.io/driftguard/

Or install the GitHub App / Action:
https://github.com/jcalhinho/driftguard

Free, open source (MIT), 53 rules, 16 providers. Rules are YAML — contribute
your own in 10 minutes.
```

---

## r/programming

**Title:**

```
40% of the top 250 GitHub repos contain broken API calls — I scanned them all
```

**Body:**

```
I built a tool called DriftGuard that scans code for breaking API changes —
retired AI models, removed endpoints, sunset SDKs, dead CI runners. Then I ran
it against the 250 most-starred repos on GitHub.

40.4% have broken API calls. 8,065 findings total. The most common:

1. Retired Claude models (claude-3-opus, claude-3.5-sonnet) — 2,423 hits in 45 repos
2. Gemini 1.x shut down — 1,219 hits in 55 repos
3. OpenAI o1-preview/mini shut down — 609 hits
4. DALL-E 2/3 shut down — 421 hits
5. GPT-3 completion models (text-davinci-003) — 305 hits
6. AWS SDK v2 end of support — 253 hits
7. GitHub Actions cache@v2 broken — part of 25 findings across 9 repos

These are all calls that fail today. Not deprecation warnings — the APIs are
gone, the models are shut down, the runners don't exist.

The tool is open source (MIT), free for everyone, and runs as a GitHub App,
GitHub Action, or CLI. There's also a browser-based scanner on the landing page.

https://github.com/jcalhinho/driftguard
https://jcalhinho.github.io/driftguard/
```

---

## Product Hunt

**Tagline:**

```
Your code breaks when APIs change. DriftGuard finds it first.
```

**Description:**

```
DriftGuard is the Dependabot for APIs. It scans your code for breaking API
changes — retired AI models (gpt-4-32k, claude-3-opus, gemini-1.5), removed
endpoints (Slack files.upload, OpenAI Assistants API), sunset SDKs (AWS SDK v2,
google-generativeai), and dead CI runners (ubuntu-20.04, actions/cache@v2).

We scanned the 250 most-starred GitHub repos: 40.4% have broken API calls.
8,065 findings. 92% are critical — the calls fail today.

DriftGuard opens a GitHub issue with the migration guide, or a fix PR when a
safe mechanical fix exists. 53 rules, 16 providers, all in contributable YAML.

Free for everyone. Open source (MIT). Install the GitHub App, add the GitHub
Action, or use the CLI. Try the online scanner — paste code, see what breaks.

🔗 https://github.com/jcalhinho/driftguard
```

---

## dev.to

**Title:**

```
I scanned the top 250 GitHub repos for broken API calls — 40% have them
```

**Body:**

```
Dependabot keeps your dependencies fresh. But who watches the APIs those
dependencies call?

When OpenAI shuts down gpt-4-32k, when Slack retires files.upload, when
actions/cache@v2 stops working — your code breaks. Silently. Users hit the
errors first.

I built [DriftGuard](https://github.com/jcalhinho/driftguard) — an open-source
tool that scans code for breaking API changes. 53 rules across 16 providers,
all in plain YAML. It runs as a GitHub App (opens issues/PRs automatically),
a GitHub Action (inline PR annotations), or a CLI.

Then I ran it against the 250 most-starled repos on GitHub.

## The results

| Metric | Value |
|---|---|
| Repos scanned | 250 |
| Repos with broken API calls | 101 (40.4%) |
| Total findings | 8,065 |
| Critical (calls fail today) | 7,459 (92%) |

## Top 5 most affected repos

| Repo | Findings |
|---|---|
| lobehub/lobehub | 1,584 |
| headroomlabs-ai/headroom | 819 |
| openai/openai-cookbook | 513 |
| google-gemini/gemini-cli | 511 |
| langflow-ai/langflow | 498 |

## What's broken?

The top 3 providers:

1. **OpenAI** (2,844 findings, 47 repos) — retired models (gpt-4-32k, o1-preview,
   dall-e-3), the old Assistants API, pre-1.0 SDK interface
2. **Anthropic** (2,423 findings, 45 repos) — claude-3-opus, claude-3.5-sonnet,
   and other retired models
3. **Google** (2,264 findings, 55 repos) — Gemini 1.x, Gemini 2.0 Flash, PaLM API,
   Universal Analytics, the old google-generativeai SDK

But it's not just AI: AWS SDK v2 (end of support), GitHub Actions (cache@v2,
upload-artifact@v3, ubuntu-20.04 runners), Slack (files.upload, legacy
conversation methods), Stripe (Charges API, redirectToCheckout)...

## Try it

- **Online scanner** (paste code, no install): https://jcalhinho.github.io/driftguard/
- **GitHub App** (auto issues/PRs): https://github.com/apps/driftguardbot
- **GitHub Action** (inline annotations): see the README
- **CLI**: `pip install git+https://github.com/jcalhinho/driftguard`

Free for everyone, open source (MIT). Rules are YAML — contribute your own in
10 minutes.
```

---

## Twitter / X

```
I scanned the 250 most-starred GitHub repos for broken API calls.

40.4% have them. 8,065 findings. 92% critical — the calls fail today.

Top 3 broken providers:
1. OpenAI — 2,844 findings (retired models, old SDK, Assistants API)
2. Anthropic — 2,423 findings (claude-3-opus, claude-3.5-sonnet)
3. Google — 2,264 findings (Gemini 1.x, PaLM, Universal Analytics)

Even openai/openai-cookbook has 513 broken calls.

I built DriftGuard to fix this — the Dependabot for APIs:
🤖 GitHub App (auto issues + fix PRs)
⚡ GitHub Action (inline annotations)
💻 CLI (local scan)
🔍 Online scanner (paste code, see what breaks)

Free, open source, 53 rules, 16 providers.

https://github.com/jcalhinho/driftguard
https://jcalhinho.github.io/driftguard/
```
