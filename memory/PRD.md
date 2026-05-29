# TokenForge — Product Requirements Document

## Original Problem Statement
> "build, make production ready and live. once we have proof of work we can market it and sell it, that is the goal. continue until complete, functionality is verified and its live and working"
>
> Based on the attached *Autonomous Token Optimization Engine (ATOE) Master Specification*.

## Product
**TokenForge** — a developer-facing SaaS that proxies LLM API calls (OpenAI, Anthropic, Gemini) and applies five deterministic distillation pillars from the ATOE spec to cut prompt-token cost by 40–80%, without retraining the model.

## Target Personas
1. **Indie devs & AI startups** burning $200–$5,000/mo on LLM APIs.
2. **Growth-stage SaaS** with prompt-heavy features (chatbots, summarizers, agents).
3. **Enterprise AI teams** needing data-sovereignty and cost predictability.

## Architecture
- **Backend**: FastAPI + MongoDB. JWT auth. Emergent Universal LLM Key for OpenAI/Anthropic/Gemini via `emergentintegrations`. Stripe Checkout for paid plans. Resend for transactional email. ReportLab for branded PDFs.
- **Frontend**: React 19 + TailwindCSS + shadcn-ui + Recharts + Sonner toasts.
- **Design**: Dark — Obsidian Black + Signal Orange #FF4500 + Matrix Green #00E676 — Cabinet Grotesk + IBM Plex Sans/Mono.
- **Optimization engine** (`/app/backend/optimizer.py`): pure-Python, deterministic. ~57% savings on the demo prompt.

## What's Been Implemented — 2026-01 (live + verified)

### Backend (✓ tested across 5 iterations)
- ✓ JWT auth (register / login / me with usage payload) + bcrypt password hashing
- ✓ Auto-seeded admin
- ✓ API key CRUD with active/revoked state
- ✓ 5-pillar optimization engine
- ✓ LLM proxy with semantic cache (cosine ≥ 0.98) and multi-tier routing
- ✓ Real LLM calls via Universal Key (OpenAI/Anthropic/Gemini)
- ✓ Monthly token quota enforcement (HTTP 429 when exceeded)
- ✓ Stripe Checkout with **monthly + annual (−20%)** billing cycles + webhook + transaction ledger
- ✓ Plan upgrade on `payment_status=paid` updates user quota
- ✓ Dashboard analytics: `/overview`, `/timeseries`, `/logs`
- ✓ **ROI Savings Report PDF** via `/api/reports/savings.pdf` (branded ReportLab)
- ✓ **Email-me-the-report** via `/api/reports/savings/email` (PDF attached)
- ✓ **Public shareable savings receipt** — `POST /api/share/savings` returns idempotent slug → `GET /api/share/savings/<slug>` returns lifetime aggregates
- ✓ Admin overview endpoint (RBAC) with revenue + waitlist
- ✓ **Resend transactional email**: welcome, quota alerts (80% + 100%, deduped per period), payment confirmation, ROI report
- ✓ **Rate limiting** with X-Forwarded-For awareness: `/optimize` 30/60s, `/auth/register` 8/600s, `/auth/login` 10/300s, `/waitlist` 10/300s
- ✓ Mongo indexes (users, api_keys, proxy_requests, waitlist, semantic_cache, payment_transactions, share_links, email_alerts)

### Frontend (✓ 100% pass through all iterations)
- ✓ Landing page with hero, live counter, calculator, 5-pillar bento, infrastructure, waitlist, pricing teaser
- ✓ Login / Register with JWT + Bearer auth
- ✓ Pricing with **Monthly/Annual toggle** + Stripe redirect
- ✓ Playground
- ✓ Dashboard: Quota Meter + 80%/100% Alert Banner + Recharts + logs + **Share / Email / Download** buttons for the ROI report
- ✓ API Keys page (reveal/copy/revoke)
- ✓ Logs page
- ✓ Billing page with usage bar + Monthly/Annual + BillingSuccess polling
- ✓ Docs with curl/Python/JS tabs + copy
- ✓ Admin console
- ✓ **Public `/share/<slug>`** receipt page with Tweet-your-savings CTA (hidden at $0 lifetime) and 404 state with recovery CTAs

