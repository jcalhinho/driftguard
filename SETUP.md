# 🛠️ Setup — running DriftGuard as a service (30 minutes)

Two manual steps (impossible to automate for you): **create the GitHub App** and
**deploy the service**. Everything else is already coded.

## 1. Create the GitHub App (github.com)

1. **GitHub → Settings → Developer settings → GitHub Apps → New GitHub App**
2. Name: `DriftGuard` — Homepage URL: your repo URL
3. **Webhook URL**: `https://YOUR-DOMAIN/webhook` (or a smee.io URL for local testing)
4. **Webhook secret**: `openssl rand -hex 32` (and put it in `.env`) — **required**, the
   service rejects every webhook (503) without it
5. **Permissions** (Repository):
   - `Contents` → **Read & write** (for fix PRs)
   - `Pull requests` → **Read & write**
   - `Issues` → **Read & write**
   - `Metadata` → Read-only (default)
6. **Events to subscribe**: `Push` (installation events are always delivered to apps)
7. Create the app → note the **App ID** → **Generate a private key** (download the `.pem`)

## 2. Configure the service

```bash
cp app/.env.example app/.env
# Fill GITHUB_APP_ID and GITHUB_WEBHOOK_SECRET
mv ~/Downloads/<your-app>.*.private-key.pem deploy/driftguard-key.pem
chmod 600 deploy/driftguard-key.pem app/.env
```

Both files are git-ignored and excluded from the Docker image (`.dockerignore`); compose
mounts the key at runtime.

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
docker compose -f deploy/docker-compose.yml up -d --build
# The port is bound to 127.0.0.1: expose it through a reverse proxy (Caddy/nginx)
# or a tunnel with HTTPS — see docs/DEPLOY-GCP.md
```

## 5. Install the app on a repo

On github.com: **Settings → GitHub Apps → DriftGuard → Install** → pick a public repo.
DriftGuard scans every selected repo right away, then on each push to the default branch.
It opens an issue (or a PR if the repo has `.driftguard.yml` with `mode: pr` and a safe
fix exists). Repos added to the installation later are scanned when added.

## 6. Per-repo configuration

See [Configuration in the README](./README.md#configuration).

## Troubleshooting

- `503 GITHUB_WEBHOOK_SECRET is not configured` → the variable is missing from `.env`
- `Invalid signature` → the webhook secret doesn't match `.env`
- Webhook returns `202` but nothing happens → scans run in the background: check
  `docker compose logs driftguard` for `scan owner/repo: …` lines
- `Failed to get installation token` → wrong private key or App ID
- Webhook receives nothing → check the public URL (smee/ngrok when local)
