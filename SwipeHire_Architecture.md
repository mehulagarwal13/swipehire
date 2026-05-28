 # SwipeHire — India AI Job Platform: Full Architecture & Build Guide

---

## 1. Product Vision

**SwipeHire** is an India-first, AI-powered job discovery and application platform. Users upload their resume once, and the system builds a rich profile. Jobs are presented as swipeable cards — right to apply, left to skip. The AI calculates match scores, auto-fills application forms, and tracks every application through its lifecycle.

**Target Users:** Students, freshers (0–2 yrs), and mid-level professionals in India  
**Core Problem Solved:** Reduces job search time from hours/week to minutes/day

---

## 2. Core Feature Set

| Feature | Description |
|---|---|
| Resume Parsing | AI extracts skills, experience, education, projects from uploaded PDF/DOCX |
| Smart Profiling | One-time setup: location, salary, job type, tech stack preferences |
| Job Aggregation | Pulls jobs from Naukri, LinkedIn, Internshala, company career pages, recruiter posts |
| AI Match Scoring | Scores each job 0–100 against user profile using embedding similarity + rule layers |
| Swipe Interface | Tinder-style card swipe — Right = Apply, Left = Skip, Up = Save |
| Auto-Apply Engine | Fills forms on supported portals using Playwright + stored profile data |
| Application Tracker | Kanban board — Applied → Screening → Interview → Offer / Rejected |
| Smart Notifications | WhatsApp + Email alerts for status changes, new matches >85 score |
| Recruiter Portal | Employers post jobs, view candidate matches, send interview invites |

---

## 3. Full Technology Stack

### 3.1 Frontend (Web & Mobile)

```
Framework:        Next.js 14 (App Router) — web
Mobile:           React Native (Expo) — iOS & Android
State Management: Zustand + React Query (TanStack Query v5)
Styling:          Tailwind CSS + shadcn/ui components
Animations:       Framer Motion (swipe physics, card transitions)
PWA:              next-pwa for installable web app
Auth UI:          NextAuth.js
```

**Why Next.js + React Native?** Code-sharing via a shared `packages/` monorepo (Turborepo). API types, hooks, and utility functions are shared between web and mobile.

### 3.2 Backend

```
Primary API:      Node.js + Fastify (REST + WebSocket)
AI Services:      Python + FastAPI (separate microservice)
Queue Worker:     BullMQ on Redis
Job Scheduler:    node-cron (job scraping schedule)
WebSockets:       Socket.IO (real-time notifications)
```

**Why Fastify over Express?** 3–4x faster throughput, built-in schema validation (Zod), TypeScript-first.

### 3.3 AI / ML Stack

```
LLM:              Google Gemini 1.5 Flash (cost-effective, Indian context aware)
Embeddings:       text-embedding-004 (Google) or OpenAI ada-002
Vector DB:        Qdrant (self-hosted on VPS) or Pinecone (managed)
Resume Parsing:   PyMuPDF + pdfplumber + custom NLP pipeline
NER:              spaCy (en_core_web_sm) for skill/tech extraction
Fallback LLM:     Groq (llama-3.1-70b) for high-volume inference
OCR:              Tesseract (for scanned resumes)
```

### 3.4 Databases

```
Primary DB:       PostgreSQL 16 (via Supabase — managed + auth + realtime)
Cache:            Redis 7 (Upstash — serverless Redis)
Vector Store:     Qdrant (job embeddings + user profile embeddings)
Object Storage:   Cloudflare R2 (resume files, profile photos)
Search:           Meilisearch (fast full-text job search)
```

### 3.5 Job Data Pipeline

```
Scraping:         Playwright (headless browser — career pages)
APIs:             RapidAPI LinkedIn Jobs, Naukri API, Indeed API
RSS Feeds:        Company blogs + job feeds
Parser:           Cheerio + custom extractors per domain
Deduplication:    Redis bloom filter + PostgreSQL unique constraints
```

### 3.6 Infrastructure & DevOps

