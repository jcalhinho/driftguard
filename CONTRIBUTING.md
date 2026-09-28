# Contributing a rule

DriftGuard is only as good as its rules base. A new rule takes about 10 minutes: one YAML
entry in [driftguard/data/rules.yaml](./driftguard/data/rules.yaml), no Python.

## Format

```yaml
- id: openai-gpt4-32k-shutdown          # unique, provider-slug — never renamed once merged
  provider: OpenAI
  title: gpt-4-32k models are shut down
  severity: critical                     # critical | warning | info (see below)
  effective: '2025-06-06'                # when the change took / takes effect upstream
  patterns:                              # Python regexes, single-quoted ('' for a quote)
    - '\bgpt-4-32k(?:-\d{4})?\b'
  files: ['.github/workflows/*']         # optional: restrict to matching paths
  examples:                              # real code lines that MUST be detected
    - 'model="gpt-4-32k-0613"'
  counter_examples:                      # look-alikes that must NOT be detected
    - 'model="gpt-4o"'
  fix_hint: Use gpt-4o or gpt-4.1 (larger context, lower price).
  migration: https://developers.openai.com/api/docs/deprecations
  since: '2026-09-28'                    # date the rule is added
```

**Severity**
- `critical` — requests fail today (model retired, endpoint removed, runner gone)
- `warning` — shutdown announced with a date, or the SDK is out of support
- `info` — legacy: still works, worth planning

## Acceptance criteria

1. **A real breaking change**, backed by the provider's own announcement in `migration`
   (not a blog post, not a best practice — those belong in linters).
2. **A precise pattern.** Add `examples` in the shapes people actually write (Python, JS,
   YAML…) and `counter_examples` for the current, valid equivalent. The test suite scans
   every example and counter-example.
3. **An actionable `fix_hint`** — what to do, in one sentence.
4. **`replace` only when strictly equivalent** — same arguments, same behaviour (e.g.
   `actions/cache@v2` → `actions/cache@v4`). It is committed as-is in PR mode, so a rename
   to an API with a different signature (Charges → PaymentIntents, rtm.start →
   rtm.connect) does NOT qualify: omit it and the finding is reported as an issue.

## Process

1. Fork → branch `rules/<id>`
2. Add the rule with its examples and counter-examples
3. `pytest -q && ruff check .`
4. Regenerate the README table: `driftguard rules --format markdown`
5. Open the PR with the link to the official announcement
