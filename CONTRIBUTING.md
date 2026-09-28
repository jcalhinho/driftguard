# 🤝 Contributing — writing a DriftGuard rule

Rules are **the heart of the product**: every documented breaking change becomes a
detection. Writing a rule takes 5 minutes.

## Format (driftguard/data/rules.yaml)

```yaml
- id: stripe-charges-api-deprecated      # unique: provider-short-slug
  provider: Stripe
  title: "The Charges API is deprecated — use Payment Intents"
  severity: critical                     # info | warning | critical
  patterns:                              # Python regex, one or more
    - "stripe\\.charges\\.create"
  fix_hint: "Replace with stripe.paymentIntents.create()."
  migration: "https://docs.stripe.com/payments/payment-intents/migration"
  # no `replace`: Payment Intents takes different arguments, so it is not a drop-in fix
  since: "2026-09-27"
```

## Acceptance criteria

1. **A real breaking change** — with an official migration link (never a mere best
   practice: those belong in linters, not here).
2. **A precise pattern** — it must match the real usage without matching anything else.
   Test it against `tests/fixtures/sample_repo/` by adding your case.
3. **An actionable fix_hint** — what the developer should do, in one sentence.
4. **`replace` only when strictly equivalent** — same arguments, same response (e.g.
   `Authorization: token` → `Bearer`). It is committed as-is in PR mode, so a rename to
   an API with a different signature (Charges → PaymentIntents, rtm.start → rtm.connect)
   does NOT qualify: omit it and the finding is reported as an issue.

## Process

1. Fork → new branch `rules/<id>`
2. Add the rule + one usage in `tests/fixtures/sample_repo/`
3. Adjust the counts in `tests/test_engine.py`
4. `pytest -q && ruff check .` → PR

## Automated checks (CI)

- `pytest -q`: the fixture must detect your usage with exact lines
- `ruff check .`: engine style
- The rule must be valid YAML (required fields, unique id, compilable regex)