```
Cloud:            AWS (primary) or Railway.app (budget start)
Container:        Docker + Docker Compose (dev), ECS Fargate (prod)
CDN:              Cloudflare (static assets, DDoS protection)
CI/CD:            GitHub Actions → ECR → ECS deploy
Monitoring:       Grafana + Prometheus + Sentry
Logs:             Loki (structured logs)
Secrets:          AWS Secrets Manager / Doppler
Email:            Resend.com (transactional emails)
WhatsApp:         Meta Cloud API / Twilio WhatsApp
SMS:              AWS SNS or MSG91 (India-optimized)
Payments:         Razorpay (subscriptions, India UPI/cards)
```

---

## 4. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                            │
│    Next.js Web App        React Native Mobile App           │
│    (Vercel / Cloudflare)  (Expo EAS Build → App Store)      │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS / WSS
┌──────────────────────▼──────────────────────────────────────┐
│                   API GATEWAY (Nginx / AWS ALB)              │
│              Rate limiting · Auth middleware · CORS          │
└──────┬──────────────────────┬──────────────────────┬─────────┘
       │                      │                      │
┌──────▼──────┐  ┌────────────▼──────┐  ┌────────────▼──────┐
│  Main API   │  │   AI Service       │  │  Job Scraper      │
│  (Fastify)  │  │   (FastAPI/Python) │  │  Worker (Node)    │
│  Port 3001  │  │   Port 8000        │  │  BullMQ Queue     │
└──────┬──────┘  └────────────┬──────┘  └────────────┬──────┘
       │                      │                      │
