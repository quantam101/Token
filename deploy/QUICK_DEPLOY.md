# 🚀 TokenForge — Quick Deploy Card

**The whole thing in 30 minutes. $0/month forever.**

---

## Step 0 — Pre-requisites
- ☐ Your GoDaddy account (for DNS edits)
- ☐ Your OCI Console access (to open firewall)
- ☐ SSH access to OCI VM `129.146.236.177` as `ubuntu` (you set this up when you created the VM)
- ☐ GitHub account
- ☐ Vercel account (free, sign in with GitHub)

If any are missing, set them up first.

---

## Step 1 — GoDaddy DNS (2 min)
**https://dcc.godaddy.com/control/portfolio/alreadyherellc.com/settings → DNS → Add Record**

Add **A record**:
- Type: `A` · Name: `api` · Value: `129.146.236.177` · TTL: `1 Hour`

Keep the existing `forge` CNAME → `cname.vercel-dns.com` (it's for the frontend).

Verify in ~5 min:
```bash
dig +short api.alreadyherellc.com
# expected: 129.146.236.177
```

---

## Step 2 — OCI Firewall (3 min)
**OCI Console → Networking → Virtual Cloud Networks → [your VCN] → Security Lists → Default Security List → Add Ingress Rules**

Add **two rules**:
| Source CIDR | Protocol | Port | Description |
|---|---|---|---|
| `0.0.0.0/0` | TCP | `80`  | HTTP / Let's Encrypt |
| `0.0.0.0/0` | TCP | `443` | HTTPS |

---

## Step 3 — Push code to GitHub (2 min)
In **this chat**, find the **"Save to Github"** button (left of the message input bar). Click it.
- Create a new private repo named `tokenforge`
- Copy the clone URL (e.g. `https://github.com/alreadyhere-site/tokenforge.git`)

---

## Step 4 — Backend deploy on OCI (10 min)

From your laptop:
```bash
ssh -i ~/.ssh/your-oci-key ubuntu@129.146.236.177
```

On the VM (one block — copy/paste the whole thing):
```bash
sudo -i
cd /opt && git clone https://github.com/alreadyhere-site/tokenforge.git tokenforge
cp /opt/tokenforge/deploy/.env.production.template /opt/tokenforge/backend/.env
nano /opt/tokenforge/backend/.env
```

In `nano`, replace every `REPLACE_WITH_...` with real (**rotated**) values:
- `JWT_SECRET` — generate with: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- `ADMIN_PASSWORD` — strong password you'll remember
- `GOOGLE_API_KEY` — paid Gemini key from https://aistudio.google.com/apikey
- `STRIPE_API_KEY` — rolled `sk_live_...` from dashboard.stripe.com/apikeys
- `STRIPE_WEBHOOK_SECRET` — leave empty for now, we set in Step 6
- `RESEND_API_KEY` — rolled `re_...` from resend.com/api-keys

Save with `Ctrl+O`, `Enter`, `Ctrl+X`.

Then run pre-flight + deploy:
```bash
bash /opt/tokenforge/deploy/preflight.sh api.alreadyherellc.com
# fix any ✗ errors it reports, then:
bash /opt/tokenforge/deploy/oci_setup.sh api.alreadyherellc.com
```

The script handles: swap, Mongo, Python venv, systemd, nginx, Let's Encrypt SSL, firewall. Takes ~8 min.

**Success looks like:** `✅ Deploy complete. Backend live at: https://api.alreadyherellc.com`

Verify:
```bash
curl https://api.alreadyherellc.com/api/stats/public
# returns JSON with tokens_saved, user_count, etc.
```

---

## Step 5 — Frontend deploy on Vercel (5 min)

1. **https://vercel.com/new** → Import your `tokenforge` GitHub repo.
2. **Configure**:
   - Framework: **Create React App**
   - Root Directory: **`frontend`**
   - Build Command: `yarn build`
   - Install Command: `yarn install --frozen-lockfile`
3. **Environment Variables** → add:
   - `REACT_APP_BACKEND_URL` = `https://api.alreadyherellc.com`
4. Click **Deploy**.
5. After build (~2 min): **Project Settings → Domains → Add `forge.alreadyherellc.com`** → Vercel auto-verifies (your CNAME is already in place).

---

## Step 6 — Update Stripe webhook (2 min)

1. **https://dashboard.stripe.com/webhooks** → click your endpoint
2. **Edit destination** → URL: `https://api.alreadyherellc.com/api/webhook/stripe`
3. Click **Roll secret** → copy the new `whsec_...`
4. SSH back to VM:
   ```bash
   sudo nano /opt/tokenforge/backend/.env
   # update STRIPE_WEBHOOK_SECRET=whsec_xxxxxxx
   sudo systemctl restart tokenforge-backend
   ```

---

## Step 7 — Enable Apple Pay + Google Pay (10 sec, FREE)

**https://dashboard.stripe.com/settings/payment_methods** → scroll to "Wallets" → **Turn on Apple Pay** → **Turn on Google Pay**.
Done. Wallets auto-show on Stripe Checkout for supported devices.

---

## Step 8 — Smoke test (2 min)

1. **https://forge.alreadyherellc.com** → landing renders, no broken images
2. **Sign in → Register** new user with your email → welcome email arrives
3. **/dashboard/llm-keys** → BYOK paywall shown (you're free tier)
4. **/pricing → click Pro** → Stripe Checkout opens with real prices + Apple Pay button (if on Safari)
5. **/api/stats/public** → returns live numbers

If all 5 work → **you're selling.**

---

## Maintenance cheatsheet

```bash
# Backend logs
sudo journalctl -fu tokenforge-backend

# Restart after .env change
sudo systemctl restart tokenforge-backend

# Pull new code + restart
cd /opt/tokenforge && sudo git pull
sudo /opt/tokenforge/backend/.venv/bin/pip install -r /opt/tokenforge/backend/requirements.txt
sudo systemctl restart tokenforge-backend

# Weekly Mongo backup (add to crontab)
mongodump --db tokenforge --out /opt/backups/$(date +%F)
```

## When something breaks
1. `sudo systemctl status tokenforge-backend` — check the service
2. `sudo journalctl -u tokenforge-backend -n 100` — check the logs
3. `curl https://api.alreadyherellc.com/api/stats/public` — check it's reachable
4. See full troubleshooting table in `/app/deploy/DEPLOY_OCI.md`
