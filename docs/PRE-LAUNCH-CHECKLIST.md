# ✅ Pre-launch checklist for the GitHub App

This guide walks through the two blocking points before any public launch,
and verifies the App is ready for external users.

## 1. Make the GitHub App public

1. Go to **GitHub → Settings → Developer settings → GitHub Apps**
2. Select **DriftGuard** (App ID: 5105596)
3. Under **General → Where can this GitHub App be installed?**
   → must be set to **Any account**
   - If it says "Only on this account", change it to **Any account** and save.
   - Without this, nobody else can install the app.

4. Under **General → Remove the app** → make sure there is no restriction.

## 2. Stabilize the webhook URL

The Cloudflare Quick Tunnel (`*.trycloudflare.com`) generates a **random URL**
that changes on every restart. For a public launch, you need a **fixed URL**.

### Option A — Named Cloudflare Tunnel (recommended, free, 10 minutes)

If you have a domain on Cloudflare:

```bash
# On the GCP VM:
cloudflared tunnel login          # browser auth, one-time
cloudflared tunnel create driftguard
# → prints a Tunnel UUID

# Configure the tunnel to point at your local app:
cat > ~/.cloudflared/config.yml <<EOF
tunnel: <TUNNEL-UUID>
credentials-file: /home/$USER/.cloudflared/<TUNNEL-UUID>.json
ingress:
  - hostname: driftguard.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
EOF

# Add a DNS CNAME (cloudflared does it for you):
cloudflared tunnel route dns driftguard driftguard.yourdomain.com

# Run as a service:
sudo cloudflared service install
sudo systemctl start cloudflared
```

→ Webhook URL: `https://driftguard.yourdomain.com/webhook` — **stable forever**.

### Option B — Caddy with your own domain

Already documented in `docs/DEPLOY-GCP.md` (Option B). If you have a domain
pointing to the VM IP, Caddy gives you automatic HTTPS with Let's Encrypt.

### Option C — Keep the quick tunnel (NOT recommended for launch)

If you must use the quick tunnel, you need to:
1. Start it with `nohup cloudflared tunnel --url http://localhost:8000 &`
2. Parse the URL from the output
3. Update the GitHub App webhook URL every time it changes

This is fragile and will break the webhook for all users on every restart.

## 3. Set the webhook URL in the GitHub App

1. **GitHub App settings → Webhook**
2. **Payload URL**: `https://<your-stable-url>/webhook`
3. **Content type**: `application/json`
4. **Secret**: must match `GITHUB_WEBHOOK_SECRET` in `app/.env`
5. **SSL verification**: Enable (you have HTTPS now)
6. **Events**: 
   - ✅ Installation
   - ✅ Installation repositories
   - ✅ Push
7. **Active**: ✅
8. Save → GitHub sends a `ping` → check the VM logs for `POST /webhook 200`

## 4. Verify the App is working

```bash
# On the VM:
curl http://localhost:8000/health
# → {"status":"ok","rules":53}

# Check the webhook is receiving events:
docker compose -f deploy/docker-compose.yml logs -f --tail 20
```

Then install the app on a test repo, push a commit containing a retired API
call (e.g. `model="gpt-4-32k"`), and verify an issue appears within seconds.

## 5. Public install URL

Once the app is public, the install URL is:

```
https://github.com/apps/driftguard
```

Users click "Install", pick their repos, and the app starts scanning immediately.