┌──────▼──────────────────────▼──────────────────────▼──────┐
│                    DATA LAYER                               │
│   PostgreSQL   │   Redis Cache   │   Qdrant Vector DB      │
│   (Supabase)   │   (Upstash)     │   (Self-hosted)         │
│                │                 │                          │
│   R2 Storage   │   Meilisearch   │   BullMQ Queues         │
└────────────────────────────────────────────────────────────┘
```

---

## 5. Database Schema (PostgreSQL)

### users
```sql
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone         VARCHAR(15) UNIQUE,  -- India: +91XXXXXXXXXX
  email         VARCHAR(255) UNIQUE,
  full_name     VARCHAR(255),
  profile_photo TEXT,  -- R2 URL
  plan          VARCHAR(20) DEFAULT 'free',  -- free | pro | premium
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);
```

### user_profiles
```sql
CREATE TABLE user_profiles (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id            UUID REFERENCES users(id) ON DELETE CASCADE,
  resume_url         TEXT,         -- R2 storage URL
  resume_text        TEXT,         -- Extracted plain text
  headline           VARCHAR(255), -- "Full-stack Developer, 2 yrs"
  skills             TEXT[],       -- ['React', 'Node.js', 'Python']
  experience_years   DECIMAL(3,1),
  current_location   VARCHAR(100), -- 'Bangalore, KA'
  preferred_locations TEXT[],      -- ['Bangalore', 'Remote', 'Mumbai']
  min_salary_lpa     DECIMAL(5,2), -- Lakhs per annum
  max_salary_lpa     DECIMAL(5,2),
  job_types          TEXT[],       -- ['full-time', 'internship', 'contract']
  notice_period_days INTEGER,
  education          JSONB,        -- [{degree, college, year, cgpa}]
  experience         JSONB,        -- [{company, role, duration, desc}]
  projects           JSONB,        -- [{name, stack, link, desc}]
  embedding_vector   VECTOR(1536), -- pgvector for profile embedding
  profile_score      INTEGER,      -- 0-100 completeness score
  updated_at         TIMESTAMPTZ DEFAULT NOW()
);
```

### jobs
```sql
CREATE TABLE jobs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id     VARCHAR(255),  -- Source system ID
  source          VARCHAR(50),   -- 'naukri' | 'linkedin' | 'scraped' | 'recruiter'
  title           VARCHAR(255) NOT NULL,
  company         VARCHAR(255) NOT NULL,
  company_logo    TEXT,
  location        VARCHAR(255),
  is_remote       BOOLEAN DEFAULT false,
  salary_min_lpa  DECIMAL(5,2),
  salary_max_lpa  DECIMAL(5,2),
  experience_min  DECIMAL(3,1),
  experience_max  DECIMAL(3,1),
  skills_required TEXT[],
  description     TEXT,
  apply_url       TEXT,
  job_type        VARCHAR(50),  -- full-time | internship | contract
  industry        VARCHAR(100),
  embedding_vector VECTOR(1536),
  is_active       BOOLEAN DEFAULT true,
  posted_at       TIMESTAMPTZ,
  expires_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(external_id, source)
);
CREATE INDEX idx_jobs_skills ON jobs USING GIN(skills_required);
CREATE INDEX idx_jobs_location ON jobs(location);
CREATE INDEX idx_jobs_posted ON jobs(posted_at DESC);
```

### swipes
```sql
CREATE TABLE swipes (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES users(id),
  job_id      UUID REFERENCES jobs(id),
  direction   VARCHAR(10),  -- 'right' | 'left' | 'up' (save)
  match_score INTEGER,      -- Score at time of swipe
  swiped_at   TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, job_id)
);
```

### applications
```sql
CREATE TABLE applications (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID REFERENCES users(id),
  job_id          UUID REFERENCES jobs(id),
  swipe_id        UUID REFERENCES swipes(id),
  status          VARCHAR(50) DEFAULT 'applied',
  -- applied → screening → interview → offer | rejected | withdrawn
  applied_at      TIMESTAMPTZ DEFAULT NOW(),
  auto_applied    BOOLEAN DEFAULT false,
  notes           TEXT,
  interview_date  TIMESTAMPTZ,
  offer_amount    DECIMAL(6,2),  -- LPA
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### job_match_scores (precomputed cache)
```sql
CREATE TABLE job_match_scores (
  user_id       UUID REFERENCES users(id),
  job_id        UUID REFERENCES jobs(id),
  score         INTEGER,       -- 0-100
  score_details JSONB,         -- {skills: 85, experience: 70, location: 90, salary: 75}
  computed_at   TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (user_id, job_id)
);
```

---

## 6. AI Pipeline: Resume → Profile

### Step 1: File Upload & Text Extraction
```
User uploads PDF/DOCX
→ Stored in Cloudflare R2
→ Job queued: EXTRACT_RESUME {userId, fileUrl}
→ Worker downloads file
→ pdfplumber extracts text (handles multi-column PDFs)
→ Tesseract OCR fallback for scanned PDFs
→ Raw text stored in user_profiles.resume_text
```

### Step 2: Structured Data Extraction (Python FastAPI)
```python
# FastAPI endpoint: POST /ai/parse-resume
async def parse_resume(text: str) -> ResumeData:
    prompt = f"""
    Extract structured data from this Indian resume. Return JSON only:
    {{
      "full_name": "...",
      "email": "...",
      "phone": "...",
      "skills": ["React", "Python", ...],
      "experience_years": 2.5,
      "education": [{{
        "degree": "B.Tech CSE",
        "college": "VIT Vellore",
        "year": 2022,
        "cgpa": 8.4
      }}],
      "experience": [{{
        "company": "Infosys",
        "role": "SDE-1",
        "duration": "Jun 2022 - Present",
        "description": "..."
      }}],
      "current_location": "Hyderabad",
      "certifications": [...],
      "projects": [...]
    }}
    Resume text:
    {text}
    """
    response = gemini.generate_content(prompt)
    return ResumeData(**json.loads(response.text))
```

### Step 3: Profile Embedding Generation
```python
# Generate 1536-dim embedding from profile summary
profile_summary = f"""
{skills} | {experience_years} years | {education} | {projects}
Location: {location} | Salary expectation: {min_lpa}-{max_lpa} LPA
"""
embedding = embed_model.get_embeddings([profile_summary])[0].values
# Store in PostgreSQL pgvector column AND Qdrant
```

---

## 7. AI Match Scoring Algorithm

The match score (0–100) is a weighted composite:

```
Score = (
  skill_overlap_score  × 0.35  +
  experience_score     × 0.20  +
  location_score       × 0.15  +
  salary_score         × 0.15  +
  semantic_similarity  × 0.15
)
```

### Skill Overlap Score
```python
def skill_overlap_score(user_skills, job_skills):
    # Normalize: lowercase, remove spaces
    user_set = {s.lower().strip() for s in user_skills}
    job_set  = {s.lower().strip() for s in job_skills}
    
    # Exact matches
    exact = len(user_set & job_set) / len(job_set) if job_set else 0
    
    # Fuzzy matches (handles "ReactJS" vs "React.js")
    fuzzy_matches = sum(
        1 for js in job_set
        if any(fuzz.ratio(js, us) > 85 for us in user_set)
    ) / len(job_set) if job_set else 0
    
    return min(round((exact * 0.7 + fuzzy_matches * 0.3) * 100), 100)
```

### Semantic Similarity (Vector Search)
```python
# Query Qdrant: find top-N jobs by cosine similarity to user embedding
results = qdrant_client.search(
    collection_name="jobs",
    query_vector=user_embedding,
    limit=200,
    score_threshold=0.65
)
# Returns jobs with cosine similarity scores
```

### Experience Score
```python
def experience_score(user_years, job_min, job_max):
    if user_years < job_min:
        # Under-qualified: penalise proportionally
        gap = job_min - user_years
        return max(0, 100 - gap * 25)
    elif user_years > job_max + 3:
        # Overqualified: slight penalty
        return 75
    return 100
```

---

## 8. Job Aggregation Pipeline

### 8.1 Scrapers (Playwright)

Scrapers run every 6 hours via cron. Each domain has a custom extractor:

```javascript
// Example: Naukri scraper
class NaukriScraper {
  async scrape(keywords, location, pages = 5) {
    const browser = await chromium.launch({ headless: true });
    const jobs = [];
    
    for (let page = 1; page <= pages; page++) {
      const url = `https://www.naukri.com/${keywords}-jobs-in-${location}-${page}`;
      await page.goto(url, { waitUntil: 'networkidle' });
      
      const listings = await page.$$eval('.jobTuple', nodes =>
        nodes.map(n => ({
          title:    n.querySelector('.title')?.innerText,
          company:  n.querySelector('.companyInfo a')?.innerText,
          location: n.querySelector('.locWdth')?.innerText,
          skills:   [...n.querySelectorAll('.tag')].map(t => t.innerText),
          url:      n.querySelector('.title')?.href,
          posted:   n.querySelector('.freshness')?.innerText
        }))
      );
      jobs.push(...listings);
    }
    return jobs;
  }
}
```

### 8.2 Deduplication
```javascript
// Redis bloom filter check before DB insert
async function isDuplicate(job) {
  const key = `${job.source}:${job.title}:${job.company}`.toLowerCase();
  const hash = crypto.createHash('md5').update(key).digest('hex');
  
  const exists = await redis.bf.exists('jobs_bloom', hash);
  if (!exists) await redis.bf.add('jobs_bloom', hash);
  return exists;
}
```

### 8.3 Job Sources Priority

| Source | Method | Frequency | Volume/day |
|---|---|---|---|
| Naukri | Scraper | Every 6h | ~5,000 |
| LinkedIn | RapidAPI | Every 2h | ~2,000 |
| Internshala | Scraper | Every 12h | ~1,000 |
| Company pages (top 500) | Playwright | Every 24h | ~3,000 |
| Recruiter posts (platform) | Real-time | Immediate | ~500 |
| Instahyre | API | Every 6h | ~800 |

---

## 9. Swipe Interface Implementation

### Card Data Structure (Frontend)
```typescript
interface JobCard {
  id: string;
  title: string;
  company: string;
  companyLogo: string;
  location: string;
  isRemote: boolean;
  salaryMin: number;  // LPA
  salaryMax: number;
  skills: string[];
  matchScore: number;  // 0-100
  experienceRange: string;  // "2-4 years"
  postedAt: string;
  highlights: string[];  // AI-generated 3 bullets
}
```

### Swipe Physics (React + Framer Motion)
```typescript
function JobCard({ job, onSwipe }) {
  const [isDragging, setDragging] = useState(false);
  
  const handleDragEnd = (event, info) => {
    const threshold = 120;  // px
    
    if (info.offset.x > threshold) {
      onSwipe('right', job.id);   // Apply
      animate(x, 500, { duration: 0.3 });
    } else if (info.offset.x < -threshold) {
      onSwipe('left', job.id);    // Skip
      animate(x, -500, { duration: 0.3 });
    } else if (info.offset.y < -threshold) {
      onSwipe('up', job.id);      // Save
      animate(y, -500, { duration: 0.3 });
    } else {
      animate(x, 0, { type: 'spring', stiffness: 400 });
    }
  };

  return (
    <motion.div
      drag
      dragConstraints={{ left: 0, right: 0, top: 0, bottom: 0 }}
      onDragEnd={handleDragEnd}
      style={{ rotate: useTransform(x, [-150, 150], [-15, 15]) }}
    >
      {/* Card content */}
    </motion.div>
  );
}
```

### Card Feed API
```typescript
// GET /api/v1/jobs/feed?limit=20&offset=0
// Returns pre-scored, pre-filtered jobs not yet seen by user

