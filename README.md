# 🛡️ DriftGuard

**Le « Dependabot des API »** — surveille les breaking changes des grandes API, scanne ton
code, et ouvre automatiquement des pull requests correctives.

> 30 % des temps d'arrêt d'AWS venaient de changements d'API non détectés. Dependabot gère
> les dépendances — DriftGuard gère les API que ton code consomme.

## Comment ça marche

1. Stripe déprécie un endpoint → la base de règles DriftGuard l'apprend
2. DriftGuard scanne ton repo, trouve les usages affectés (fichier + ligne exacte)
3. DriftGuard ouvre une **issue** (défaut) ou une **PR corrective** (`.driftguard.yml` avec
   `mode: pr`) : correctif + guide de migration officiel
4. Tu merges en 5 minutes. Aucune rupture de prod.

## Installation

**GitHub App** (gratuite pour les repos publics) : voir [SETUP.md](./SETUP.md) — création
de l'app, déploiement VPS, installation sur tes repos en 2 clics.

**CLI** (scan local en 2 minutes) :

```bash
pip install -e .
driftguard scan ./mon-repo           # rapport texte
driftguard scan ./mon-repo --format json --min-severity critical
driftguard rules                     # liste les règles actives
```

## Règles couvertes (13)

| Provider | Règle | Sévérité |
|---|---|---|
| Stripe | API Charges dépréciée → Payment Intents | 🔴 critical |
| Stripe | API Sources dépréciée → Payment Methods | 🟠 warning |
| Stripe | Version d'API épinglée à une année ancienne | 🔵 info |
| OpenAI | `text-davinci-003` / `code-davinci-002` retirés | 🔴 critical |
| OpenAI | Endpoint legacy `/completions` en fin de vie | 🟠 warning |
| GitHub | Flux OAuth par mot de passe désactivé | 🔴 critical |
| GitHub | En-tête `Authorization: token` → Bearer | 🔵 info |
| Slack | `rtm.start` déprécié → `rtm.connect` | 🟠 warning |
| Slack | Tokens legacy (`xoxp-`/`xoxo-`) retirés | 🔴 critical |
| Twilio | Lookups v1 dépréciée → v2 | 🟠 warning |
| Twilio | Identifiants en clair dans l'URL | 🟠 warning |
| SendGrid | API v2 (basic auth) retirée → v3 Bearer | 🟠 warning |
| AWS | URLs S3 path-style dépréciées | 🔵 info |

Les règles sont du **YAML contribuable** : [CONTRIBUTING.md](./CONTRIBUTING.md) — 5 minutes
par règle, c'est la communauté qui élargit la couverture.

## Modèle

- **Open source (MIT)** : moteur, règles, CLI
- **Gratuit** : repos publics, pour toujours
- **Payant (à venir)** : repos privés / équipes — 49 €/mois par équipe

## Structure

```
engine/    # Moteur : scanner, règles, fixer, rapports (Python, testé)
rules/     # Base de règles de breaking changes (YAML, contribuable)
app/       # GitHub App : webhooks, JWT, issues, PR via git data API
cli.py     # CLI : driftguard scan|rules
deploy/    # Docker + compose
docs/      # Plan de lancement (LAUNCH.md)
tests/     # 29 tests : moteur + app + CLI
```

## Qualité

- ✅ 29 tests (pytest) : moteur, signature webhook, JWT, pipeline issue/PR, anti-doublons
- ✅ Lint ruff, CI GitHub Actions
- ✅ Anti-faux-positifs : mode issue par défaut, détection des commentaires,
  anti-doublons SQLite, seuils de sévérité par repo

## Roadmap

- [x] **Phase 0** — Moteur + CLI + règles (terminé)
- [x] **Phase 1** — GitHub App + PR automatiques (code terminé — reste la création de
  l'app et le déploiement : voir SETUP.md)
- [ ] **Phase 2** — Lancement public (voir docs/LAUNCH.md)
- [ ] **Phase 3** — Tier payant + couverture élargie
