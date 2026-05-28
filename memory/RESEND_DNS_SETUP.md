# Resend Domain Verification — Zoho DNS Setup

Until `alreadyherellc.com` is verified in Resend, transactional email only delivers to `alreadyherellc@gmail.com` (the Resend account owner). Here's the **15-minute** path to flip on customer email delivery.

## 1. Add the domain in Resend

1. Go to **https://resend.com/domains**
2. Click **Add Domain** → enter `alreadyherellc.com` → pick the **us-east-1** region (default; lowest latency for the deployment).
3. Resend now shows you **3 DNS records** (1 MX + 2 TXT). Keep that tab open — values are unique to your account and required exactly.

The records look like this (your exact values will differ — copy from your Resend dashboard):

| Type | Name / Host                  | Value (priority)                                                              |
|------|------------------------------|--------------------------------------------------------------------------------|
| MX   | `send`                       | `feedback-smtp.us-east-1.amazonses.com` &nbsp;&nbsp;**priority 10**            |
| TXT  | `send`                       | `v=spf1 include:amazonses.com ~all`                                            |
| TXT  | `resend._domainkey`          | `p=MIGfMA0GCSq…` (long DKIM public key — paste the entire string Resend shows) |

(Optional but recommended — improves deliverability)

| Type | Name / Host | Value                                                                  |
|------|-------------|------------------------------------------------------------------------|
| TXT  | `_dmarc`    | `v=DMARC1; p=none; rua=mailto:dispatch@alreadyherellc.com; pct=100`     |

## 2. Add the records in Zoho

1. Go to **https://mailadmin.zoho.com** → log in with the dispatch account.
2. **Domains** → click `alreadyherellc.com` → **DNS** (or **DNS Management** depending on UI).
3. For each row in the Resend table above, click **Add Record**:
   - **Type**: pick `MX` or `TXT` to match
   - **Hostname/Name**: type **exactly** what Resend shows (e.g. `send`, not `send.alreadyherellc.com`)
   - **Value**: paste exactly what Resend shows. **Do not** add quotes; Zoho adds them for TXT.
   - For the **MX** row, set **Priority** to `10` (or whatever Resend specified).
   - **TTL**: leave default (3600).
4. Save each record.

⚠ **Important**: if Zoho complains that an SPF record already exists at root (`@`), do NOT add a second SPF; the Resend SPF record above is at `send` (a subdomain used for the bounce-return path), so it's a different record and shouldn't conflict. If you DO want envelope-from `dispatch@alreadyherellc.com`, you'd merge `include:amazonses.com` into your root `@` SPF instead — but that's not required for Resend.

## 3. Wait + verify

- DNS propagation is usually **15-30 minutes**; sometimes up to 24h.
- Check from terminal:
  ```bash
  dig +short MX send.alreadyherellc.com
  dig +short TXT send.alreadyherellc.com
  dig +short TXT resend._domainkey.alreadyherellc.com
  ```
- Back in **resend.com/domains** → click **Verify DNS records** on the `alreadyherellc.com` row. Once all three turn green, you're live.

## 4. Flip TokenForge to use the verified sender

Edit `/app/backend/.env`:

```env
SENDER_EMAIL="TokenForge <dispatch@alreadyherellc.com>"
OPERATOR_BCC="1"
```

Then:
```bash
sudo supervisorctl restart backend
```

Now every welcome email, quota alert, payment confirmation, and ROI report is delivered to the actual customer **AND** BCC'd to your Zoho inbox at `dispatch@alreadyherellc.com`.

## 5. Sanity test

```bash
# Register a fresh user — should trigger a real welcome email
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d'=' -f2)
curl -X POST "$API_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"YOU@youremail.com","password":"forge-test-1234","name":"Sanity"}'
```

Check the inbox; both your test address and `dispatch@alreadyherellc.com` should receive the branded welcome email.
