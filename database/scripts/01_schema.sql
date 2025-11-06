-- ===========================================================
-- RIGHTSTAFF: OLTP schema for Candidate / Jobs / Applications
-- PostgreSQL (RDS-ready)
-- ===========================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

-- 00) Idempotent: create role if missing 
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'right_staff') THEN
    CREATE ROLE right_staff LOGIN;
  END IF;
END$$;

-- 01)c  Create schema; owner = current_user first
CREATE SCHEMA IF NOT EXISTS rightstaff;

-- If role exists, set schema owner to right_staff
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'right_staff') THEN
    ALTER SCHEMA rightstaff OWNER TO right_staff;
  END IF;
END$$;

-- 03) Use the schema
SET search_path = rightstaff, public;

-- Grant privileges to right_staff only if it exists
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'right_staff') THEN
    GRANT USAGE ON SCHEMA rightstaff TO right_staff;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA rightstaff TO right_staff;
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA rightstaff TO right_staff;

    ALTER DEFAULT PRIVILEGES IN SCHEMA rightstaff
      GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO right_staff;
    ALTER DEFAULT PRIVILEGES IN SCHEMA rightstaff
      GRANT USAGE, SELECT ON SEQUENCES TO right_staff;
  END IF;
END$$;

-- 3) Enumerations
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'job_status_enum') THEN
    CREATE TYPE job_status_enum AS ENUM ('draft','open','on_hold','closed','filled');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'application_status_enum') THEN
    CREATE TYPE application_status_enum AS ENUM ('sourced','applied','screen','shortlist','interview','offer','hired','rejected','withdrawn');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'employment_type_enum') THEN
    CREATE TYPE employment_type_enum AS ENUM ('full_time','contract','internship','freelance');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'work_arrangement_enum') THEN
    CREATE TYPE work_arrangement_enum AS ENUM ('Remote','Hybrid','On-site');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'company_size_enum') THEN
    CREATE TYPE company_size_enum AS ENUM ('Startup','SME','Enterprise');
  END IF;
END$$;

-- ===========================================================
-- 4) Core person tables
-- ===========================================================

CREATE TABLE IF NOT EXISTS candidate (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name           text NOT NULL,
  years_experience    numeric(5,2),              -- supports 3.50 etc.
  professional_summary text,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS candidate_contact (
  candidate_id        uuid PRIMARY KEY REFERENCES candidate(id) ON DELETE CASCADE,
  email               citext,                    -- case-insensitive
  phone               text,
  address_line1       text,
  address_line2       text,
  city                text,
  region              text,
  postal_code         text,
  country             text
);

CREATE TABLE IF NOT EXISTS candidate_preference (
  candidate_id        uuid PRIMARY KEY REFERENCES candidate(id) ON DELETE CASCADE,
  work_authorization  text,
  work_arrangement    work_arrangement_enum,
  willing_to_relocate text,                      -- "Yes" / "No" / "Specific: ..."
  desired_salary_min  numeric(12,2),
  desired_salary_max  numeric(12,2),
  salary_currency     char(3) DEFAULT 'USD',
  salary_period       text     DEFAULT 'year',   -- 'year','hour', etc.
  availability_start  text,
  open_to_remote      boolean
);

-- Sensitive data
CREATE TABLE IF NOT EXISTS candidate_demographics (
  candidate_id        uuid PRIMARY KEY REFERENCES candidate(id) ON DELETE CASCADE,
  disability          text,
  ethnicity           text,
  veteran_status      text,
  collected_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS candidate_stats (
  candidate_id              uuid PRIMARY KEY REFERENCES candidate(id) ON DELETE CASCADE,
  profile_completion_score  int,
  last_profile_update_at    timestamptz
);

-- ===========================================================
-- 5) Resume
-- ===========================================================

CREATE TABLE IF NOT EXISTS candidate_resume (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id     uuid NOT NULL REFERENCES candidate(id) ON DELETE CASCADE,
  s3_url           text NOT NULL,
  file_type        text,
  is_latest        boolean NOT NULL DEFAULT true,
  uploaded_at      timestamptz NOT NULL DEFAULT now()
);

-- Partial unique: only one latest resume per candidate
CREATE UNIQUE INDEX IF NOT EXISTS ux_resume_latest
  ON candidate_resume (candidate_id)
  WHERE is_latest = true;

-- Helpful time-sort index
CREATE INDEX IF NOT EXISTS ix_resume_candidate_time
  ON candidate_resume (candidate_id, uploaded_at DESC);

-- ===========================================================
-- 6) Experience / Education / Certification / Reference
-- ===========================================================

CREATE TABLE IF NOT EXISTS candidate_experience (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id     uuid NOT NULL REFERENCES candidate(id) ON DELETE CASCADE,
  title            text,
  company          text,
  employment_type  employment_type_enum,
  start_date       date,
  end_date         date,
  description      text,
  industry         text
);

