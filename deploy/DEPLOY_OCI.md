# TokenForge — OCI Always-Free + Vercel Deployment Runbook

**Target architecture (truly $0/month forever):**

```
┌──────────────────────────────────────────────────────────────┐
│  Browser → forge.alreadyherellc.com                          │
│             (Vercel — free static React frontend, global CDN) │
│                                                              │
│  Frontend → api.alreadyherellc.com                           │
│             (OCI Always-Free VM — FastAPI + MongoDB)         │
│                                                              │
│  Stripe webhook → api.alreadyherellc.com/api/webhook/stripe  │
└──────────────────────────────────────────────────────────────┘
```

Total cost: **$0/month forever** (OCI Always Free + Vercel Hobby + MongoDB local + Resend + Stripe pay-per-tx).

---

## Step 1 — GoDaddy DNS

Go to **https://dcc.godaddy.com/control/portfolio/alreadyherellc.com/settings**
→ **DNS** → **Manage DNS** → **Add Record**.

Add a new **A record** for the backend:

| Type | Name | Value | TTL |
|---|---|---|---|
| `A` | `api` | `129.146.236.177` | `1 Hour` |

**Leave the `forge` CNAME alone** (it still points at Vercel — that's where the frontend will live).

Verify in ~5 min:
```bash
dig +short api.alreadyherellc.com
# should return: 129.146.236.177
```

---

## Step 2 — OCI firewall (Ingress Rules)

Your VM's **Virtual Cloud Network** security list blocks ports by default.

1. Go to **OCI Console → Networking → Virtual Cloud Networks → [your VCN] → Security Lists → Default Security List**.
2. Click **Add Ingress Rules**. Add these two:

| Source CIDR | IP Protocol | Destination Port | Description |
|---|---|---|---|
| `0.0.0.0/0` | TCP | `80` | HTTP for Let's Encrypt + nginx |
| `0.0.0.0/0` | TCP | `443` | HTTPS app traffic |

(SSH on 22 should already be open.)

---

## Step 3 — Save TokenForge code to GitHub

In this chat, find the **"Save to Github"** button (left side of the message input). Push the code to a new private repo named `tokenforge` under your GitHub account.

Once pushed, **note the clone URL**, e.g.:
```
git@github.com:alreadyhere-site/tokenforge.git
```

---

## Step 4 — SSH into the OCI VM and deploy

```bash
# From your local machine
ssh -i ~/.ssh/your-oci-key ubuntu@129.146.236.177
```

On the VM:

```bash
# Become root
sudo -i

# Clone the code (replace with your actual repo URL)
mkdir -p /opt && cd /opt
git clone https://github.com/alreadyhere-site/tokenforge.git tokenforge
# OR for private repo: use a GitHub deploy key or PAT

# Create production .env (copy from template, edit secrets)
cp /opt/tokenforge/deploy/.env.production.template /opt/tokenforge/backend/.env
nano /opt/tokenforge/backend/.env
# ⚠ REPLACE every "REPLACE_WITH_..." with your real (rotated) secrets
# Generate JWT_SECRET with: python3 -c "import secrets;print(secrets.token_hex(32))"

# Make script executable and run it
chmod +x /opt/tokenforge/deploy/oci_setup.sh
bash /opt/tokenforge/deploy/oci_setup.sh api.alreadyherellc.com
```

The script does everything: swap, MongoDB, Python venv, systemd service, nginx, Let's Encrypt SSL, firewall. Takes ~5–10 minutes.

**At the end you should see:** `✅ Deploy complete. Backend live at: https://api.alreadyherellc.com`

Verify:
```bash
curl https://api.alreadyherellc.com/api/stats/public
# Should return JSON with tokens_saved, user_count, etc.
```

---

## Step 5 — Deploy frontend to Vercel

1. Go to **https://vercel.com/new** → import your `tokenforge` GitHub repo.
2. **Configure project**:
   - Framework Preset: **Create React App**
   - Root Directory: `frontend`
   - Build Command: `yarn build`
   - Output Directory: `build`
   - Install Command: `yarn install --frozen-lockfile`
3. **Environment Variables** — add this one:
   - `REACT_APP_BACKEND_URL` = `https://api.alreadyherellc.com`
4. Click **Deploy**.

Once it's built (~2 min), go to **Project → Settings → Domains**:
- Add `forge.alreadyherellc.com` — Vercel will say "Valid Configuration" because your CNAME at GoDaddy already points to `cname.vercel-dns.com`. SSL is auto-provisioned.

Now `https://forge.alreadyherellc.com` serves your React frontend, which calls `https://api.alreadyherellc.com` for the API.

---

## Step 6 — Update Stripe webhook

1. Go to **https://dashboard.stripe.com/webhooks** → click your existing endpoint.
2. **Update endpoint** → change URL to:
   ```
   https://api.alreadyherellc.com/api/webhook/stripe
   ```
3. Keep the same `whsec_...` signing secret (it doesn't change when URL changes).
4. If you want a fresh signing secret to install on the VM (recommended since the old one was pasted in chat), click **Roll secret** → copy the new `whsec_...` → SSH back to VM:
   ```bash
   sudo nano /opt/tokenforge/backend/.env
   # update STRIPE_WEBHOOK_SECRET
   sudo systemctl restart tokenforge-backend
   ```

---

## Step 7 — Smoke test the live site

1. Visit **https://forge.alreadyherellc.com** → landing page should render
2. Click **Start free** → register a new user with your personal email → should receive welcome email
3. Log in → dashboard renders
4. Visit `/dashboard/llm-keys` → BYOK paywall shown (because new user is free tier)
5. Visit `/pricing` → click **Pro** → Stripe Checkout opens at `checkout.stripe.com` with a `cs_live_...` session

If all 5 work, **you're selling.**

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `502 Bad Gateway` from nginx | `sudo journalctl -u tokenforge-backend -n 100` — check for missing env var |
| Mongo killed (OOM) | `free -h` to verify swap is on. Mongo cache should be 256MB — confirm in `/etc/mongod.conf` |
| Frontend shows "Network Error" | Check `REACT_APP_BACKEND_URL` in Vercel matches the actual backend domain; check `CORS_ORIGINS` in backend `.env` includes `https://forge.alreadyherellc.com` |
| Let's Encrypt fails | Make sure DNS A record propagated (`dig +short api.alreadyherellc.com`) AND port 80 is open in OCI Security List |
| `systemctl restart tokenforge-backend` failures | `sudo nano /etc/systemd/system/tokenforge-backend.service` → check `WorkingDirectory` and `User=ubuntu` exists |

## Maintenance commands

```bash
# Backend logs
sudo journalctl -fu tokenforge-backend

# Mongo logs
sudo journalctl -fu mongod

# Restart backend after .env change
sudo systemctl restart tokenforge-backend

# Pull new code + restart
cd /opt/tokenforge && sudo git pull
sudo /opt/tokenforge/backend/.venv/bin/pip install -r /opt/tokenforge/backend/requirements.txt
sudo systemctl restart tokenforge-backend

# Mongo backup (run weekly via cron)
mongodump --db tokenforge --out /opt/backups/$(date +%F)
```

## Capacity expectations on the free VM (1 CPU, 1 GB RAM)

- ✅ Handles **20–50 concurrent users** comfortably
- ✅ Up to **~5,000 daily LLM proxy requests** (assuming reasonable mix of cache hits)
- ⚠ At >100 concurrent users you'll see latency spikes. Upgrade path:
  - **Free**: provision an OCI **Ampere A1 ARM** instance (4 OCPUs, 24 GB RAM — also Always Free if you haven't used your ARM allowance)
  - **$5/mo**: Hetzner CX11 (2 vCPU, 4 GB RAM)
