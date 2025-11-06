DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname='rightstaff') THEN
    EXECUTE 'SET search_path = rightstaff, public';
  END IF;
END$$;

DROP TABLE IF EXISTS rightstaff.application                           CASCADE;
DROP TABLE IF EXISTS rightstaff.job                                   CASCADE;

DROP TABLE IF EXISTS rightstaff.candidate_preferred_company_size      CASCADE;
DROP TABLE IF EXISTS rightstaff.candidate_preferred_industry          CASCADE;
DROP TABLE IF EXISTS rightstaff.candidate_desired_title               CASCADE;

DROP TABLE IF EXISTS rightstaff.candidate_interest                    CASCADE;
DROP TABLE IF EXISTS rightstaff.interest                              CASCADE;

DROP TABLE IF EXISTS rightstaff.candidate_skill                       CASCADE;
DROP TABLE IF EXISTS rightstaff.skill_synonym                         CASCADE;
DROP TABLE IF EXISTS rightstaff.skill                                 CASCADE;

DROP TABLE IF EXISTS rightstaff.candidate_reference                   CASCADE;
DROP TABLE IF EXISTS rightstaff.candidate_certification               CASCADE;
DROP TABLE IF EXISTS rightstaff.candidate_education                   CASCADE;
DROP TABLE IF EXISTS rightstaff.candidate_experience                  CASCADE;
DROP TABLE IF EXISTS rightstaff.candidate_resume                      CASCADE;

DROP TABLE IF EXISTS rightstaff.candidate_stats                       CASCADE;
DROP TABLE IF EXISTS rightstaff.candidate_demographics                CASCADE;
DROP TABLE IF EXISTS rightstaff.candidate_preference                  CASCADE;
DROP TABLE IF EXISTS rightstaff.candidate_contact                     CASCADE;
DROP TABLE IF EXISTS rightstaff.candidate                             CASCADE;

DROP TRIGGER IF EXISTS trg_candidate_touch ON rightstaff.candidate;
DROP FUNCTION IF EXISTS rightstaff.touch_updated_at();

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_type WHERE typname='job_status_enum') THEN
    DROP TYPE rightstaff.job_status_enum;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_type WHERE typname='application_status_enum') THEN
    DROP TYPE rightstaff.application_status_enum;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_type WHERE typname='employment_type_enum') THEN
    DROP TYPE rightstaff.employment_type_enum;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_type WHERE typname='work_arrangement_enum') THEN
    DROP TYPE rightstaff.work_arrangement_enum;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_type WHERE typname='company_size_enum') THEN
    DROP TYPE rightstaff.company_size_enum;
  END IF;
END$$;

DROP SCHEMA IF EXISTS rightstaff CASCADE;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='RIGHT_STAFF') THEN
    DROP ROLE RIGHT_STAFF;
  END IF;
END$$;