CREATE TABLE IF NOT EXISTS candidate_education (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id     uuid NOT NULL REFERENCES candidate(id) ON DELETE CASCADE,
  degree           text,
  institution      text,
  field_of_study   text,
  graduation_year  int,
  gpa              text,            
  honors           text
);

CREATE TABLE IF NOT EXISTS candidate_certification (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id     uuid NOT NULL REFERENCES candidate(id) ON DELETE CASCADE,
  name             text NOT NULL,
  issuer           text,
  issued_on        date,
  expires_on       date,
  credential_url   text,
  credential_id    text
);

CREATE TABLE IF NOT EXISTS candidate_reference (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id     uuid NOT NULL REFERENCES candidate(id) ON DELETE CASCADE,
  name             text,
  relationship     text,
  contact          text
);

-- ===========================================================
-- 7) Skills / Interests
-- ===========================================================

CREATE TABLE IF NOT EXISTS skill (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name              text NOT NULL UNIQUE,
  parent_skill_id   uuid REFERENCES skill(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS skill_synonym (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  skill_id    uuid NOT NULL REFERENCES skill(id) ON DELETE CASCADE,
  synonym     text NOT NULL,
  UNIQUE (skill_id, synonym)
);

CREATE TABLE IF NOT EXISTS candidate_skill (
  candidate_id  uuid NOT NULL REFERENCES candidate(id) ON DELETE CASCADE,
  skill_id      uuid NOT NULL REFERENCES skill(id) ON DELETE CASCADE,
  level         text,
  years         numeric(5,2),
  PRIMARY KEY (candidate_id, skill_id)
);

-- For reverse lookups by skill
CREATE INDEX IF NOT EXISTS ix_cskill_skill ON candidate_skill (skill_id);

CREATE TABLE IF NOT EXISTS interest (
  id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name   text NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS candidate_interest (
  candidate_id  uuid NOT NULL REFERENCES candidate(id) ON DELETE CASCADE,
  interest_id   uuid NOT NULL REFERENCES interest(id) ON DELETE CASCADE,
  PRIMARY KEY (candidate_id, interest_id)
);

-- ===========================================================
-- 8) Preference “lists” (normalized)
-- ===========================================================

CREATE TABLE IF NOT EXISTS candidate_desired_title (
  candidate_id  uuid NOT NULL REFERENCES candidate(id) ON DELETE CASCADE,
  title         text NOT NULL,
  PRIMARY KEY (candidate_id, title)
);

CREATE TABLE IF NOT EXISTS candidate_preferred_industry (
  candidate_id  uuid NOT NULL REFERENCES candidate(id) ON DELETE CASCADE,
  industry      text NOT NULL,
  PRIMARY KEY (candidate_id, industry)
);

CREATE TABLE IF NOT EXISTS candidate_preferred_company_size (
  candidate_id  uuid NOT NULL REFERENCES candidate(id) ON DELETE CASCADE,
  size          company_size_enum NOT NULL,
  PRIMARY KEY (candidate_id, size)
);

-- ===========================================================
-- 9) Jobs & Applications
-- ===========================================================

CREATE TABLE IF NOT EXISTS job (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title       text NOT NULL,
  department  text,
  location    text,
  status      job_status_enum NOT NULL DEFAULT 'draft',
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS application (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),   -- Applied Jobs ID
  candidate_id  uuid NOT NULL REFERENCES candidate(id) ON DELETE CASCADE,
  job_id        uuid NOT NULL REFERENCES job(id)       ON DELETE CASCADE,
  status        application_status_enum NOT NULL DEFAULT 'applied',
  applied_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (candidate_id, job_id)                                -- one app per candidate per job
);

-- Helpful indexes for dashboard queries
CREATE INDEX IF NOT EXISTS ix_app_job_status ON application (job_id, status);
CREATE INDEX IF NOT EXISTS ix_app_candidate   ON application (candidate_id);

-- ===========================================================
-- 10) Basic row-change timestamp trigger (optional)
--     Keeps candidate.updated_at current on UPDATE
-- ===========================================================
CREATE OR REPLACE FUNCTION touch_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_candidate_touch ON candidate;
CREATE TRIGGER trg_candidate_touch
BEFORE UPDATE ON candidate
FOR EACH ROW
EXECUTE FUNCTION touch_updated_at();

-- ===========================================================
-- 11) Grants (optional — adjust to your security model)
-- ===========================================================
GRANT USAGE ON SCHEMA rightstaff TO RIGHT_STAFF;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA rightstaff TO RIGHT_STAFF;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA rightstaff TO RIGHT_STAFF;

-- Make future tables auto-grant to role
ALTER DEFAULT PRIVILEGES IN SCHEMA rightstaff
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO RIGHT_STAFF;
ALTER DEFAULT PRIVILEGES IN SCHEMA rightstaff
GRANT USAGE, SELECT ON SEQUENCES TO RIGHT_STAFF;
