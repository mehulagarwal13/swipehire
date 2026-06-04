# SwipeHire — Local Development Setup

## Prerequisites

- Node.js 20+, pnpm 9+
- Python 3.12+
- Docker + Docker Compose
- (Optional) Gemini API key for resume parsing

---

## 1. Clone & install

```bash
git clone <repo>
cd swipehire
cp .env.example .env          # fill in secrets
pnpm install                  # install all JS deps
```

---

## 2. Start infrastructure

```bash
docker-compose up -d postgres redis qdrant meilisearch
```

Wait ~10 seconds for PostgreSQL to initialize.  
The `scripts/init.sql` runs automatically and creates all tables + extensions.

---

## 3. Start the AI / backend service

```bash
cd apps/ai-service
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
playwright install chromium

# Seed 100 sample jobs
python seed_jobs.py

# Start the server
uvicorn main:app --reload --port 8000
```

API docs → http://localhost:8000/docs

---

## 4. Start the Next.js web app

```bash
cd apps/web
cp ../../.env.example .env.local  # ensure NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
pnpm dev
```

Web app → http://localhost:3000

---

## 5. First login (dev mode)

1. Go to http://localhost:3000/login
2. Enter any 10-digit number (e.g. `9876543210`)
3. Click "Send OTP" — the OTP appears in the terminal as `[DEV OTP]`
4. Enter OTP → you're in!

---

## Project Structure

```
swipehire/
├── apps/
│   ├── web/          ← Next.js 14 (port 3000)
│   └── ai-service/   ← FastAPI + ML (port 8000)
├── packages/
│   └── shared-types/ ← TypeScript interfaces
├── scripts/
│   └── init.sql      ← DB schema (auto-runs in Docker)
├── docker-compose.yml
└── .env.example
```

---

## Key environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `GEMINI_API_KEY` | Google Gemini — for resume parsing |
| `JWT_SECRET` | ≥32 char secret for JWT signing |
| `NEXTAUTH_SECRET` | NextAuth.js secret |
| `GOOGLE_CLIENT_ID/SECRET` | Google OAuth (optional) |

---

## Running scrapers manually

```bash
cd apps/ai-service
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

---

## Deployment

| Service | Platform | Notes |
|---|---|---|
| Next.js web | Vercel | Auto-deploys from `main` branch |
| AI service | Railway / Render | Docker container, port 8000 |
| PostgreSQL | Supabase | Managed, includes pgvector |
| Redis | Upstash | Serverless, free tier |
| Qdrant | Qdrant Cloud | Free tier (1GB) |
| File storage | Cloudflare R2 | 10GB free |
