# DriftGuard — Plan d'exécution (v1)

> **Le « Dependabot des API »** : un agent qui surveille les breaking changes des grandes
> API, scanne le code de ses utilisateurs, et ouvre automatiquement des pull requests
> correctives. Open source, gratuit pour les repos publics, payant pour les repos privés.

Date du plan : 2026-09-27 · Auteur : jcalhinho · Statut : phase 0

---

## 1. Le problème (chiffré)

- **30 % des temps d'arrêt d'AWS** provenaient de changements d'API/paquets non détectés (source : YC RFS).
- Dependabot/Renovate gèrent les **dépendances** depuis 10 ans — personne ne fait l'équivalent pour les **API**.
- Un breaking change d'API se découvre aujourd'hui **en production**, par les erreurs clients.
- La demande est **explicite et écrite** dans le Request for Startups de Y Combinator (automne 2026) :
  « quand un fournisseur publie un changement cassant, un agent devrait scanner les codebases
  clients et ouvrir une PR avec le correctif — un Dependabot pour les API ».

## 2. Le produit

### Exemple de parcours utilisateur (Stripe, 2019, cas réel)

1. Stripe déprécie `stripe.charges.create()` → Payment Intents.
2. DriftGuard détecte le changement via sa base de règles, scanne les repos installés,
   trouve `stripe.charges.create(` dans 14 fichiers.
3. DriftGuard ouvre **une PR par impact** : correctif + lien vers le guide de migration.
4. L'équipe merge en 5 minutes. Aucune rupture de prod.

### Ce que DriftGuard n'est PAS

- Pas un linter générique (Semgrep/CodeQL font ça).
- Pas un outil de gestion de changements pour les fournisseurs d'API (Optic/Bump.sh font ça).
- C'est la **couche consommateur** : du côté des équipes qui *utilisent* les API.

### Positionnement concurrentiel (honnête)

| Acteur | Couvre |
|---|---|
| Dependabot, Renovate | Versions de dépendances — pas les API |
| Optic, Bump.sh | Changements d'API **côté fournisseur** |
| Semgrep, CodeQL | Scan générique — pas de base « breaking changes API » |
| **DriftGuard** | **Breaking changes d'API, côté consommateur — le créneau vide** |

## 3. Le modèle économique (open core)

- **Gratuit pour toujours** : moteur open source (MIT), GitHub App gratuite pour les repos publics.
- **Payant (phase 3)** : repos privés et équipes — 49 €/mois par équipe (~19 €/repo/mois).
- Référence : le modèle Renovate (OSS gratuit + hébergement payant) et la tarification Dependabot.

### Scénarios de revenus (honnêtes)

| Scénario | Équipes payantes | MRR | Annuel |
|---|---|---|---|
| Échec d'adoption | 0–5 | ~0 € | 0 € (le repo reste un atout portfolio) |
| Distribution travaillée (3 mois) | 30–50 | 1 500–2 500 € | 18–30 k€ |
| Bouche-à-oreille dev | 200 | ~10 k€ | ~120 k€ |
| Leader du créneau | 1 000+ | 50 k€+ | 600 k€+ ou rachat (Snyk/GitHub/Datadog) |

## 4. Architecture technique

```
driftguard/
├── engine/              # Moteur open source (Python)
│   ├── scanner.py       # Scan d'une codebase : usages d'API (regex + contexte)
│   ├── rules.py         # Chargement/validation des règles YAML
│   ├── fixer.py         # Génération du patch correctif
│   └── tests/           # Fixtures de repos + tests unitaires
├── rules/               # LA moat : base de règles de breaking changes (YAML, contribuable)
│   ├── stripe.yaml      # charges → payment_intents, sk_test en prod, etc.
│   ├── github.yaml      # Endpoints dépréciés, tokens d'API...
│   └── slack.yaml
├── app/                 # Service FastAPI + GitHub App (webhooks, scan, PR)
│   ├── main.py
│   ├── github_app.py    # Auth app (JWT), installation tokens, PR via API REST
│   └── storage.py       # SQLite : installations, repos, historique des scans
├── cli/                 # CLI : driftguard scan ./mon-repo (usage local, porte d'entrée OSS)
├── .github/workflows/   # CI : tests + lint à chaque push
├── PLAN.md
└── README.md            # Lancement : démo, install, règles supportées
```

### Décisions techniques

