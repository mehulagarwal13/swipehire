-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- for fuzzy text search
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- ─── USERS ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone         VARCHAR(15) UNIQUE,
  email         VARCHAR(255) UNIQUE,
  full_name     VARCHAR(255),
  profile_photo TEXT,
  plan          VARCHAR(20) DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'premium')),
  is_verified   BOOLEAN DEFAULT false,
  is_active     BOOLEAN DEFAULT true,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ─── USER PROFILES ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_profiles (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id              UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
  resume_url           TEXT,
  resume_text          TEXT,
  headline             VARCHAR(255),
  skills               TEXT[] DEFAULT '{}',
  experience_years     DECIMAL(3,1) DEFAULT 0,
  current_location     VARCHAR(100),
  preferred_locations  TEXT[] DEFAULT '{}',
  min_salary_lpa       DECIMAL(5,2),
  max_salary_lpa       DECIMAL(5,2),
  job_types            TEXT[] DEFAULT '{}',
  notice_period_days   INTEGER DEFAULT 30,
  education            JSONB DEFAULT '[]',
  experience           JSONB DEFAULT '[]',
  projects             JSONB DEFAULT '[]',
  certifications       JSONB DEFAULT '[]',
  embedding_vector     vector(1536),
  profile_score        INTEGER DEFAULT 0 CHECK (profile_score BETWEEN 0 AND 100),
  is_onboarded         BOOLEAN DEFAULT false,
  updated_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_embedding
  ON user_profiles USING ivfflat (embedding_vector vector_cosine_ops)
  WITH (lists = 100);

-- ─── JOBS ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS jobs (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id      VARCHAR(255),
  source           VARCHAR(50) NOT NULL CHECK (source IN ('naukri','linkedin','internshala','instahyre','scraped','recruiter','seed')),
  title            VARCHAR(255) NOT NULL,
  company          VARCHAR(255) NOT NULL,
  company_logo     TEXT,
  location         VARCHAR(255),
  is_remote        BOOLEAN DEFAULT false,
  salary_min_lpa   DECIMAL(5,2),
  salary_max_lpa   DECIMAL(5,2),
  experience_min   DECIMAL(3,1) DEFAULT 0,
  experience_max   DECIMAL(3,1) DEFAULT 50,
  skills_required  TEXT[] DEFAULT '{}',
  description      TEXT,
  apply_url        TEXT,
  job_type         VARCHAR(50) CHECK (job_type IN ('full-time','part-time','internship','contract','freelance')),
  industry         VARCHAR(100),
  embedding_vector vector(1536),
  is_active        BOOLEAN DEFAULT true,
  posted_at        TIMESTAMPTZ DEFAULT NOW(),
  expires_at       TIMESTAMPTZ,
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(external_id, source)
);

CREATE INDEX IF NOT EXISTS idx_jobs_skills    ON jobs USING GIN(skills_required);
CREATE INDEX IF NOT EXISTS idx_jobs_location  ON jobs(location);
CREATE INDEX IF NOT EXISTS idx_jobs_posted    ON jobs(posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_active    ON jobs(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_jobs_source    ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_jobs_embedding
  ON jobs USING ivfflat (embedding_vector vector_cosine_ops)
  WITH (lists = 100);

-- ─── SWIPES ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS swipes (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
  job_id      UUID REFERENCES jobs(id) ON DELETE CASCADE,
  direction   VARCHAR(10) NOT NULL CHECK (direction IN ('right','left','up')),
  match_score INTEGER CHECK (match_score BETWEEN 0 AND 100),
  swiped_at   TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_swipes_user    ON swipes(user_id);
CREATE INDEX IF NOT EXISTS idx_swipes_user_ts ON swipes(user_id, swiped_at DESC);

-- ─── APPLICATIONS ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS applications (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID REFERENCES users(id) ON DELETE CASCADE,
  job_id         UUID REFERENCES jobs(id) ON DELETE CASCADE,
  swipe_id       UUID REFERENCES swipes(id),
  status         VARCHAR(50) DEFAULT 'applied' CHECK (status IN (
                   'applied','screening','interview_scheduled',
                   'interview_completed','offer_extended','offer_accepted',
                   'offer_rejected','rejected','withdrawn'
                 )),
  applied_at     TIMESTAMPTZ DEFAULT NOW(),
  auto_applied   BOOLEAN DEFAULT false,
  notes          TEXT,
  interview_date TIMESTAMPTZ,
  offer_amount   DECIMAL(6,2),
  updated_at     TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_applications_user   ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(user_id, status);

-- ─── JOB MATCH SCORES (precomputed cache) ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS job_match_scores (
  user_id       UUID REFERENCES users(id) ON DELETE CASCADE,
  job_id        UUID REFERENCES jobs(id) ON DELETE CASCADE,
  score         INTEGER CHECK (score BETWEEN 0 AND 100),
  score_details JSONB DEFAULT '{}',
  computed_at   TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (user_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_match_scores_user ON job_match_scores(user_id, score DESC);

-- ─── NOTIFICATIONS ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID REFERENCES users(id) ON DELETE CASCADE,
  type       VARCHAR(50) NOT NULL,
  title      VARCHAR(255) NOT NULL,
  body       TEXT,
  data       JSONB DEFAULT '{}',
  is_read    BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read, created_at DESC);

-- ─── OTP TOKENS ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS otp_tokens (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone      VARCHAR(15) NOT NULL,
  otp_hash   VARCHAR(255) NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  is_used    BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_otp_phone ON otp_tokens(phone, expires_at);

-- ─── REFRESH TOKENS ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS refresh_tokens (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID REFERENCES users(id) ON DELETE CASCADE,
  token_hash VARCHAR(255) UNIQUE NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  revoked    BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── RECRUITER JOBS ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS recruiter_profiles (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
  company_name VARCHAR(255) NOT NULL,
  company_logo TEXT,
  company_size VARCHAR(50),
  industry     VARCHAR(100),
  website      TEXT,
  verified     BOOLEAN DEFAULT false,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ─── SUBSCRIPTION TRACKING ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subscriptions (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID REFERENCES users(id) ON DELETE CASCADE,
  plan              VARCHAR(20) NOT NULL CHECK (plan IN ('pro','premium','recruiter')),
  razorpay_sub_id   VARCHAR(255) UNIQUE,
  status            VARCHAR(30) DEFAULT 'active',
  current_period_end TIMESTAMPTZ,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ─── TRIGGERS: auto-update updated_at ─────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_user_profiles_updated_at
  BEFORE UPDATE ON user_profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_applications_updated_at
  BEFORE UPDATE ON applications
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ─── GMAIL TOKENS ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gmail_tokens (
  user_id       UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  access_token  TEXT NOT NULL,
  refresh_token TEXT NOT NULL,
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ─── PUSH TOKENS ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS push_tokens (
  user_id    UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  token      TEXT NOT NULL,
  platform   VARCHAR(20) DEFAULT 'unknown',
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
