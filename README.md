# 🛡️ DriftGuard

**The Dependabot for APIs.** Dependabot keeps your dependencies up to date — DriftGuard
finds the API calls in your code that a provider has shut down or is about to: retired
AI models, removed endpoints, sunset SDKs, dead CI runners.

```
📄 src/llm.py
  🔴 [critical] L12   Retired Claude model — requests to it fail
         ↳ model="claude-3-opus-20240229"
         💡 Move to a current model (claude-sonnet-4-6, claude-opus-4-8 or claude-haiku-4-5).
         🔗 https://platform.claude.com/docs/en/about-claude/model-deprecations
```

## Quick start

### GitHub Action (recommended — nothing to host)

```yaml
# .github/workflows/driftguard.yml
name: DriftGuard
on: [push, pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: jcalhinho/driftguard@v1
        with:
          min-severity: warning      # info | warning | critical
          # fail-on-findings: "false"
          # ignore: "tests/** docs/**"
```

Findings show up as inline annotations on the affected lines of your pull requests.

### CLI

```bash
pip install git+https://github.com/jcalhinho/driftguard
driftguard scan .                                   # human-readable report
driftguard scan . --min-severity critical --format json
driftguard scan . --ignore 'tests/**' --only OpenAI
driftguard rules                                    # list the rules
```

Exit code is `1` when something is found (use `--no-fail` to only report).

### GitHub App (issues and fix PRs, automatically)

Install the app on your repos: it scans them right away, then on every push to the default
branch, and opens an **issue** listing what breaks — or a **fix PR** when a safe mechanical
fix exists and the repo opts in with `mode: pr`. Self-hosting: see [SETUP.md](./SETUP.md).

## Configuration

Optional `.driftguard.yml` at the repo root — read by the CLI, the Action and the App:

```yaml
mode: issue              # App only: issue (default) | pr
min_severity: warning    # info | warning | critical
ignore_rules:            # rule ids, see `driftguard rules`
  - stripe-pinned-old-api-version
ignore_paths:            # globs
  - tests/**
  - docs/**
only_providers: []       # e.g. [OpenAI, Stripe]
```

To silence a single line, add a `driftguard: ignore` comment on it:

```python
MODEL = "gpt-4-32k"  # driftguard: ignore — archived benchmark, never called
```

**Severities** — 🔴 **critical**: calls fail today · 🟠 **warning**: shutdown announced or SDK
unsupported · 🔵 **info**: legacy, plan the migration.

## Rules covered (53)

Every rule links to the provider's official announcement, carries the date the change took
effect, and ships with examples and counter-examples that the test suite checks.

