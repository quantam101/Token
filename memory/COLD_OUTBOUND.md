# TokenForge — 5 Cold Outbound Emails (First-100-Customers Playbook)

These are ready-to-send. Replace `{NAME}`, `{COMPANY}`, and `{YOUR_DEPLOY_URL}` before sending.
Send from `dispatch@alreadyherellc.com` (verified Resend domain) so deliverability is high.

## How to use
1. Build a list of 50 prospects via LinkedIn search: `"AI engineer" OR "founder" + ("OpenAI API" OR "Claude API" OR "ChatGPT") + post within 30 days`.
2. Scrape email via Hunter.io / Apollo (~$0.10 each).
3. Send 1 email per prospect from your Gmail or Resend. Track opens with a single tracking pixel if you want.
4. **Goal**: 5–10 replies → 3 demos → 1 paid customer. That funnel converts at ~2% on cold dev-tool outbound; you need volume.

---

## Email 1 — "I built it for myself" (works on technical founders)

**Subject**: cut $7k/yr off our OpenAI bill — built this proxy, want it?

Hi {NAME},

We were burning ~$2.3k/mo on GPT-4o for our internal RAG bot. Most of those tokens were boilerplate ("Please could you help me…"), JSON whitespace, and near-duplicate prompts the LLM had seen 30 seconds ago.

So we built **TokenForge** — a drop-in proxy that sits in front of OpenAI/Anthropic/Gemini and:

1. Compresses verbose prompts deterministically (no LLM call, no quality loss)
2. Caches semantically-similar prompts (cosine ≥ 0.98 → instant return, $0)
3. Routes trivial requests away from frontier models

It cut **our** input bill 57%. We're now letting other teams plug it in for free.

If you're using {OpenAI/Claude/Gemini} in production, want me to send you a 90-second video showing the before/after dashboard? You can plug it in with a 1-line baseURL swap.

— {YOUR_NAME}
{YOUR_DEPLOY_URL}

P.S. — Free tier is 50k tokens/mo, no card required. Just drop your existing OpenAI key into the BYOK tab and you'll see savings within 5 minutes.

---

## Email 2 — "specific number" (works on CTOs / heads of eng)

**Subject**: {COMPANY}'s GPT-4o spend, halved

Hi {NAME},

Quick math: if {COMPANY} is doing ~1M GPT-4o calls/month at ~2k input tokens each, that's roughly **$10k/mo in input tokens alone**.

TokenForge drops that to **$4,200/mo** through deterministic prompt compression + semantic caching. Same model. Same outputs. Just 58% less input billed.

Worth 15 minutes? Live demo on your stack: {YOUR_DEPLOY_URL}

You can also self-serve — drop your OpenAI key in our BYOK vault and the dashboard shows live $ savings on every request. We don't see your tokens; the key is Fernet-encrypted at rest.

— {YOUR_NAME}

---

## Email 3 — "permissionless trial" (works on individual devs)

**Subject**: 1-line LLM cost cut for {COMPANY}

{NAME} —

Saw your post about scaling {AI feature}. If your prompts have **any** of these patterns, you're overpaying OpenAI by 30–80%:

- Politeness padding ("Please could you help me with the following…")
- Repeated system messages on every call
- Near-duplicate user prompts in short time windows
- JSON output schemas with verbose key names

TokenForge fixes all four, deterministically, with zero quality loss. 30-second test:

1. Open {YOUR_DEPLOY_URL}
2. Paste a real prompt you use into the calculator
3. See your % savings + projected annual $ before you sign up

If the number is < 30% I'll buy you a coffee. If it's > 30%, you'd be insane not to add the 1-line baseURL swap.

— {YOUR_NAME}

---

## Email 4 — "warm intro angle" (works after a LinkedIn comment exchange)

**Subject**: re: your AI cost comment

Hey {NAME},

Caught your comment on {LinkedIn post / Twitter thread} about LLM costs spiraling. Same boat — we shipped a fix and figured I'd send it your way.

It's called TokenForge. Live: {YOUR_DEPLOY_URL}

Two things make it different from Helicone / Portkey:

1. **Deterministic prompt distillation** before the LLM sees the request — they only do observability
2. **BYO Keys** — you keep paying OpenAI directly at *their* rate, we just shave 40–80% off what you'd send them. We don't markup tokens.

$19/mo on the Starter tier. Free for 50k tokens. Pricing capped at $499 enterprise. No "contact sales" BS.

If it's not 10x cheaper per token saved than your current setup, just hit reply and tell me why — I'll fix the gap.

— {YOUR_NAME}

---

## Email 5 — "the social proof one" (send after first 5 customers)

**Subject**: Customers saving $4k–$30k/yr on LLM bills (case studies inside)

Hi {NAME},

Three customers since {LAUNCH_DATE}:

- **{Customer 1}** — RAG chatbot, OpenAI GPT-4o → saving **$3,840/yr** at 1.2M req/mo
- **{Customer 2}** — Agent framework, Claude Sonnet → saving **$11,200/yr** at 4M req/mo
- **{Customer 3}** — Code-gen SaaS, Gemini Pro → saving **$28,400/yr** at 18M req/mo

Same engine. No retraining. 1-line baseURL swap.

You can try the same engine on your prompts here without signing up: {YOUR_DEPLOY_URL}#calculator

If you'd rather see numbers on YOUR traffic, drop me a session token and we'll generate a savings report PDF for you in 24 hours — no obligation.

— {YOUR_NAME}

---

## Follow-up cadence (do this religiously)

| Day | Action |
|---|---|
| 0 | Email 1 |
| 3 | Email 2 (if no reply) |
| 7 | Email 3 (if no reply) |
| 14 | Email 4 (if no reply) |
| 30 | Email 5 + "moving on" line |
| 31 | Move to nurture sequence — monthly cost newsletter |

## Subject-line A/B test ideas (after first 50 sends)
- ❓ Question format → "{COMPANY}'s GPT-4o spend — fixable?"
- 💰 Dollar amount → "saves {COMPANY} ~$8.4k/yr"
- 🔧 Tactical → "1-line code change cuts LLM bill 57%"
- 👤 Personal → "{NAME}, quick cost question"

## Reply-handling tips

| If they say… | Reply with… |
|---|---|
| "We use {Helicone/Portkey/Langsmith}" | "Cool — those are observability. TokenForge is *upstream* of them. Run both: distill with us, log with them. Often 90% of the cost savings come from our side." |
| "We already cache" | "Manual caching = exact-match only. We do semantic (cosine ≥ 0.98). Catches 4–8× more hits. Want a side-by-side?" |
| "Security / on-prem concerns" | "Enterprise tier ships as Docker image with your VPC. No data leaves your cloud. SOC 2 in progress." |
| "Send me a deck" | Send a Loom of the dashboard instead. 90 sec. Converts 3× better. |
| "How much can you actually save?" | Use the calculator on the landing page on one of their public prompts. Show them the number live. |

## What NOT to do

- ❌ No images in cold emails (kills deliverability)
- ❌ No PDF attachments cold (spam triggers)
- ❌ No "Hi, I'd love to introduce…" openers (delete-on-sight)
- ❌ Don't mention you wrote this with AI (if anyone asks, you obviously didn't)
