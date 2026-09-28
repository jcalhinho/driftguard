# ☁️ Deploying DriftGuard on GCP (e2-micro, free tier)

Target: GitHub App running with a public HTTPS webhook URL — €0/month.

> Prerequisites: GitHub App created (App ID + private key), a Google Cloud account
> with billing attached (the free tier requires a billing account, but e2-micro costs
> nothing in us-west1/us-central1/us-east1).

## 1. Create the instance

1. Go to https://console.cloud.google.com → create a project (`driftguard`) if needed
2. **Compute Engine → VM instances → Create instance**
3. Config:
   - Name: `driftguard`
   - Region: `us-west1` (or `us-central1` / `us-east1` — required for the free tier)
   - Machine type: `e2-micro`
   - Boot disk: Debian 12, 30 GB standard
   - Firewall: ✅ **Allow HTTP traffic** + ✅ **Allow HTTPS traffic**
4. Create. Note the **external IP**.

## 2. Install Docker and tools (via SSH)

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER && newgrp docker
```

## 3. Deploy the app

```bash
git clone https://github.com/jcalhinho/driftguard.git
cd driftguard
# Upload your private key to the VM:
#   scp driftguard-key.pem USER@IP:~/driftguard/deploy/driftguard-key.pem
cp app/.env.example app/.env            # then edit: App ID + webhook secret
```

Edit `app/.env`:

```
GITHUB_APP_ID=5105596
GITHUB_WEBHOOK_SECRET=<generated: openssl rand -hex 32>
```

Then:

```bash
docker compose -f deploy/docker-compose.yml up -d --build
curl http://localhost:8000/health   # → {"status":"ok","rules":13}
```

## 4. Public HTTPS URL (two options)

### Option A — Cloudflare Quick Tunnel (recommended, zero domain, 2 minutes)

```bash
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64 && sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
cloudflared tunnel --url http://localhost:8000
```

→ Cloudflare prints a `https://xxx.trycloudflare.com` URL.
→ Set it as the **Webhook URL** in the GitHub App settings: `https://xxx.trycloudflare.com/webhook`,
tick **Active**, and set the same webhook secret.
→ Run it in the background: `nohup cloudflared tunnel --url http://localhost:8000 &`
(For long-term use: a named tunnel or systemd service.)

### Option B — Domain + Caddy (for production)

With a domain pointing to the VM IP:

```bash
sudo apt install -y caddy
sudo tee /etc/caddy/Caddyfile <<'EOF'
driftguard.votredomaine.fr {
    reverse_proxy localhost:8000
}
EOF
sudo systemctl reload caddy
```

→ Webhook URL: `https://driftguard.votredomaine.fr/webhook`

## 5. Activate the webhook on GitHub

1. GitHub App settings → **Webhook**
2. URL: `https://<ton-url>/webhook` · ✅ Active · Secret: same as `.env`
3. Save → GitHub sends a `ping` → the VM log should show `POST /webhook 200`

## 6. Install the app on a repo

GitHub App settings → **Install App** → pick a public repo → push anything →
the log shows the scan → an issue appears on the repo. 🎉
