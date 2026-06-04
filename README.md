# ⚡ SwipeHire — India's AI-Powered Job Platform

Swipe right on your dream job. SwipeHire is a Tinder-style job discovery platform built for the Indian market, powered by AI matching, resume parsing, and auto-apply automation.

---

## 🚀 Run Commands (All Services)

| What | Command | URL |
|---|---|---|
| Databases | `docker-compose up -d postgres redis qdrant meilisearch` | — |
| API server | `uvicorn main:app --reload --port 8000` | http://localhost:8000/docs |
| Web app | `pnpm dev` (from `apps/web`) | http://localhost:3000 |
| Mobile app | `npx expo start` (from `apps/mobile`) | Expo Go / Emulator |
| Celery worker | `celery -A workers.celery_app worker -Q scraping,ml,apply,default` | — |
| Celery beat | `celery -A workers.celery_app beat` | — |
| Celery monitor | `celery -A workers.celery_app flower` | http://localhost:5555 |
| Backend tests | `python -m pytest tests/ -v` (from `apps/ai-service`) | 48 tests |
| E2E tests | `npx playwright test` (from `apps/web`) | — |

---

## ⚡ Quick Start (TL;DR)

```bash
# 1. Clone + configure
git clone https://github.com/your-org/swipehire.git && cd swipehire
cp .env.example .env          # set JWT_SECRET and NEXTAUTH_SECRET at minimum

# 2. Start databases
docker-compose up -d postgres redis qdrant meilisearch

# 3. Backend
cd apps/ai-service
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python seed_jobs.py                                  # load 100 sample jobs
uvicorn main:app --reload --port 8000               # → http://localhost:8000/docs

# 4. Web app (new terminal)
cd ../..
pnpm install
cd apps/web && pnpm dev                              # → http://localhost:3000
```

Login at http://localhost:3000/login → enter any 10-digit phone → OTP appears in the backend terminal → enter it → done.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web App | Next.js 14 (App Router), Tailwind CSS, Framer Motion |
| Mobile | React Native (Expo) |
| Backend API | Python FastAPI |
| ML / AI | sentence-transformers, scikit-learn, Google Gemini 1.5 Flash |
| Database | PostgreSQL 16 + pgvector (Supabase) |
| Cache | Redis (Upstash) |
| Vector Search | Qdrant |
| Full-text Search | Meilisearch |
| File Storage | Cloudflare R2 |
| Auth | Phone OTP (MSG91) + Google OAuth + JWT |
| Payments | Razorpay (UPI / cards) |
| Notifications | WhatsApp (Meta Cloud API) + Email (Resend) |

---

## Project Structure

```
swipehire/
├── apps/
│   ├── web/            # Next.js 14 web app      (port 3000)
│   ├── mobile/         # React Native Expo app
│   └── ai-service/     # FastAPI backend + ML    (port 8000)
├── packages/
│   └── shared-types/   # Shared TypeScript types
├── scripts/
│   └── init.sql        # PostgreSQL schema (auto-runs in Docker)
├── docker-compose.yml
├── .env.example
└── turbo.json
```

---

## Prerequisites

- **Node.js** ≥ 20, **pnpm** ≥ 9
- **Python** 3.12+
- **Docker** + Docker Compose
- (Optional) API keys: Gemini, MSG91, Razorpay, Resend, WhatsApp

---

## Local Development Setup

### 1. Clone and configure

```bash
git clone https://github.com/your-org/swipehire.git
cd swipehire
cp .env.example .env
# Edit .env and fill in at minimum: JWT_SECRET, NEXTAUTH_SECRET
```

### 2. Start infrastructure services

```bash
docker-compose up -d postgres redis qdrant meilisearch
```

Wait ~10 seconds for PostgreSQL to initialise. The `scripts/init.sql` runs automatically and creates all tables, indexes, and extensions (`pgvector`, `pg_trgm`, `uuid-ossp`).

Verify services are up:
```bash
docker-compose ps
# postgres, redis, qdrant, meilisearch should all show "healthy" / "running"
```

### 3. Set up the AI/Backend service

```bash
cd apps/ai-service

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy language model
python -m spacy download en_core_web_sm

# Install Playwright browser (for job scraping + auto-apply)
playwright install chromium

# Seed 100 sample jobs
python seed_jobs.py

# Index jobs into Qdrant (run after seeding)
python scripts/index_jobs_qdrant.py

# Start the API server
uvicorn main:app --reload --port 8000
```

