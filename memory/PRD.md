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

### Iter-7/8 — Embeddable savings widget
- `GET /api/widget.js` — tiny IIFE loader; hosts paste a one-line `<script src="…/api/widget.js" data-tf-slug="…" data-tf-theme="dark" async defer></script>`
- `GET /api/embed/<slug>` — branded iframe HTML with dark/light theme + postMessage auto-resize + ALLOWALL X-Frame-Options + `frame-ancestors *` CSP
- Share page `/share/<slug>` gets "Embed this widget →" panel with copyable snippet, live preview, dark/light toggle
- `avg_compression_pct` capped at 100% in share JSON + embed HTML (cache hits previously could inflate past 100%)

## Prioritized Backlog

### P0 — Pre-launch hardening
- [ ] Pin CORS `allow_origins` to explicit production origin (currently `*`)
- [ ] Migrate rate-limit buckets to Redis once we scale beyond uvicorn single-worker
- [ ] Verify `alreadyherellc.com` domain in Resend → flip `SENDER_EMAIL` to `dispatch@alreadyherellc.com` and `OPERATOR_BCC=1`

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
