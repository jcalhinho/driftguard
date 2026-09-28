# 🛠️ Setup — running DriftGuard as a service (30 minutes)

Two manual steps (impossible to automate for you): **create the GitHub App** and
**deploy the service**. Everything else is already coded.

## 1. Create the GitHub App (github.com)

1. **GitHub → Settings → Developer settings → GitHub Apps → New GitHub App**
2. Name: `DriftGuard` — Homepage URL: your repo URL
3. **Webhook URL**: `https://YOUR-DOMAIN/webhook` (or a smee.io URL for local testing)
4. **Webhook secret**: generate a long secret (and put it in `.env`)
5. **Permissions** (Repository):
   - `Contents` → **Read & write** (for fix PRs)
   - `Pull requests` → **Read & write**
   - `Issues` → **Read & write**
   - `Metadata` → Read-only (default)
6. **Events to subscribe**: `Push`, `Pull request`, `Installation`
7. Create the app → note the **App ID** → **Generate a private key** (download the `.pem`)

## 2. Configure the service

```bash
cd app
cp .env.example .env
# Fill GITHUB_APP_ID and GITHUB_WEBHOOK_SECRET
cp ../deploy/driftguard-key.pem .   # the downloaded private key
```

## 3. Run (development)

```bash
cd driftguard
python3 -m venv .venv && .venv/bin/pip install -e ".[app]"
set -a && source app/.env && set +a
.venv/bin/uvicorn app.main:app --port 8000
# Test: curl http://localhost:8000/health
```

## 4. Run (production, VPS + Docker)

```bash
# On your VPS: clone the repo, then
cd deploy
export GITHUB_APP_ID=123456 GITHUB_WEBHOOK_SECRET=...
docker compose up -d --build
# Behind a reverse proxy (nginx/caddy) with HTTPS to localhost:8000
```

## 5. Install the app on a repo

On github.com: **Settings → GitHub Apps → DriftGuard → Install** → pick a public repo.
On the next push, DriftGuard scans and opens an issue (or a PR if the repo has
`.driftguard.yml` with `mode: pr`).

## 6. Per-repo configuration (.driftguard.yml at the repo root)

```yaml
mode: issue            # issue (default) | pr
min_severity: warning  # info | warning | critical
ignore_rules:
  - slack-legacy-tokens
only_providers:        # optional: restrict to specific providers
  - Stripe
```

## Troubleshooting

- `Invalid signature` → the webhook secret doesn't match `.env`
- `Failed to get installation token` → wrong private key or App ID
- Webhook receives nothing → check the public URL (smee/ngrok when local)