API docs → http://localhost:8000/docs

### 4. Set up the Next.js web app

```bash
# From repo root — installs all workspaces at once
pnpm install

# Copy env for web
cp .env.example apps/web/.env.local
# Ensure NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

cd apps/web
pnpm dev
```

Web app → http://localhost:3000

### 5. Set up the React Native mobile app (optional)

```bash
cd apps/mobile
npm install

# Install Expo CLI globally (first time only)
npm install -g expo-cli

# Run on Android emulator or physical device
npx expo start --android

# Run on iOS simulator (macOS only)
npx expo start --ios

# Scan QR code with Expo Go app on your phone
npx expo start
```

> Set `EXPO_PUBLIC_API_URL=http://<YOUR_LOCAL_IP>:8000/api/v1` in `apps/mobile/.env`  
> (Use your machine's LAN IP, not `localhost`, so the phone can reach the backend)

### 6. First login (dev mode)

1. Go to http://localhost:3000/login
2. Enter any 10-digit number (e.g. `9876543210`)
3. Click **Send OTP** — the OTP prints to the AI service terminal as `[DEV] OTP for ...`
4. Enter the OTP → you're in!
5. Complete the 5-step onboarding wizard

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values below.

### Required (app won't start without these)

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET` | ≥ 32 character secret for signing JWTs |
| `NEXTAUTH_SECRET` | NextAuth.js secret |
| `NEXTAUTH_URL` | e.g. `http://localhost:3000` |

### AI / ML

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key (resume parsing) |
| `GROQ_API_KEY` | Groq API key (fallback LLM) |

### Auth & Notifications (optional in dev, required in prod)

| Variable | Description |
|---|---|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `MSG91_AUTH_KEY` | SMS OTP via MSG91 (India) |
| `MSG91_OTP_TEMPLATE_ID` | DLT-approved OTP template ID |
| `RESEND_API_KEY` | Transactional email |
| `WHATSAPP_ACCESS_TOKEN` | Meta Cloud API token |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp Business phone number ID |

### Storage & Search

| Variable | Description |
|---|---|
| `CLOUDFLARE_R2_ACCESS_KEY` | R2 storage for resumes |
| `CLOUDFLARE_R2_SECRET_KEY` | R2 secret key |
| `CLOUDFLARE_R2_BUCKET` | R2 bucket name |
| `QDRANT_URL` | Qdrant vector DB URL |
| `REDIS_URL` | Redis connection string |
| `MEILISEARCH_URL` | Meilisearch URL |
| `MEILISEARCH_MASTER_KEY` | Meilisearch master key |

### Payments

| Variable | Description |
|---|---|
| `RAZORPAY_KEY_ID` | Razorpay key ID |
| `RAZORPAY_KEY_SECRET` | Razorpay key secret |
| `RAZORPAY_WEBHOOK_SECRET` | Razorpay webhook signing secret |

---

## Running Tests

### Backend (pytest)

```bash
cd apps/ai-service
source .venv/bin/activate

# Run full test suite (48 tests)
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_ml.py -v       # ML scorer unit tests
python -m pytest tests/test_auth.py -v     # Auth endpoints
python -m pytest tests/test_jobs.py -v     # Jobs feed + search
python -m pytest tests/test_swipes.py -v   # Swipe recording
python -m pytest tests/test_profile.py -v  # Profile management
```

Tests use an in-memory SQLite database — no running PostgreSQL needed. Heavy ML deps (sentence-transformers) are mocked automatically.

Expected output:
```
======================== 48 passed, 1 warning in 0.68s =========================
```

### Web E2E (Playwright)

```bash
cd apps/web

# Install Playwright browsers (first time only)
npx playwright install chromium

# Run E2E tests (requires web app running on port 3000)
npx playwright test

# Run with UI mode (headed browser, great for debugging)
npx playwright test --ui

# Run specific test file
npx playwright test tests/e2e/swipe-flow.spec.ts
```

---

## Useful Commands

### Seed & Index

```bash
# Seed 100 realistic Indian tech jobs
cd apps/ai-service && python seed_jobs.py

# Index all jobs into Qdrant for vector search
python scripts/index_jobs_qdrant.py

# Run Naukri scraper manually
python -c "
import asyncio
from scrapers.naukri import NaukriScraper
async def main():
    async with NaukriScraper() as s:
        jobs = await s.scrape('python developer', 'bangalore', pages=2)
        print(f'Scraped {len(jobs)} jobs')
asyncio.run(main())
"
```

### Database

```bash
# Connect to local PostgreSQL
docker exec -it swipehire_postgres psql -U swipehire -d swipehire

# Check job count
SELECT source, COUNT(*) FROM jobs GROUP BY source;

# Check users
SELECT id, phone, email, plan FROM users;
```

### Logs

```bash
# All services
docker-compose logs -f

# AI service only
docker-compose logs -f ai-service
```

---

## Deployment

### Backend → Railway

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login
railway up --service ai-service
```

Set all environment variables in the Railway dashboard.

### Web → Vercel

```bash
npx vercel --prod
```

Set environment variables in Vercel project settings.

### Mobile → Expo EAS

```bash
cd apps/mobile
npm install -g eas-cli
eas login
eas build --platform android   # Android APK/AAB
eas build --platform ios       # iOS IPA
```

---

## Monetisation

| Plan | Price | Key Features |
|---|---|---|
| Free | ₹0 | 20 swipes/day, manual apply only |
| Pro | ₹299/month | Unlimited swipes, auto-apply, WhatsApp alerts |
| Premium | ₹699/month | Everything + AI resume rewrite, interview prep |
| Recruiter | ₹4,999/month | Job posting, candidate matching, direct messaging |

---

## Architecture Overview

```
Client (Next.js / React Native)
        │ HTTPS / JWT
        ▼
FastAPI AI Service (port 8000)
   ├── Auth (OTP + Google OAuth)
   ├── Jobs Feed (ML-ranked via Qdrant ANN)
   ├── Swipes + Applications Tracker
   ├── Profile + Resume Parser (Gemini)
   ├── Auto-Apply Engine (Playwright)
   └── Notifications (WhatsApp + Email)
        │
        ▼
Data Layer
   ├── PostgreSQL + pgvector  (primary DB)
   ├── Redis                  (OTP store, cache, queues)
   ├── Qdrant                 (job embeddings — ANN search)
   ├── Meilisearch            (full-text job search)
   └── Cloudflare R2          (resume file storage)
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'asyncpg'`**
```bash
pip install asyncpg --break-system-packages
```

**`docker-compose up` fails — port already in use**
```bash
# Find and kill the process using the port (e.g. 5432)
lsof -i :5432 | awk 'NR>1 {print $2}' | xargs kill -9
```

**`pgvector` extension missing on startup**  
The `scripts/init.sql` runs automatically in Docker. If you're using an external PostgreSQL, run:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

**OTP not appearing in terminal**  
Make sure `DEBUG=true` is set in your `.env`. The OTP prints as `[DEV] OTP for 9876543210: 123456`.

**`pnpm install` fails — wrong Node version**  
```bash
node --version   # must be >= 20
nvm use 20       # if using nvm
```

**Qdrant index not finding jobs**  
Run the indexing script after seeding:
```bash
cd apps/ai-service && python scripts/index_jobs_qdrant.py
```

**Next.js build error: `authOptions` not found**  
The `authOptions` live in `apps/web/lib/auth.ts`. Make sure this file exists and is not empty.

**Mobile app can't reach backend**  
Use your machine's LAN IP (not `localhost`) in `EXPO_PUBLIC_API_URL`:
```bash
# Find your LAN IP
ipconfig    # Windows
ifconfig    # macOS/Linux
# Then set: EXPO_PUBLIC_API_URL=http://192.168.x.x:8000/api/v1
```

---

## Service Ports

| Service | Port | URL |
|---|---|---|
| Next.js web | 3000 | http://localhost:3000 |
| FastAPI backend | 8000 | http://localhost:8000/docs |
| PostgreSQL | 5432 | `postgresql://swipehire:swipehire123@localhost:5432/swipehire` |
| Redis | 6379 | `redis://localhost:6379` |
| Qdrant | 6333 | http://localhost:6333/dashboard |
| Meilisearch | 7700 | http://localhost:7700 |

---

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Run tests: `cd apps/ai-service && python -m pytest tests/ -v`
4. Open a PR against `develop`

---

*SwipeHire v1.0 · Built for India 🇮🇳*