async function getJobFeed(userId: string, limit = 20) {
  // 1. Get user's already-swiped job IDs
  const seenIds = await getSeenJobIds(userId);
  
  // 2. Query precomputed match scores
  const scored = await db.query(`
    SELECT j.*, jms.score, jms.score_details
    FROM jobs j
    JOIN job_match_scores jms ON j.id = jms.job_id
    WHERE jms.user_id = $1
    AND j.id NOT IN (${seenIds.join(',')})
    AND j.is_active = true
    ORDER BY jms.score DESC, j.posted_at DESC
    LIMIT $2
  `, [userId, limit]);
  
  // 3. Enrich with AI-generated highlights
  return enrichWithHighlights(scored);
}
```

---

## 10. Auto-Apply Engine

### Supported Portals (Phase 1)
- Naukri.com — form fill via Playwright
- Internshala — form fill + resume upload
- Lever-based portals (many Indian startups)
- Greenhouse-based portals

### Auto-Apply Flow
```
User swipes right → 
  Check if portal supports auto-apply →
    YES: Queue job AUTOAPPLY { userId, jobId, applyUrl }
      → Worker runs Playwright session
      → Fills form fields from user profile
      → Uploads resume from R2
      → Submits form
      → Screenshots confirmation
      → Updates application status to 'applied'
    NO: Open portal in in-app browser
      → Pre-fill form with stored data
      → User reviews & submits manually
