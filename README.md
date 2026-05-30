# TokenForge

**Multi-provider LLM optimization SaaS** — rent access to the best free and paid AI models without managing your own API keys.

- **Frontend**: React (CRA + craco) → `forge.alreadyherellc.com`
- **Backend**: FastAPI + MongoDB → `api.alreadyherellc.com`
- **Billing**: Stripe subscriptions ($19 / $99 / $499 per month)
- **Email**: Resend (transactional)

## Provider Priority (cost-optimised)

| Priority | Provider | Tier |
|---|---|---|
| 1 | Groq | Free (llama / gemma) |
| 2 | Google Gemini | Free (gemini-2.0-flash) |
| 3 | OpenAI | Paid |
| 4 | Anthropic | Paid |
| 5 | Pollinations | Keyless free fallback |

## Quick Start

```bash
# Backend
cp backend/.env.example backend/.env
# Fill in JWT_SECRET, MONGO_URL, STRIPE_API_KEY, GROQ_API_KEY, GOOGLE_API_KEY
cd backend && pip install -r requirements.txt
uvicorn server:app --reload

# Frontend
cd frontend && yarn install
REACT_APP_BACKEND_URL=http://localhost:8000 yarn start
```

## Subscription Tiers

| Plan | Price | Requests/day | BYOK |
|---|---|---|---|
| Free | $0 | 50 | No |
| Starter | $19/mo | 500 | No |
| Pro | $99/mo | 5,000 | Yes |
| Enterprise | $499/mo | Unlimited | Yes |

**BYOK (Bring Your Own Key)**: Pro+ customers can register their own provider API keys. Keys are encrypted at rest using Fernet derived from `JWT_SECRET`.

## Environment Variables

See `backend/.env.example` for the full list.  
**Never commit `.env` files** — use GitHub Secrets for CI and server `.env` for production.

## Deployment

- Backend: Docker or bare-metal on OCI (`api.alreadyherellc.com`)
- Frontend: Vercel (`forge.alreadyherellc.com`)
- See `deploy/` for OCI setup scripts

## CI

GitHub Actions runs on every push to `main`:
1. Backend lint (ruff)
2. Frontend build (yarn)
3. Integration tests (requires `TOKENFORGE_API_URL` secret — skipped until backend is deployed)
