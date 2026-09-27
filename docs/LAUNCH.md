# 🚀 Plan de lancement public (Phase 2 — S4)

Objectif : 30+ installs de la GitHub App, 100+ étoiles, premiers retours qualitatifs.

## Pré-requis avant lancement

- [ ] La GitHub App tourne en prod (VPS) et scanne 3-5 repos réels sans faux positif
- [ ] GIF de démo (10 s) : un push sur un repo de test → issue DriftGuard ouverte
- [ ] README avec : badge, table des règles couvertes, install en 2 clics
- [ ] Le repo public `jcalhinho/driftguard` avec CI verte

## Séquence de lancement (sur 2 semaines)

| J | Action | Cible |
|---|---|---|
| J-2 | Beta privée : installer l'app sur 10 repos amis, corriger les faux positifs | 10 repos réels |
| J1 | **Post r/webdev** : « I built the Dependabot for APIs — it scans your code for breaking API changes and opens fix PRs » | Premier trafic + feedback |
| J3 | **Show HN** : « Show HN: DriftGuard — Dependabot for APIs (YC requested this, I built it) » | Hacker News |
| J5 | **Product Hunt** (gratuit) : tagline « Your code breaks when Stripe changes its API. DriftGuard finds it first. » | Visibilité produit |
| J7 | **Post r/opensource + r/javascript** : le format de règles YAML contribuable | Contributeurs |
| J14 | Bilan : installs, PRs mergées, faux positifs → ajustements | Décision phase 3 |

## Titres & pitchs prêts à coller

**Show HN :**
> Show HN: DriftGuard — the Dependabot for APIs. It watches breaking changes from
> Stripe, GitHub, Slack & OpenAI, scans your repos, and opens fix PRs. Free for public
> repos. YC's latest RFS asked for exactly this — I built the open-source core.

**r/webdev :**
> 30% of AWS outages came from undetected API changes. Dependabot handles packages,
> nothing handles APIs — so I built DriftGuard: it scans your code for deprecated API
> usage (stripe.charges, text-davinci-003, legacy Slack tokens…) and opens a PR with
> the fix + migration link. Free for public repos, rules are open YAML.

**Product Hunt tagline :**
> Your code breaks when APIs change. DriftGuard finds it before your users do.

## Métriques à suivre

- Installs GitHub App (Settings → Installations)
- PRs ouvertes vs mergées (le ratio = la qualité des corrections)
- Faux positifs signalés par les utilisateurs (le ratio critique = la confiance)
- Étoiles/fourches du repo