```

### Playwright Auto-Apply Worker
```python
async def auto_apply(user_profile, job):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(job.apply_url)
        
        # Detect form type
        form_type = await detect_form_type(page)
        
        if form_type == 'naukri':
            await fill_naukri_form(page, user_profile)
        elif form_type == 'lever':
            await fill_lever_form(page, user_profile)
        elif form_type == 'greenhouse':
            await fill_greenhouse_form(page, user_profile)
        
        # Upload resume
        resume_path = await download_resume_temp(user_profile.resume_url)
        await page.set_input_files('input[type=file]', resume_path)
        
        # Submit
        await page.click('button[type=submit]')
        await page.wait_for_load_state('networkidle')
        
        # Capture confirmation
        screenshot = await page.screenshot()
        confirmation_url = page.url
        
        return { 'success': True, 'confirmation_url': confirmation_url }
```

---

## 11. Application Tracker

### Status State Machine
```
applied → screening → interview_scheduled → interview_completed
                   ↘ rejected
                   ↘ offer_extended → offer_accepted | offer_rejected
                   ↘ withdrawn (by user)
```

### Tracker API
```typescript
// PATCH /api/v1/applications/:id/status
async function updateApplicationStatus(appId, newStatus, metadata) {
  const app = await db.applications.findById(appId);
  
  // Validate state transition
  validateTransition(app.status, newStatus);
  
  // Update
  await db.applications.update(appId, {
    status: newStatus,
    interview_date: metadata?.interviewDate,
    offer_amount: metadata?.offerAmount,
    updated_at: new Date()
  });
  
  // Trigger notification
  await notifyUser(app.user_id, {
    type: 'status_change',
    job: app.job,
    oldStatus: app.status,
    newStatus
  });
  
  // Update analytics
  await updateUserAnalytics(app.user_id);
}
```

---

## 12. Notification System

### WhatsApp Integration (Meta Cloud API)
```javascript
// Triggered on: new matches, interview invites, offers
async function sendWhatsAppNotification(phone, template, variables) {
  await axios.post(
    `https://graph.facebook.com/v18.0/${PHONE_NUMBER_ID}/messages`,
    {
      messaging_product: 'whatsapp',
      to: `91${phone}`,
      type: 'template',
      template: {
        name: template,  // 'new_match', 'interview_invite', 'offer_received'
        language: { code: 'en_IN' },
        components: [{ type: 'body', parameters: variables }]
      }
    },
    { headers: { Authorization: `Bearer ${WHATSAPP_TOKEN}` } }
  );
}
```

### Notification Templates
- **new_match**: "🎯 You have 5 new jobs matching 85%+ today! [Open SwipeHire]"
- **application_viewed**: "👁️ {Company} viewed your application for {Role}"
- **interview_invite**: "🎉 Interview scheduled at {Company} on {Date}"

---

## 13. Project Structure (Monorepo)

```
swipehire/
├── apps/
│   ├── web/                    # Next.js 14
│   │   ├── app/
│   │   │   ├── (auth)/
│   │   │   │   ├── login/
│   │   │   │   └── onboarding/
│   │   │   ├── (dashboard)/
│   │   │   │   ├── swipe/       # Main swipe feed
│   │   │   │   ├── applications/ # Tracker
│   │   │   │   ├── profile/
│   │   │   │   └── insights/
│   │   │   └── api/
│   │   │       ├── auth/
│   │   │       └── webhooks/
│   │   ├── components/
│   │   │   ├── swipe/
│   │   │   │   ├── JobCard.tsx
│   │   │   │   ├── SwipeDeck.tsx
│   │   │   │   └── MatchBadge.tsx
│   │   │   └── tracker/
│   │   └── lib/
│   │
│   ├── mobile/                 # React Native (Expo)
│   │   ├── app/
│   │   │   ├── (tabs)/
│   │   │   │   ├── index.tsx    # Swipe feed
│   │   │   │   ├── applications.tsx
│   │   │   │   └── profile.tsx
│   │   └── components/
│   │
│   ├── api/                    # Fastify API
│   │   ├── src/
│   │   │   ├── routes/
│   │   │   │   ├── auth.ts
│   │   │   │   ├── jobs.ts
│   │   │   │   ├── swipes.ts
│   │   │   │   ├── applications.ts
│   │   │   │   └── profile.ts
│   │   │   ├── services/
│   │   │   │   ├── matchingService.ts
│   │   │   │   ├── notificationService.ts
│   │   │   │   └── autoApplyService.ts
│   │   │   ├── workers/
│   │   │   │   ├── resumeParser.worker.ts
│   │   │   │   ├── matchScore.worker.ts
│   │   │   │   └── autoApply.worker.ts
│   │   │   └── db/
│   │   │       ├── schema.ts    # Drizzle ORM schema
│   │   │       └── migrations/
│   │
│   └── ai-service/             # Python FastAPI
│       ├── main.py
│       ├── routers/
│       │   ├── resume.py
│       │   ├── matching.py
│       │   └── embeddings.py
│       ├── services/
│       │   ├── parser.py
│       │   ├── scorer.py
│       │   └── embedder.py
│       └── scrapers/
│           ├── naukri.py
│           ├── linkedin.py
│           └── internshala.py
│
└── packages/
    ├── shared-types/           # TypeScript interfaces
    ├── ui/                     # Shared React components
    └── utils/                  # Shared utilities
