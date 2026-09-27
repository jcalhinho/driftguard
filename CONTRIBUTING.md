# 🤝 Contribuer — écrire une règle DriftGuard

Les règles sont **le cœur du produit** : chaque breaking change documenté devient une
détection. Écrire une règle prend 5 minutes.

## Format (rules/rules.yaml)

```yaml
- id: stripe-charges-api-deprecated      # unique : provider-slug-court
  provider: Stripe
  title: "L'API Charges est dépréciée — utilisez Payment Intents"
  severity: critical                     # info | warning | critical
  patterns:                              # regex Python, une ou plusieurs
    - "stripe\\.charges\\.create"
  fix_hint: "Remplacer par stripe.paymentIntents.create()."
  migration: "https://docs.stripe.com/payments/payment-intents/migration"
  replace:                               # optionnel : remplacement mécanique sûr
    "stripe.charges.create": "stripe.paymentIntents.create"
  since: "2026-09-27"
```

## Critères d'acceptation

1. **Un vrai breaking change** — avec un lien de migration officiel (jamais une simple
   bonne pratique : celles-là vont dans des linters, pas ici).
2. **Pattern précis** — il doit matcher l'usage réel sans matcher n'importe quoi.
   Teste sur `tests/fixtures/sample_repo/` en ajoutant ton cas.
3. **fix_hint actionnable** — ce que le dev doit faire, en une phrase.
4. **`replace` seulement si sûr** — remplacement mécanique sans ambiguïté ; sinon,
   ne pas mettre de `replace` (le mode issue s'en charge).

## Process

1. Fork → nouvelle branche `rules/<id>`
2. Ajoute la règle + un usage dans `tests/fixtures/sample_repo/`
3. Ajuste les comptes dans `tests/test_engine.py`
4. `pytest -q && ruff check .` → PR

## Vérifications automatiques (CI)

- `pytest -q` : la fixture doit détecter ton usage, lignes exactes
- `ruff check .` : style du moteur
- La règle doit être valide YAML (champs requis, id unique, regex compilable)
