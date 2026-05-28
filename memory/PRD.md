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
- **Backend**: FastAPI + MongoDB. JWT auth. Emergent Universal LLM Key for OpenAI/Anthropic/Gemini calls via `emergentintegrations`. Stripe Checkout for paid plans.
- **Frontend**: React 19 + TailwindCSS + shadcn-ui + Recharts + Sonner toasts.
- **Design**: Dark theme — Obsidian Black + Signal Orange (#FF4500) + Matrix Green (#00E676), with Cabinet Grotesk display, IBM Plex Sans/Mono.
- **Optimization engine** (`/app/backend/optimizer.py`): pure-Python, deterministic. ~57% savings on the demo prompt.

## Core Requirements (static)
1. Public landing page with conversion-optimized hero, live calculator, 5-pillar bento, infrastructure section, waitlist + pricing teaser.
2. Email/password JWT auth (24h tokens, Bearer header).
3. Auto-issued API key on signup; full CRUD with reveal/copy/revoke.
4. LLM proxy endpoint `POST /api/proxy/chat` with `X-TF-Key` header — distills prompt, hits semantic cache, routes to right model tier, calls Universal Key LLM, returns response + token accounting + cost-saved metric.
5. Public optimizer endpoint `POST /api/optimize` (no auth) — distills any prompt without calling the LLM.
6. Stripe Checkout for Starter ($19), Pro ($99), Enterprise ($499) plans + webhook + transaction ledger.
7. Dashboard: KPI grid, 14-day Recharts charts, request logs.
8. Admin role with overview + waitlist table (RBAC enforced server + client side).
9. Documentation page with curl / Python / JS samples + copy buttons.
10. Waitlist capture for enterprise pilot.

## What's Been Implemented — 2026-01

### Backend (✓ 33/33 tests passing as of iter-3)
- ✓ JWT auth (register / login / me with monthly usage payload) + bcrypt password hashing
- ✓ Auto-seeded admin user from `.env`
- ✓ API key CRUD with active/revoked state
- ✓ 5-pillar optimization engine (`optimizer.py`)
- ✓ LLM proxy with semantic cache (cosine ≥ 0.98) and multi-tier routing
- ✓ Real LLM calls via `emergentintegrations` (OpenAI/Anthropic/Gemini)
- ✓ **Monthly token quota enforcement** on `/api/proxy/chat` (HTTP 429 when over)
- ✓ Dashboard analytics: `/overview`, `/timeseries`, `/logs`
- ✓ Stripe Checkout session + webhook + payment_transactions ledger
- ✓ **Annual billing cycle** with 20% discount (monthly|annual on `/api/billing/checkout`)
- ✓ Plan upgrade on `payment_status=paid` updates user quota
- ✓ **ROI Savings Report PDF** via `/api/reports/savings.pdf` (ReportLab, branded)
- ✓ Admin overview endpoint (RBAC) with revenue + waitlist
- ✓ Mongo indexes on email/key/created_at, etc.

### Frontend (✓ 19/19 flows passing across iters 2+3)
- ✓ Landing page with live token counter, calculator, bento grid of 5 pillars, infrastructure block, waitlist form, pricing teaser
- ✓ Login / Register with form validation + error mapping
- ✓ Pricing page with 4 tiers + **Monthly/Annual toggle** + Stripe redirect
- ✓ Playground (public + signed-in) with sample buttons
- ✓ Dashboard with Recharts, recent-logs table, **live Quota Meter**, **80%/100% Quota Alert Banner**, **Download ROI Report (PDF) button**
- ✓ API Keys page with reveal/copy/revoke
- ✓ Logs page (up to 100 entries)
- ✓ Billing page + Monthly/Annual toggle + usage bar + BillingSuccess polling
- ✓ Docs page with tabbed code samples (curl/python/js) + copy
- ✓ Admin console
- ✓ Custom typography (Cabinet Grotesk + IBM Plex Sans/Mono)

### Enhancements shipped — 2026-01 (iter-3)
1. Monthly token quota enforcement + dashboard meter + 80%/100% alert banner
2. ROI Savings Report PDF (branded, with KPIs + per-model breakdown)
3. Annual billing toggle (20% discount, monthly-equivalent shown)
4. Usage usage bar on Billing page

## Prioritized Backlog

### P0 — Pre-launch hardening
- [ ] Per-user monthly quota enforcement on `/proxy/chat` (currently logged, not enforced)
- [ ] Rate limit `/api/optimize` (public endpoint, DOS surface)
- [ ] Move CORS `allow_origins` from `*` to explicit prod origin
- [ ] Sanitize LLM error messages before bubbling to 502 detail

### P1 — Revenue + retention
- [ ] Annual billing with discount (Stripe price IDs)
- [ ] Usage email alerts at 80% / 100% of quota
- [ ] "Refer a developer, get 1M free tokens" referral program
- [ ] Public status page

### P2 — Engine v2
- [ ] Real tiktoken-based token estimation (replace heuristic)
- [ ] Vector index for semantic cache (Mongo Atlas Vector Search or pinecone)
- [ ] Per-provider failover (anthropic → openai if 5xx)
- [ ] BYO Key option (user pastes their own provider key, we never see token spend)

### P3 — Enterprise
- [ ] SSO / SAML
- [ ] VPC-deploy installer (mirror the OCI Free Tier 24/7 deployment from the spec)
- [ ] Audit logs export (CSV / Datadog)

## Next Tasks
1. P0 quota enforcement → ship enterprise pilots
2. Build "ROI report" PDF generator (auto-emails the customer their monthly savings — best retention hook)
3. Launch wait/lead capture → cold-outbound to top 50 AI startups by LLM spend

## Test credentials
See `/app/memory/test_credentials.md`.
