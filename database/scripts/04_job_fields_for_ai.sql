-- 04_job_fields_for_ai.sql
-- Add AI ranking fields to job table
--
-- Why these fields?
-- - description: Job description text for semantic search
-- - required_skills_json: All skills mentioned in JD (for scoring)
-- - must_have_skills_json: Non-negotiable skills (for SQL gating)
-- - min/max_years_experience: Experience filter
-- - work_arrangement: Remote/hybrid/onsite preference
-- - employment_type: Full-time/part-time/contract
-- - updated_at: Track when job was last modified

SET search_path = rightstaff, public;

-- Add description and skills fields for AI ranking
ALTER TABLE job ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE job ADD COLUMN IF NOT EXISTS required_skills_json JSONB;
ALTER TABLE job ADD COLUMN IF NOT EXISTS must_have_skills_json JSONB;
ALTER TABLE job ADD COLUMN IF NOT EXISTS min_years_experience NUMERIC(5,2);
ALTER TABLE job ADD COLUMN IF NOT EXISTS max_years_experience NUMERIC(5,2);
ALTER TABLE job ADD COLUMN IF NOT EXISTS work_arrangement TEXT;
ALTER TABLE job ADD COLUMN IF NOT EXISTS employment_type TEXT;
ALTER TABLE job ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- Indexes for performance
CREATE INDEX IF NOT EXISTS ix_job_status ON job(status);
CREATE INDEX IF NOT EXISTS ix_job_created_at ON job(created_at DESC);

-- Trigger to auto-update updated_at on job modifications
DROP TRIGGER IF EXISTS trg_job_touch ON job;
CREATE TRIGGER trg_job_touch
BEFORE UPDATE ON job
FOR EACH ROW
EXECUTE FUNCTION touch_updated_at();

-- Permissions (ensure right_staff role has access)
GRANT SELECT, INSERT, UPDATE, DELETE ON job TO right_staff;

-- Verification queries (commented out - uncomment for debugging)
-- \d rightstaff.job
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'rightstaff' AND table_name = 'job';

