-- ==========================================
-- RIGHTSTAFF seed + smoke-test (PostgreSQL)
-- ==========================================
SET search_path = rightstaff, public;

-- Wrap everything in one transaction for convenience
BEGIN;

DO $$
DECLARE
  v_cand_id           uuid;
  v_job_id            uuid;
  v_skill_python      uuid;
  v_skill_nlp         uuid;
  v_skill_postgres    uuid;
  v_interest_climate  uuid;
  v_interest_fintech  uuid;
  v_old_resume_id     uuid;
  v_new_resume_id     uuid;
BEGIN
  --------------------------------------------------------------------
  -- Seed: Skills (idempotent)
  --------------------------------------------------------------------
  INSERT INTO skill (id, name) VALUES
    (gen_random_uuid(), 'Python'),
    (gen_random_uuid(), 'NLP'),
    (gen_random_uuid(), 'Postgres')
  ON CONFLICT (name) DO NOTHING;

  SELECT id INTO v_skill_python   FROM skill WHERE name='Python';
  SELECT id INTO v_skill_nlp      FROM skill WHERE name='NLP';
  SELECT id INTO v_skill_postgres FROM skill WHERE name='Postgres';

  -- Skill synonyms
  INSERT INTO skill_synonym (id, skill_id, synonym)
  VALUES
    (gen_random_uuid(), v_skill_python,  'Py'),
    (gen_random_uuid(), v_skill_postgres,'PostgreSQL')
  ON CONFLICT (skill_id, synonym) DO NOTHING;

  --------------------------------------------------------------------
  -- Seed: Interests (idempotent)
  --------------------------------------------------------------------
  INSERT INTO interest (id, name) VALUES
    (gen_random_uuid(), 'ClimateTech'),
    (gen_random_uuid(), 'FinTech')
  ON CONFLICT (name) DO NOTHING;

  SELECT id INTO v_interest_climate FROM interest WHERE name='ClimateTech';
  SELECT id INTO v_interest_fintech FROM interest WHERE name='FinTech';

  --------------------------------------------------------------------
  -- Seed: One candidate (Prathyusha Elipay)
  --------------------------------------------------------------------
  INSERT INTO candidate (id, full_name, years_experience, professional_summary)
  VALUES (gen_random_uuid(), 'Prathyusha Elipay', 3.50,
          'Data/BI professional: SQL, Python, Postgres, cloud dashboards.')
  RETURNING id INTO v_cand_id;

  INSERT INTO candidate_contact (candidate_id, email, phone, city, region, country)
  VALUES (v_cand_id, 'prathyusha@example.com', '+1-555-0100', 'Columbus', 'OH', 'US');

  INSERT INTO candidate_preference (
      candidate_id, work_authorization, work_arrangement, willing_to_relocate,
      desired_salary_min, desired_salary_max, salary_currency, salary_period,
      availability_start, open_to_remote
  ) VALUES (
      v_cand_id, 'F1 OPT', 'Hybrid', 'Specific: Bay Area',
      95000, 115000, 'USD', 'year', '2 weeks', true
  );

  INSERT INTO candidate_stats (candidate_id, profile_completion_score, last_profile_update_at)
  VALUES (v_cand_id, 85, now());

  INSERT INTO candidate_demographics (candidate_id, ethnicity, veteran_status)
  VALUES (v_cand_id, 'Asian', 'Non-veteran');

  -- Experience
  INSERT INTO candidate_experience (
      id, candidate_id, title, company, employment_type,
      start_date, end_date, description, industry
  ) VALUES (
      gen_random_uuid(), v_cand_id, 'Application Development Analyst', 'Accenture', 'full_time',
      DATE '2019-05-01', DATE '2022-12-31',
      'Built ETL pipelines, QlikView dashboards, fixed data integrity issues.',
      'Consulting'
  );

  -- Education
  INSERT INTO candidate_education (
      id, candidate_id, degree, institution, field_of_study, graduation_year, gpa
  ) VALUES (
      gen_random_uuid(), v_cand_id, 'MS', 'George Mason University',
      'Data Analytics Engineering', 2024, '3.97'
  );

  -- Certifications
  INSERT INTO candidate_certification (id, candidate_id, name, issuer, issued_on)
  VALUES (gen_random_uuid(), v_cand_id, 'AWS Cloud Practitioner', 'Amazon', DATE '2024-03-01')
  ON CONFLICT DO NOTHING;

  -- References
  INSERT INTO candidate_reference (id, candidate_id, name, relationship, contact)
  VALUES (gen_random_uuid(), v_cand_id, 'Jerin G.', 'Colleague', 'jerin@example.com')
  ON CONFLICT DO NOTHING;

  -- Skills (M:N)
  INSERT INTO candidate_skill (candidate_id, skill_id, level, years)
  VALUES
    (v_cand_id, v_skill_python,   'advanced', 3.5),
    (v_cand_id, v_skill_postgres, 'advanced', 3.0)
  ON CONFLICT DO NOTHING;

  -- Interests (M:N)
  INSERT INTO candidate_interest (candidate_id, interest_id)
  VALUES (v_cand_id, v_interest_climate)
  ON CONFLICT DO NOTHING;

  -- Preference “lists”
  INSERT INTO candidate_desired_title (candidate_id, title)
  VALUES (v_cand_id, 'Data Engineer')
  ON CONFLICT DO NOTHING;

  INSERT INTO candidate_preferred_industry (candidate_id, industry)
  VALUES (v_cand_id, 'Climate Analytics')
  ON CONFLICT DO NOTHING;

  INSERT INTO candidate_preferred_company_size (candidate_id, size)
  VALUES (v_cand_id, 'Startup')
  ON CONFLICT DO NOTHING;

  -- Résumé: one latest + one historical
  INSERT INTO candidate_resume (id, candidate_id, s3_url, file_type, is_latest)
  VALUES (gen_random_uuid(), v_cand_id, 's3://rightstaff/resumes/pratz_v1.pdf', 'pdf', true)
  RETURNING id INTO v_old_resume_id;

  INSERT INTO candidate_resume (id, candidate_id, s3_url, file_type, is_latest)
  VALUES (gen_random_uuid(), v_cand_id, 's3://rightstaff/resumes/pratz_v0.pdf', 'pdf', false)
  RETURNING id INTO v_new_resume_id;

  RAISE NOTICE 'Seeded candidate %, skills %, %, interests %, %',
               v_cand_id, v_skill_python, v_skill_postgres,
               v_interest_climate, v_interest_fintech;

  --------------------------------------------------------------------
  -- Seed: One job and application
  --------------------------------------------------------------------
  INSERT INTO job (id, title, department, location, status)
  VALUES (gen_random_uuid(), 'Data Engineer', 'Engineering', 'Remote', 'open')
  RETURNING id INTO v_job_id;

  INSERT INTO application (id, candidate_id, job_id, status)
  VALUES (gen_random_uuid(), v_cand_id, v_job_id, 'applied')
  ON CONFLICT DO NOTHING;

  RAISE NOTICE 'Seeded job % and application for candidate %', v_job_id, v_cand_id;

  --------------------------------------------------------------------
  -- Smoke tests (constraints & behaviors)
  --------------------------------------------------------------------

  -- A) Composite unique on application (candidate_id, job_id)
  BEGIN
    INSERT INTO application (id, candidate_id, job_id, status)
    VALUES (gen_random_uuid(), v_cand_id, v_job_id, 'applied');
  EXCEPTION WHEN unique_violation THEN
    RAISE NOTICE 'OK: composite unique on application blocked duplicate apply.';
  END;

  -- B) Partial unique: only one latest resume per candidate
  BEGIN
    INSERT INTO candidate_resume (id, candidate_id, s3_url, file_type, is_latest)
    VALUES (gen_random_uuid(), v_cand_id, 's3://rightstaff/resumes/pratz_v2.pdf', 'pdf', true);
    RAISE EXCEPTION 'Partial unique on resumes did NOT fire (should not reach here)';
  EXCEPTION WHEN unique_violation THEN
    RAISE NOTICE 'OK: partial unique on candidate_resume (is_latest) enforced.';
  END;

  -- C) Update latest resume correctly: flip old latest to false, then insert a new latest
  UPDATE candidate_resume
  SET is_latest = false
  WHERE candidate_id = v_cand_id AND is_latest = true;

  INSERT INTO candidate_resume (id, candidate_id, s3_url, file_type, is_latest)
  VALUES (gen_random_uuid(), v_cand_id, 's3://rightstaff/resumes/pratz_v2.pdf', 'pdf', true)
  RETURNING id INTO v_new_resume_id;

  RAISE NOTICE 'Rotated latest resume successfully to id %', v_new_resume_id;

  -- D) Read model checks (notices show row counts)
  PERFORM 1;
  RAISE NOTICE 'Applicants for job %: %',
    v_job_id,
    (SELECT count(*) FROM application WHERE job_id = v_job_id);

  RAISE NOTICE 'Candidate skills: %',
    (SELECT string_agg(s.name, ', ' ORDER BY s.name)
       FROM candidate_skill cs
       JOIN skill s ON s.id = cs.skill_id
      WHERE cs.candidate_id = v_cand_id);

  RAISE NOTICE 'Latest resume URI: %',
    (SELECT r.s3_url FROM candidate_resume r
      WHERE r.candidate_id = v_cand_id AND r.is_latest = true);

  -- E) Cascade test: delete a TEMP candidate and verify all children go
  --    (We create a throwaway candidate to prove ON DELETE CASCADE, leaving the seeded one intact)
  DECLARE
    v_tmp uuid;
  BEGIN
    INSERT INTO candidate (id, full_name) VALUES (gen_random_uuid(), 'Temp Candidate')
    RETURNING id INTO v_tmp;

    INSERT INTO candidate_resume (candidate_id, s3_url, file_type, is_latest)
    VALUES (v_tmp, 's3://rightstaff/resumes/tmp.pdf', 'pdf', true);

    INSERT INTO candidate_skill (candidate_id, skill_id) VALUES (v_tmp, v_skill_python);

    DELETE FROM candidate WHERE id = v_tmp;

    IF (SELECT count(*) FROM candidate_resume WHERE candidate_id = v_tmp) = 0
       AND (SELECT count(*) FROM candidate_skill WHERE candidate_id = v_tmp) = 0 THEN
      RAISE NOTICE 'OK: ON DELETE CASCADE removed dependent rows for temp candidate.';
    ELSE
      RAISE EXCEPTION 'Cascade delete failed for temp candidate.';
    END IF;
  END;

END
$$ LANGUAGE plpgsql;

-- Handy result queries 
-- 1) Candidate + latest resume + skills
SELECT c.full_name,
       r.s3_url AS latest_resume,
       array_agg(s.name ORDER BY s.name) AS skills
FROM candidate c
LEFT JOIN candidate_resume r
  ON r.candidate_id = c.id AND r.is_latest = true
LEFT JOIN candidate_skill cs ON cs.candidate_id = c.id
LEFT JOIN skill s ON s.id = cs.skill_id
GROUP BY c.id, r.s3_url;

-- 2) Applicants per job
SELECT j.title, j.status, COUNT(a.id) AS applicants
FROM job j
LEFT JOIN application a ON a.job_id = j.id
GROUP BY j.id
ORDER BY applicants DESC;

COMMIT;