```

---

## 14. Authentication & Security

### Auth Flow (India-optimized)
```
Option 1: Phone OTP (preferred for India)
  → User enters +91 number
  → OTP sent via MSG91 / AWS SNS
  → Verify OTP → JWT issued

Option 2: Google OAuth
  → nextAuth.js Google provider

JWT Strategy:
  → Access token: 15 min TTL
  → Refresh token: 30 days, HttpOnly cookie
  → Stored in Redis for instant revocation
```

### Security Measures
- All resumes encrypted at rest (AES-256) in R2
- Row-level security (RLS) in Supabase PostgreSQL
- API rate limiting: 100 req/min per user, 10 req/min for auth endpoints
- Helmet.js headers, CORS whitelist
- Auto-apply sessions run in isolated containers
- PII masking in logs

---

## 15. Monetisation Strategy

### Free Tier
- 20 swipes/day
- Manual apply only
- Basic match scores
- 5 active applications

### Pro (₹299/month)
- Unlimited swipes
- Auto-apply on 10 portals
- Detailed score breakdown
- Priority job feed
- WhatsApp notifications

### Premium (₹699/month)
- Everything in Pro
- Resume AI rewrite for each job
- Interview prep AI (company-specific Q&A)
- Salary negotiation insights
- Dedicated application manager

### Recruiter Portal (₹4,999/month per seat)
- Post jobs (unlimited)
- AI candidate matching
- Direct messaging
- Interview scheduling

---

## 16. Build Phases (Roadmap)

### Phase 0 — Foundation (Month 1–2)
- [ ] Monorepo setup (Turborepo + pnpm)
- [ ] Supabase PostgreSQL schema
- [ ] Auth: Phone OTP + Google OAuth
- [ ] Resume upload + pdfplumber extraction
- [ ] Gemini resume parser API
- [ ] Basic job CRUD

### Phase 1 — MVP (Month 3–4)
- [ ] Naukri + LinkedIn scrapers
- [ ] Match scoring algorithm v1
- [ ] Swipe UI (web)
- [ ] Basic application tracker
- [ ] Email notifications

### Phase 2 — AI Enhancement (Month 5–6)
- [ ] Vector embeddings (Qdrant)
- [ ] Semantic matching v2
- [ ] React Native mobile app
- [ ] WhatsApp notifications
- [ ] Auto-apply for Naukri + Internshala

### Phase 3 — Growth (Month 7–9)
- [ ] Recruiter portal
- [ ] AI interview prep feature
- [ ] Resume rewriter
- [ ] Razorpay subscriptions
- [ ] Analytics dashboard

### Phase 4 — Scale (Month 10–12)
- [ ] 10+ more job source scrapers
- [ ] ML model fine-tuning on Indian job data
- [ ] Browser extension for quick apply
- [ ] API for third-party integration

---

## 17. Infrastructure Cost Estimate (MVP)

| Service | Plan | Monthly Cost |
|---|---|---|
| Supabase (PostgreSQL) | Pro | ₹1,700 (~$20) |
| Vercel (Next.js) | Pro | ₹850 (~$10) |
| Railway (API + AI service) | Starter | ₹2,500 (~$30) |
| Upstash Redis | Pay-as-go | ₹500 (~$6) |
| Qdrant Cloud | Free tier | ₹0 |
| Cloudflare R2 (storage) | Free tier | ₹0 |
| Resend (email) | Free tier (3k/mo) | ₹0 |
| Gemini API (AI) | ~1M tokens/day | ₹4,200 (~$50) |
| **Total MVP** | | **~₹10,000/mo** |

---

## 18. Key India-Specific Considerations

1. **Hindi support** — UI strings in both English and Hindi (i18next)
2. **Salary in LPA** — All salary displayed as Lakhs Per Annum, not USD
3. **College tier awareness** — IIT/NIT/BITS gets separate scoring weight
4. **Notice period** — Common Indian HR requirement; include in profile
5. **Service sector jobs** — BFSI, IT services, BPO are major categories; weight accordingly
6. **Location specificity** — Tier 1 (Bengaluru, Mumbai, Delhi NCR), Tier 2 (Pune, Hyderabad, Chennai), Tier 3 (Jaipur, Indore) — separate scoring for each
7. **Freshers segment** — Campuses, 0-1 year exp, CTC instead of LPA
8. **Resume styles** — Indian resumes often have photos, DOB, hobbies — parser must handle these gracefully

---

*Document version: 1.0 | Platform: SwipeHire India*