| Provider | Breaking change | Severity | Effective |
|---|---|---|---|
| Anthropic | [Retired Claude model — requests to it fail](https://platform.claude.com/docs/en/about-claude/model-deprecations) | 🔴 critical | — |
| Apple | [The Dark Sky API is shut down](https://developer.apple.com/weatherkit/get-started/) | 🔴 critical | 2023-03-31 |
| AWS | [Deprecated AWS Lambda runtime (no patches; updates get blocked)](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html#runtimes-deprecated) | 🟠 warning | — |
| AWS | [AWS SDK for JavaScript v2 (aws-sdk) reached end of support](https://aws.amazon.com/blogs/developer/announcing-end-of-support-for-aws-sdk-for-javascript-v2/) | 🟠 warning | 2025-09-08 |
| AWS | [S3 path-style URLs are deprecated (unsupported for buckets created after 2020-09-30)](https://aws.amazon.com/blogs/aws/amazon-s3-path-deprecation-plan-the-rest-of-the-story/) | 🔵 info | — |
| Firebase | [Firebase Dynamic Links is shut down (all links return 404)](https://firebase.google.com/support/dynamic-links-faq) | 🔴 critical | 2025-08-25 |
| Firebase | [FCM legacy HTTP/XMPP APIs are shut down](https://firebase.google.com/docs/cloud-messaging/send/v1-api) | 🔴 critical | 2024-07-22 |
| GitHub | [Authenticating with ?access_token= in the URL is no longer supported](https://developer.github.com/changes/2020-02-10-deprecating-auth-through-query-param/) | 🔴 critical | — |
| GitHub | [actions/upload-artifact and download-artifact v1–v3 fail](https://github.blog/changelog/2024-04-16-deprecation-notice-v3-of-the-artifact-actions/) | 🔴 critical | 2025-01-30 |
| GitHub | [actions/cache v1 and v2 no longer work](https://github.blog/changelog/2024-12-05-notice-of-upcoming-releases-and-breaking-changes-for-github-actions/) | 🔴 critical | 2025-02-01 |
| GitHub | [Retired GitHub-hosted runner image (jobs never start)](https://github.com/actions/runner-images#available-images) | 🔴 critical | — |
| GitHub | [The OAuth Authorizations API (/authorizations) was removed](https://developer.github.com/changes/2020-02-14-deprecating-oauth-auth-endpoint/) | 🔴 critical | 2020-11-13 |
| GitHub | [The OAuth password grant flow is disabled](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps) | 🔴 critical | — |
| Google | [Gemini 1.0 and 1.5 models are shut down (requests return 404)](https://ai.google.dev/gemini-api/docs/deprecations) | 🔴 critical | 2025-09-24 |
| Google | [Gemini 2.0 Flash models are shut down](https://ai.google.dev/gemini-api/docs/deprecations) | 🔴 critical | 2026-06-01 |
| Google | [The Google Image Charts API (chart.googleapis.com/chart) is shut down](https://developers.google.com/chart/image) | 🔴 critical | — |
| Google | [Google Optimize has been shut down](https://support.google.com/optimize/answer/12979939) | 🔴 critical | 2023-09-30 |
| Google | [The PaLM API (text-bison, chat-bison) is shut down](https://ai.google.dev/gemini-api/docs/migrate) | 🔴 critical | — |
| Google | [Universal Analytics (UA-… properties, analytics.js) stopped processing data](https://support.google.com/analytics/answer/11583528) | 🔴 critical | 2023-07-01 |
| Google | [The google-generativeai / @google/generative-ai SDKs are deprecated and unsupported](https://ai.google.dev/gemini-api/docs/migrate) | 🟠 warning | 2025-11-30 |
| Google | [The Google Sign-In platform library (gapi.auth2) is deprecated](https://developers.google.com/identity/sign-in/web/deprecation-and-sunset) | 🟠 warning | 2023-03-31 |
| IEX | [IEX Cloud is shut down](https://en.wikipedia.org/wiki/Investors_Exchange) | 🔴 critical | 2024-08-31 |
| Meta | [The Instagram Basic Display API is shut down](https://developers.facebook.com/blog/post/2024/09/04/update-on-instagram-basic-display-api/) | 🔴 critical | 2024-12-04 |
| Microsoft | [Azure AD Graph (graph.windows.net) is retired](https://learn.microsoft.com/en-us/graph/migrate-azure-ad-graph-overview) | 🔴 critical | 2025-08-31 |
| Microsoft | [ADAL authentication libraries are out of support](https://learn.microsoft.com/en-us/entra/identity-platform/msal-migration) | 🟠 warning | 2023-06-30 |
| MongoDB | [Atlas Data API, App Services and Device Sync are shut down](https://www.mongodb.com/docs/atlas/app-services/deprecation/) | 🔴 critical | 2025-09-30 |
| OpenAI | [The Assistants API is shut down](https://developers.openai.com/api/docs/assistants/migration) | 🔴 critical | 2026-08-26 |
| OpenAI | [chatgpt-4o-latest is shut down](https://developers.openai.com/api/docs/deprecations) | 🔴 critical | 2026-02-17 |
| OpenAI | [codex-mini-latest is shut down](https://developers.openai.com/api/docs/deprecations) | 🔴 critical | 2026-02-12 |
| OpenAI | [dall-e-2 and dall-e-3 are shut down](https://developers.openai.com/api/docs/deprecations) | 🔴 critical | 2026-05-12 |
| OpenAI | [The /v1/edits endpoint is shut down](https://developers.openai.com/api/docs/deprecations) | 🔴 critical | 2024-01-04 |
| OpenAI | [GPT-3 completion models (text-davinci-003, text-curie-001, code-davinci-002…) are shut down](https://developers.openai.com/api/docs/deprecations) | 🔴 critical | 2024-01-04 |
| OpenAI | [GPT-3 similarity/search embedding models are shut down](https://developers.openai.com/api/docs/deprecations) | 🔴 critical | 2024-01-04 |
| OpenAI | [gpt-3.5-turbo-0301 / -0613 / -16k-0613 snapshots are shut down](https://developers.openai.com/api/docs/deprecations) | 🔴 critical | 2024-09-13 |
| OpenAI | [gpt-4-32k models are shut down](https://developers.openai.com/api/docs/deprecations) | 🔴 critical | 2025-06-06 |
| OpenAI | [gpt-4-turbo-preview / gpt-4-1106-preview are shut down](https://developers.openai.com/api/docs/deprecations) | 🔴 critical | 2026-03-26 |
| OpenAI | [gpt-4-vision-preview is shut down](https://developers.openai.com/api/docs/deprecations) | 🔴 critical | 2024-12-06 |
| OpenAI | [gpt-4.5-preview is shut down](https://developers.openai.com/api/docs/deprecations) | 🔴 critical | 2025-07-14 |
| OpenAI | [o1-preview (2025-07-28) and o1-mini (2025-10-27) are shut down](https://developers.openai.com/api/docs/deprecations) | 🔴 critical | 2025-10-27 |
| OpenAI | [gpt-4o-realtime-preview / gpt-4o-audio-preview are shut down](https://developers.openai.com/api/docs/deprecations) | 🔴 critical | 2026-05-07 |
| OpenAI | [The Realtime API beta interface is shut down](https://developers.openai.com/api/docs/deprecations) | 🔴 critical | 2026-05-12 |
| OpenAI | [Pre-1.0 OpenAI SDK interface (openai.ChatCompletion.create, OpenAIApi) was removed](https://github.com/openai/openai-python/discussions/742) | 🟠 warning | 2023-11-06 |
| SendGrid | [The v2 Web API with username/password (api_user) is retired](https://www.twilio.com/docs/sendgrid/for-developers/sending-email/upgrade-your-authentication-method-to-api-keys) | 🟠 warning | — |
| Slack | [files.upload is retired](https://docs.slack.dev/changelog/2024-04-a-better-way-to-upload-files-is-here-to-stay/) | 🔴 critical | 2025-11-12 |
| Slack | [channels.*, groups.*, im.* and mpim.* methods are retired](https://api.slack.com/changelog/2020-01-deprecating-antecedents-to-the-conversations-api) | 🔴 critical | 2021-02-24 |
| Slack | [rtm.start is deprecated — use rtm.connect (or the Events API / Socket Mode)](https://api.slack.com/methods/rtm.connect) | 🟠 warning | — |
| Stripe | [The Charges API is legacy and cannot handle SCA / 3D Secure](https://docs.stripe.com/payments/payment-intents/migration) | 🟠 warning | — |
| Stripe | [stripe.redirectToCheckout() is removed from Stripe.js](https://docs.stripe.com/changelog/clover/2025-09-30/remove-redirect-to-checkout) | 🟠 warning | 2025-09-30 |
| Stripe | [The Sources API is deprecated](https://docs.stripe.com/payments/payment-methods/transitioning) | 🟠 warning | — |
| Stripe | [Stripe API version pinned to a pre-2020 release](https://docs.stripe.com/upgrades) | 🔵 info | — |
| Twilio | [Twilio Programmable Video reaches end of life on 2026-12-05](https://help.twilio.com/articles/20950630029595-Programmable-Video-End-of-Life-Notice) | 🟠 warning | 2026-12-05 |
| Twilio | [Lookup v1 is superseded by Lookup v2](https://www.twilio.com/docs/lookup/v2-api) | 🔵 info | — |
| Yahoo | [YQL (query.yahooapis.com) is shut down](https://developer.yahoo.com/yql/) | 🔴 critical | 2019-01-03 |

Missing an API? Rules are plain YAML — see [CONTRIBUTING.md](./CONTRIBUTING.md), about
10 minutes per rule.

## How it stays trustworthy

- **Issues by default.** A PR is only opened for strictly equivalent replacements
  (e.g. `actions/cache@v2` → `@v4`); everything else is reported, never rewritten.
- **No noise on every push.** Each finding is reported once, keyed on the code itself —
  not the line number — so editing a file doesn't re-open issues.
- **Read-only scan.** The App downloads a tarball of the default branch into a temporary
  directory and deletes it after the scan; nothing is executed.

## Project layout

```
driftguard/        # Engine + CLI: scanner, rules loader, fixer, reports
driftguard/data/   # The rules base (rules.yaml)
app/               # GitHub App service (FastAPI): webhooks, issues, PRs
action.yml         # GitHub Action
deploy/            # Dockerfile + compose
bench/             # Rust scanner benchmark
tests/             # pytest suite (engine, every rule, app, CLI)
```

## Pricing

- **Open source (MIT)**: engine, rules, CLI, Action
- **GitHub App**: free for public repositories
- **Private repositories / teams**: coming soon

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[app,dev]"
.venv/bin/pytest -q && .venv/bin/ruff check .
```
