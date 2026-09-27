# 🛠️ Setup — mettre DriftGuard en service (30 minutes)

Deux étapes manuelles (impossibles à automatiser pour toi) : **créer la GitHub App**
et **déployer le service**. Tout le reste est déjà codé.

## 1. Créer la GitHub App (github.com)

1. **GitHub → Settings → Developer settings → GitHub Apps → New GitHub App**
2. Nom : `DriftGuard` — Homepage URL : l'URL de ton repo
3. **Webhook URL** : `https://TON-DOMAINE/webhook` (ou une URL smee.io pendant les tests locaux)
4. **Webhook secret** : génère un secret long (et mets-le dans `.env`)
5. **Permissions** (Repository) :
   - `Contents` → **Read & write** (pour les PR correctives)
   - `Pull requests` → **Read & write**
   - `Issues` → **Read & write**
   - `Metadata` → Read-only (par défaut)
6. **Events à souscrire** : `Push`, `Pull request`, `Installation`
7. Créer l'app → noter l'**App ID** → **Generate a private key** (télécharge le `.pem`)

## 2. Configurer le service

```bash
cd app
cp .env.example .env
# Renseigner GITHUB_APP_ID, GITHUB_WEBHOOK_SECRET
cp ../deploy/driftguard-key.pem .   # la clé privée téléchargée
```

## 3. Lancer (développement)

```bash
cd driftguard
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r app/requirements.txt -e .
set -a && source app/.env && set +a
.venv/bin/uvicorn app.main:app --port 8000
# Test : curl http://localhost:8000/health
```

## 4. Lancer (production, VPS + Docker)

```bash
# Sur ton VPS : clone du repo, puis
cd deploy
export GITHUB_APP_ID=123456 GITHUB_WEBHOOK_SECRET=...
docker compose up -d --build
# Derrière un reverse proxy (nginx/caddy) avec HTTPS vers localhost:8000
```

## 5. Installer l'app sur un repo

Sur github.com : **Settings → GitHub Apps → DriftGuard → Install** → choisis un repo public.
Dès le prochain push, DriftGuard scanne et ouvre une issue (ou une PR si le repo a
`.driftguard.yml` avec `mode: pr`).

## 6. Configuration par repo (.driftguard.yml à la racine du repo)

```yaml
mode: issue            # issue (défaut) | pr
min_severity: warning  # info | warning | critical
ignore_rules:
  - slack-legacy-tokens
only_providers:        # optionnel : restreindre à certains fournisseurs
  - Stripe
```

## Dépannage

- `Signature invalide` → le secret du webhook ne correspond pas à celui de `.env`
- `Échec du token d'installation` → clé privée ou App ID erronés
- Le webhook ne reçoit rien → vérifier l'URL publique (smee/ngrok en local)