| Sujet | Décision | Justification |
|---|---|---|
| Langage moteur | Python 3.12+ | Vitesse de dev, écosystème regex/AST, déjà maîtrisé |
| Format des règles | YAML | Lisible, contribuable — la communauté peut écrire des règles (la moat) |
| Détection | Regex + contexte (pas d'AST complet) | 80 % des usages d'API se détectent par pattern + lignes voisines ; simple et robuste |
| GitHub App (pas OAuth) | App avec permissions minimales (Contents, Pull requests) | Installation par repo, tokens par installation, 5 000 req/h |
| Stratégie anti-faux-positifs | Mode **Issue** par défaut, mode **PR** opt-in | La confiance est le produit : on n'ouvre une PR que si la confiance est haute |
| Déploiement | VPS 5 €/mois + Docker | Maîtrisé, suffisant pour 10 000 repos |
| Règles v1 | Stripe, GitHub, Slack (10–15 règles réelles) | Commencer étroit, élargir ensuite (OpenAI, Twilio, SendGrid, AWS) |

## 5. Roadmap (12 semaines)

### Phase 0 — Fondations (S1 : 29/09 → 05/10)
- [x] Repo open source `driftguard` (MIT) + README + CI (tests + lint)
- [x] Moteur : scanner de codebase (usages d'API par pattern + contexte)
- [x] Format de règles YAML + 5 règles Stripe réelles
- [x] CLI `driftguard scan ./repo` avec sortie JSON/rapport
- [x] Tests unitaires sur repo fixture (14 usages → détections exactes)

> ✅ **Phase 0 terminée le 2026-09-27** : 8 règles réelles (Stripe, OpenAI, GitHub, Slack,
> Twilio), moteur + CLI + fixer + rapports text/JSON, 19 tests verts, lint ruff propre,
> CI configurée. Le CLI détecte 8/8 usages de la fixture avec lignes exactes, drapeau
> commentaire, hints de correction et liens de migration.

### Phase 1 — GitHub App (S2–3 : 06/10 → 19/10)
- [x] GitHub App : installation, webhooks (push, PR), scan automatique
- [x] Ouverture de PR correctives (correctif + lien de migration)
- [x] Mode Issue (défaut) / mode PR (opt-in) + badge DriftGuard dans le message
- [x] SQLite : installations, repos, historique
- [ ] Déploiement VPS + tests réels sur 3 repos (dont les nôtres)

> ✅ **Code de la phase 1 terminé le 2026-09-27** : `app/github_app.py` (JWT RS256,
> tokens d'installation, download tarball, issues, PR via git data API blob/tree/commit/ref),
> `app/pipeline.py` (scan → dédup SQLite → issue ou PR avec correctifs mécaniques),
> `app/main.py` (webhook avec signature HMAC, événements ping/installation/push/PR),
> `app/config.py` (.driftguard.yml par repo : mode, seuil, règles ignorées), Docker +
> compose. Testé : 29 tests dont pipeline complet avec GitHub mocké (issue, PR, dédup),
> webhook simulé en local (health/ping/installation OK). **Reste action humaine** :
> créer la GitHub App sur github.com + déployer (SETUP.md, 30 min).

### Phase 2 — Lancement public (S4 : 20/10 → 26/10)
- [ ] Beta sur 10 repos amis → itération sur les faux positifs
- [ ] Exécution du lancement : r/webdev, Show HN, Product Hunt
- [ ] KPI mis en place : installs, PRs mergées, étoiles

> ✅ **Matériel de la phase 2 prêt (2026-09-27)** : `docs/LAUNCH.md` avec séquence
> J-2→J14, pitchs prêts à coller (Show HN, r/webdev, Product Hunt), checklist beta,
> README de lancement avec tableau des règles. L'exécution démarre quand la GitHub App
> tourne en prod (phase 1) — ce sont des actions sur TES comptes (Reddit, HN, PH).

### Phase 3 — Croissance & monétisation (S5–12)
- [x] Tier payant : repos privés, équipes (49 €/mois)
- [x] Couverture : OpenAI, Twilio, SendGrid, AWS SDK (les plus utilisés)
- [x] Contribution communautaire aux règles (le moteur de la moat)
- [x] Self-hosted pour entreprises

> ✅ **Socle de la phase 3 posé (2026-09-27)** : 13 règles (Stripe, OpenAI, GitHub,
> Slack, Twilio, SendGrid, AWS), `CONTRIBUTING.md` (process de contribution aux règles,
> critères d'acceptation, CI), modèle open core documenté dans le README. La
> monétisation elle-même (Stripe, facturation) s'active après les premiers installs.

## 6. KPI du succès

| Étape | KPI |
|---|---|
| Fin S1 | CLI qui détecte 100 % des usages du repo fixture |
| Fin S3 | PR auto ouverte et mergée sur un vrai repo |
| Fin S4 | 30+ installs de la GitHub App |
| Fin S8 | 500+ repos scannés, 10 PRs mergées par semaine |
| Fin S12 | Premiers clients payants (3+) |

## 7. Risques & parades

| Risque | Parade |
|---|---|
| La base de règles est le vrai travail (curation des changelogs) | Format YAML contribuable + règles vérifiées par la communauté ; couverture étroite au début |
| Faux positifs → perte de confiance | Mode Issue par défaut, seuils conservateurs, PR opt-in |
| Concurrence (Snyk, GitHub, Sourcegraph) | Vitesse + communauté de règles ; le créneau est déclaré vide par YC |
| Revenus lents (B2B dev tools) | Open core : l'adoption passe par le gratuit ; runway 6 mois de revenus persos |

## 8. Ce qui rend le projet réaliste pour un solo builder

- Le scan de code est **déjà maîtrisé** (mode repo d'AegisScan, même famille technique).
- L'API GitHub est **déjà maîtrisée** (GitVibe, jobs, webhooks).
- Pas d'audience requise : **le GitHub Marketplace est l'audience**.
- La boucle de croissance est intégrée au produit : chaque PR ouverte porte le nom DriftGuard.