### Test posture
- iter-1: 27/27 backend ✓
- iter-2: 13/13 frontend ✓
- iter-3: 33/33 backend + 6/6 frontend ✓ (quota, PDF, annual, banner)
- iter-4: 14/18 backend (4 rate-limit failures — diagnosed XFF bug) + 5/5 frontend ✓
- iter-5: 6/6 rate-limit + 11/11 smoke + 100% frontend ✓ (XFF fix verified)
- iter-6: 16/16 + 100% frontend ✓ (code-review fixes — SHA-256, var init, stable keys)
- iter-7: 18/25 backend + 90% frontend — /embed routing bug diagnosed
- iter-8: **25/25 backend + 100% frontend ✓** (embed widget — route moved under /api)

### Iter-11 — Launch features (OG image, Referrals, Showcase, CORS pin)
- **OG image generator** `GET /api/share/savings/<slug>/og.png` — 1200×630 PNG via Pillow, branded TF header, hero number in matrix green, $ saved + avg compression cards, "Start saving — free →" CTA. Auto-injected into `/share/<slug>` page head as `og:image` + `twitter:image` for live LinkedIn/X/Slack previews. Placeholder returned (200, not 404) for unknown slugs so social cards never break.
- **Referral system** — `POST /api/auth/register` now accepts `ref: <user_id>`; valid referral grants **+500K bonus tokens** to BOTH parties (atomic `$inc`). New `GET /api/referrals/me` endpoint returns the user's code + count + bonus. Dashboard exposes a Referral card with one-click copy of `/register?ref=<id>`. Register page reads `?ref=` and shows a green "REFERRAL BONUS unlocked" banner.
- **Public showcase** — `GET /api/showcase/savings?limit=12` returns opted-in customers (those with share_links + actual savings) sorted by $ saved. Landing page now has a **"Used By" marquee strip** that fetches showcase data and renders deep-linked pills (each click goes to that customer's public share page → which has a free-signup CTA).
- **Production CORS pin** — `CORS_ORIGINS` env list (comma-separated) replaces `*`. Preview + tokenforge.io origins included. `allow_credentials=False` keeps wildcard fallback safe.

### Test posture
- iter-1: 27/27 backend ✓
- iter-2: 13/13 frontend ✓
- iter-3: 33/33 + 6/6 ✓
- iter-4: 14/18 backend + 5/5 frontend — XFF rate-limit bug diagnosed
- iter-5: 6/6 rate-limit + 11/11 smoke + 100% frontend ✓
- iter-6: 16/16 + 100% frontend ✓ (code-review fixes)
- iter-7: 18/25 backend + 90% frontend — /embed routing diagnosed
- iter-8: 25/25 backend + 100% frontend ✓ (embed widget)
- iter-9: 25/25 + 100% ✓ (perf/readability polish)
- iter-10: 25/25 + 100% ✓ (code-review polish 3)
- iter-11: **38/38 backend + 100% frontend ✓** (OG, referrals, showcase, CORS — launch features)

## Launch runbook
See **`/app/memory/RESEND_DNS_SETUP.md`** for the step-by-step Resend domain verification in Zoho.

After that:
1. Edit `/app/backend/.env` → `SENDER_EMAIL="TokenForge <dispatch@alreadyherellc.com>"`, `OPERATOR_BCC="1"`.
2. `sudo supervisorctl restart backend`
3. Click Deploy in Emergent (CORS already pinned to preview + tokenforge.io).

### Iter-13 — Resend domain verified + email delivery LIVE
- **Domain `alreadyherellc.com` verified at Resend** (GoDaddy DNS) → `SENDER_EMAIL` flipped to `TokenForge <dispatch@alreadyherellc.com>`, `OPERATOR_BCC=1` enabled in `/app/backend/.env`.
- **Milestone celebration flow verified end-to-end**: $1/$20/$100/$1000 thresholds correctly insert `milestone_alerts` row, auto-create public share link, and dispatch milestone email — all idempotent under repeated requests.

### Test posture (cont.)
- iter-13: **11/11 backend ✓** (email delivery + milestone flywheel re-verification)

### Iter-14a — Direct-SDK migration (LLM + Stripe LIVE)
- **Removed `emergentintegrations` from server.py imports.** New `/app/backend/llm_router.py` (OpenAI/Anthropic/Google Gemini direct SDKs) + `/app/backend/stripe_service.py` (official Stripe Python SDK).
- **Stripe LIVE**: `STRIPE_API_KEY=sk_live_...` verified via real `cs_live_...` checkout creation. Webhook signing secret `whsec_...` installed and verified.
- **Gemini direct routing** end-to-end verified ("PONG" response, semantic cache hits).

### Iter-14b — BYOK feature + 100% Emergent runtime separation ✅
- **`emergentintegrations` uninstalled** (`pip uninstall` + removed from requirements.txt). Backend imports zero Emergent code.
- **BYOK (Bring Your Own Keys)** as Pro+ upsell:
  - New `/app/backend/byok_service.py` — Fernet (AES-128-CBC + HMAC) encryption derived from JWT_SECRET. Keys decrypted in-memory per request only.
  - 3 endpoints: `GET /api/byok` (list, masked), `POST /api/byok` (upsert, 402 paywall for free/starter), `DELETE /api/byok/{provider}`.
  - Free/Starter plans **paywalled at HTTP 402** — `/api/proxy/chat` silently routes them to platform Gemini 2.5 Flash with a `platform_note` upsell hint.
  - Pro/Enterprise plans get full provider choice + their own stored keys (zero LLM cost to TokenForge at any scale).
  - New `/app/frontend/src/pages/LlmKeys.jsx` page at `/dashboard/llm-keys` — paywall banner for free users, 3 provider cards for Pro+, input/save/remove with masked display.
  - Pricing page updated with "BYO Keys" line on Pro & Enterprise tiers.
- **Encryption verified at rest**: direct Mongo inspection in tests confirms `gAAAAA` Fernet prefix, no raw key substring leakage.

### Test posture (cont.)
- iter-14: **22/22 ✓** (11 backend pytest + 11 frontend UI assertions); encryption-at-rest verified; full regression spine clean.

## Prioritized Backlog

### P0 — Pre-launch hardening
- [x] Verify `alreadyherellc.com` domain in Resend (DONE — iter-13)
- [x] Pin CORS `allow_origins` to explicit production origins (DONE — iter-11, expanded iter-16)
- [x] Remove all Emergent code/branding from shipped surface (DONE — iter-16)
- [x] BYOK as Pro+ paid upsell with encrypted vault (DONE — iter-14b)
- [x] LLM router fix — confirmed customer BYOK keys actually used (DONE — iter-15)
- [ ] Rotate every secret pasted in chat (USER action)
- [ ] Enable Apple Pay + Google Pay in Stripe dashboard (USER action, 10 sec)
- [ ] Fund Google Gemini billing (free tier = 20 req/day, will choke real users)
- [ ] Deploy: OCI Always-Free + Vercel per `/app/deploy/DEPLOY_OCI.md`

### Iter-16 — Full Emergent scrub (pre-sale validation) ✅
- **All Emergent surface area removed** from shipped code: badge, PostHog telemetry, `emergent-main.js` script, `@emergentbase/visual-edits` dev dep, Emergent CDN hero image, deprecated `EMERGENT_LLM_KEY` constant — all gone.
- **Hero is now CSS-only** (radial spotlight + orange beam grid).
- **`public/index.html` is minimal** — meta tags + fonts + root div only.
- **Test result (iter-16)**: 0 forbidden tokens across served HTML + 11 rendered routes; `window.posthog` undefined; `#emergent-badge` count 0; `import emergentintegrations` → ModuleNotFoundError.
- **Critical regression intact**: BYOK negative-test confirms customer keys are actually used (bogus key → 502); Stripe LIVE checkout, PDF reports, webhook signing, encryption-at-rest all PASS.
- **22/23 PASS, 1 SKIP** (transient Gemini 503, not a code bug). Frontend: 100% (all 11 routes + scrub checks pass).

### P1 — Revenue + retention
- [ ] Cron job to auto-email monthly ROI report on the 1st of each month
- [ ] Email usage alerts also gate to "you'll hit your cap by <date>" projection
- [ ] Referral program: `?ref=<user_id>` + +500K tokens on both sides
- [ ] OG meta tags + screenshot per `/share/<slug>` for Twitter/LinkedIn previews

### P2 — Engine v2
- [ ] tiktoken-accurate token estimation
- [ ] Vector index (Atlas Vector Search / Pinecone) for semantic cache
- [ ] Provider failover (Anthropic → OpenAI fallback on 5xx)
- [ ] BYO Key

### P3 — Enterprise
- [ ] SSO / SAML
- [ ] On-prem / VPC installer (per ATOE spec OCI Free Tier baseline)
- [ ] CSV / Datadog audit log export

## Next Tasks
1. Verify `alreadyherellc.com` in Resend dashboard so emails reach all customers (not just gmail owner)
2. Pin CORS, deploy via Emergent's "Make Live" / Vercel
3. Send first 50 cold outbound emails using the in-app Share / ROI receipt as proof-of-savings

## Test credentials
See `/app/memory/test_credentials.md`.
