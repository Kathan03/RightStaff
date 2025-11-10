-- ==========================================
-- RIGHTSTAFF: Dummy Data - 10+ Candidates
-- ==========================================
SET search_path = rightstaff, public;

BEGIN;

DO $$
DECLARE
  -- Candidate IDs
  v_cand1_id uuid;
  v_cand2_id uuid;
  v_cand3_id uuid;
  v_cand4_id uuid;
  v_cand5_id uuid;
  v_cand6_id uuid;
  v_cand7_id uuid;
  v_cand8_id uuid;
  v_cand9_id uuid;
  v_cand10_id uuid;
  
  -- Job IDs
  v_job1_id uuid;
  v_job2_id uuid;
  v_job3_id uuid;
  v_job4_id uuid;
  v_job5_id uuid;
  
  -- Skill IDs
  v_skill_python uuid;
  v_skill_java uuid;
  v_skill_javascript uuid;
  v_skill_react uuid;
  v_skill_nodejs uuid;
  v_skill_aws uuid;
  v_skill_docker uuid;
  v_skill_kubernetes uuid;
  v_skill_sql uuid;
  v_skill_mongodb uuid;
  v_skill_machine_learning uuid;
  v_skill_data_science uuid;
  v_skill_product_management uuid;
  v_skill_ui_ux uuid;
  v_skill_agile uuid;
  
  -- Interest IDs
  v_interest_ai uuid;
  v_interest_blockchain uuid;
  v_interest_gaming uuid;
  v_interest_healthtech uuid;
  v_interest_edtech uuid;
  v_interest_saas uuid;

BEGIN
  RAISE NOTICE '========================================';
  RAISE NOTICE 'Starting Dummy Data Insertion...';
  RAISE NOTICE '========================================';

  --------------------------------------------------------------------
  -- 1) Insert Skills (with idempotent conflict handling)
  --------------------------------------------------------------------
  INSERT INTO skill (id, name) VALUES
    (gen_random_uuid(), 'Python'),
    (gen_random_uuid(), 'Java'),
    (gen_random_uuid(), 'JavaScript'),
    (gen_random_uuid(), 'React'),
    (gen_random_uuid(), 'Node.js'),
    (gen_random_uuid(), 'AWS'),
    (gen_random_uuid(), 'Docker'),
    (gen_random_uuid(), 'Kubernetes'),
    (gen_random_uuid(), 'SQL'),
    (gen_random_uuid(), 'MongoDB'),
    (gen_random_uuid(), 'Machine Learning'),
    (gen_random_uuid(), 'Data Science'),
    (gen_random_uuid(), 'Product Management'),
    (gen_random_uuid(), 'UI/UX Design'),
    (gen_random_uuid(), 'Agile')
  ON CONFLICT (name) DO NOTHING;

  -- Fetch skill IDs
  SELECT id INTO v_skill_python FROM skill WHERE name='Python';
  SELECT id INTO v_skill_java FROM skill WHERE name='Java';
  SELECT id INTO v_skill_javascript FROM skill WHERE name='JavaScript';
  SELECT id INTO v_skill_react FROM skill WHERE name='React';
  SELECT id INTO v_skill_nodejs FROM skill WHERE name='Node.js';
  SELECT id INTO v_skill_aws FROM skill WHERE name='AWS';
  SELECT id INTO v_skill_docker FROM skill WHERE name='Docker';
  SELECT id INTO v_skill_kubernetes FROM skill WHERE name='Kubernetes';
  SELECT id INTO v_skill_sql FROM skill WHERE name='SQL';
  SELECT id INTO v_skill_mongodb FROM skill WHERE name='MongoDB';
  SELECT id INTO v_skill_machine_learning FROM skill WHERE name='Machine Learning';
  SELECT id INTO v_skill_data_science FROM skill WHERE name='Data Science';
  SELECT id INTO v_skill_product_management FROM skill WHERE name='Product Management';
  SELECT id INTO v_skill_ui_ux FROM skill WHERE name='UI/UX Design';
  SELECT id INTO v_skill_agile FROM skill WHERE name='Agile';

  RAISE NOTICE 'Skills inserted successfully';

  --------------------------------------------------------------------
  -- 2) Insert Interests
  --------------------------------------------------------------------
  INSERT INTO interest (id, name) VALUES
    (gen_random_uuid(), 'Artificial Intelligence'),
    (gen_random_uuid(), 'Blockchain'),
    (gen_random_uuid(), 'Gaming'),
    (gen_random_uuid(), 'HealthTech'),
    (gen_random_uuid(), 'EdTech'),
    (gen_random_uuid(), 'SaaS')
  ON CONFLICT (name) DO NOTHING;

  -- Fetch interest IDs
  SELECT id INTO v_interest_ai FROM interest WHERE name='Artificial Intelligence';
  SELECT id INTO v_interest_blockchain FROM interest WHERE name='Blockchain';
  SELECT id INTO v_interest_gaming FROM interest WHERE name='Gaming';
  SELECT id INTO v_interest_healthtech FROM interest WHERE name='HealthTech';
  SELECT id INTO v_interest_edtech FROM interest WHERE name='EdTech';
  SELECT id INTO v_interest_saas FROM interest WHERE name='SaaS';

  RAISE NOTICE 'Interests inserted successfully';

  --------------------------------------------------------------------
  -- 3) CANDIDATE 1: Sarah Johnson - Full Stack Developer
  --------------------------------------------------------------------
  INSERT INTO candidate (id, full_name, years_experience, professional_summary)
  VALUES (gen_random_uuid(), 'Sarah Johnson', 5.00,
          'Senior Full Stack Developer with expertise in React, Node.js, and cloud infrastructure.')
  RETURNING id INTO v_cand1_id;

  INSERT INTO candidate_contact (candidate_id, email, phone, city, region, country)
  VALUES (v_cand1_id, 'sarah.johnson@example.com', '+1-555-0201', 'San Francisco', 'CA', 'US');

  INSERT INTO candidate_preference (
      candidate_id, work_authorization, work_arrangement, willing_to_relocate,
      desired_salary_min, desired_salary_max, salary_currency, salary_period,
      availability_start, open_to_remote
  ) VALUES (
      v_cand1_id, 'US Citizen', 'Remote', 'No',
      120000, 150000, 'USD', 'year', 'Immediate', true
  );

  INSERT INTO candidate_experience (
      id, candidate_id, title, company, employment_type,
      start_date, end_date, description, industry
  ) VALUES (
      gen_random_uuid(), v_cand1_id, 'Senior Full Stack Developer', 'TechCorp Inc.', 'full_time',
      DATE '2020-01-01', NULL,
      'Leading development of scalable web applications using React, Node.js, and AWS.',
      'Technology'
  );

  INSERT INTO candidate_education (
      id, candidate_id, degree, institution, field_of_study, graduation_year, gpa
  ) VALUES (
      gen_random_uuid(), v_cand1_id, 'BS', 'Stanford University',
      'Computer Science', 2019, '3.85'
  );

  INSERT INTO candidate_skill (candidate_id, skill_id, level, years)
  VALUES
    (v_cand1_id, v_skill_javascript, 'expert', 5.0),
    (v_cand1_id, v_skill_react, 'expert', 4.5),
    (v_cand1_id, v_skill_nodejs, 'advanced', 4.0),
    (v_cand1_id, v_skill_aws, 'advanced', 3.0);

  INSERT INTO candidate_resume (id, candidate_id, s3_url, file_type, is_latest)
  VALUES (gen_random_uuid(), v_cand1_id, 's3://rightstaff/resumes/sarah_johnson.pdf', 'pdf', true);

  RAISE NOTICE 'Candidate 1 (Sarah Johnson) inserted: %', v_cand1_id;

  --------------------------------------------------------------------
  -- 4) CANDIDATE 2: Michael Chen - Data Scientist
  --------------------------------------------------------------------
  INSERT INTO candidate (id, full_name, years_experience, professional_summary)
  VALUES (gen_random_uuid(), 'Michael Chen', 7.50,
          'Experienced Data Scientist specializing in machine learning and predictive analytics.')
  RETURNING id INTO v_cand2_id;

  INSERT INTO candidate_contact (candidate_id, email, phone, city, region, country)
  VALUES (v_cand2_id, 'michael.chen@example.com', '+1-555-0202', 'New York', 'NY', 'US');

  INSERT INTO candidate_preference (
      candidate_id, work_authorization, work_arrangement, willing_to_relocate,
      desired_salary_min, desired_salary_max, salary_currency, salary_period,
      availability_start, open_to_remote
  ) VALUES (
      v_cand2_id, 'H1B', 'Hybrid', 'Yes',
      130000, 160000, 'USD', 'year', '1 month', true
  );

  INSERT INTO candidate_experience (
      id, candidate_id, title, company, employment_type,
      start_date, end_date, description, industry
  ) VALUES (
      gen_random_uuid(), v_cand2_id, 'Senior Data Scientist', 'DataCorp', 'full_time',
      DATE '2018-06-01', NULL,
      'Developed ML models for customer segmentation and churn prediction.',
      'Finance'
  );

  INSERT INTO candidate_education (
      id, candidate_id, degree, institution, field_of_study, graduation_year, gpa
  ) VALUES (
      gen_random_uuid(), v_cand2_id, 'PhD', 'MIT',
      'Machine Learning', 2017, '3.92'
  );

  INSERT INTO candidate_skill (candidate_id, skill_id, level, years)
  VALUES
    (v_cand2_id, v_skill_python, 'expert', 7.5),
    (v_cand2_id, v_skill_machine_learning, 'expert', 6.0),
    (v_cand2_id, v_skill_data_science, 'expert', 7.0),
    (v_cand2_id, v_skill_sql, 'advanced', 5.0);

  INSERT INTO candidate_interest (candidate_id, interest_id)
  VALUES (v_cand2_id, v_interest_ai);

  INSERT INTO candidate_resume (id, candidate_id, s3_url, file_type, is_latest)
  VALUES (gen_random_uuid(), v_cand2_id, 's3://rightstaff/resumes/michael_chen.pdf', 'pdf', true);

  RAISE NOTICE 'Candidate 2 (Michael Chen) inserted: %', v_cand2_id;

  --------------------------------------------------------------------
  -- 5) CANDIDATE 3: Emily Rodriguez - DevOps Engineer
  --------------------------------------------------------------------
  INSERT INTO candidate (id, full_name, years_experience, professional_summary)
  VALUES (gen_random_uuid(), 'Emily Rodriguez', 6.00,
          'DevOps Engineer with strong expertise in Kubernetes, Docker, and CI/CD pipelines.')
  RETURNING id INTO v_cand3_id;

  INSERT INTO candidate_contact (candidate_id, email, phone, city, region, country)
  VALUES (v_cand3_id, 'emily.rodriguez@example.com', '+1-555-0203', 'Austin', 'TX', 'US');

  INSERT INTO candidate_preference (
      candidate_id, work_authorization, work_arrangement, willing_to_relocate,
      desired_salary_min, desired_salary_max, salary_currency, salary_period,
      availability_start, open_to_remote
  ) VALUES (
      v_cand3_id, 'US Citizen', 'Remote', 'No',
      110000, 140000, 'USD', 'year', '2 weeks', true
  );

  INSERT INTO candidate_experience (
      id, candidate_id, title, company, employment_type,
      start_date, end_date, description, industry
  ) VALUES (
      gen_random_uuid(), v_cand3_id, 'DevOps Engineer', 'CloudFirst Inc.', 'full_time',
      DATE '2019-03-01', NULL,
      'Managing Kubernetes clusters and implementing automated deployment pipelines.',
      'Technology'
  );

  INSERT INTO candidate_education (
      id, candidate_id, degree, institution, field_of_study, graduation_year, gpa
  ) VALUES (
      gen_random_uuid(), v_cand3_id, 'MS', 'University of Texas',
      'Computer Engineering', 2018, '3.78'
  );

  INSERT INTO candidate_skill (candidate_id, skill_id, level, years)
  VALUES
    (v_cand3_id, v_skill_kubernetes, 'expert', 4.5),
    (v_cand3_id, v_skill_docker, 'expert', 6.0),
    (v_cand3_id, v_skill_aws, 'advanced', 5.0),
    (v_cand3_id, v_skill_python, 'advanced', 4.0);

  INSERT INTO candidate_resume (id, candidate_id, s3_url, file_type, is_latest)
  VALUES (gen_random_uuid(), v_cand3_id, 's3://rightstaff/resumes/emily_rodriguez.pdf', 'pdf', true);

  RAISE NOTICE 'Candidate 3 (Emily Rodriguez) inserted: %', v_cand3_id;

  --------------------------------------------------------------------
  -- 6) CANDIDATE 4: David Kim - Java Backend Developer
  --------------------------------------------------------------------
  INSERT INTO candidate (id, full_name, years_experience, professional_summary)
  VALUES (gen_random_uuid(), 'David Kim', 8.00,
          'Java Backend Developer with expertise in microservices and distributed systems.')
  RETURNING id INTO v_cand4_id;

  INSERT INTO candidate_contact (candidate_id, email, phone, city, region, country)
  VALUES (v_cand4_id, 'david.kim@example.com', '+1-555-0204', 'Seattle', 'WA', 'US');

  INSERT INTO candidate_preference (
      candidate_id, work_authorization, work_arrangement, willing_to_relocate,
      desired_salary_min, desired_salary_max, salary_currency, salary_period,
      availability_start, open_to_remote
  ) VALUES (
      v_cand4_id, 'US Citizen', 'Hybrid', 'Specific: West Coast',
      140000, 170000, 'USD', 'year', '1 month', true
  );

  INSERT INTO candidate_experience (
      id, candidate_id, title, company, employment_type,
      start_date, end_date, description, industry
  ) VALUES (
      gen_random_uuid(), v_cand4_id, 'Senior Backend Engineer', 'Amazon', 'full_time',
      DATE '2017-08-01', NULL,
      'Designing and implementing high-scale microservices using Java and Spring Boot.',
      'E-commerce'
  );

  INSERT INTO candidate_education (
      id, candidate_id, degree, institution, field_of_study, graduation_year, gpa
  ) VALUES (
      gen_random_uuid(), v_cand4_id, 'BS', 'University of Washington',
      'Software Engineering', 2016, '3.81'
  );

  INSERT INTO candidate_skill (candidate_id, skill_id, level, years)
  VALUES
    (v_cand4_id, v_skill_java, 'expert', 8.0),
    (v_cand4_id, v_skill_sql, 'advanced', 6.0),
    (v_cand4_id, v_skill_aws, 'advanced', 5.0),
    (v_cand4_id, v_skill_docker, 'advanced', 4.0);

  INSERT INTO candidate_interest (candidate_id, interest_id)
  VALUES (v_cand4_id, v_interest_saas);

  INSERT INTO candidate_resume (id, candidate_id, s3_url, file_type, is_latest)
  VALUES (gen_random_uuid(), v_cand4_id, 's3://rightstaff/resumes/david_kim.pdf', 'pdf', true);

  RAISE NOTICE 'Candidate 4 (David Kim) inserted: %', v_cand4_id;

  --------------------------------------------------------------------
  -- 7) CANDIDATE 5: Jessica Williams - Product Manager
  --------------------------------------------------------------------
  INSERT INTO candidate (id, full_name, years_experience, professional_summary)
  VALUES (gen_random_uuid(), 'Jessica Williams', 9.00,
          'Product Manager with a track record of launching successful B2B SaaS products.')
  RETURNING id INTO v_cand5_id;

  INSERT INTO candidate_contact (candidate_id, email, phone, city, region, country)
  VALUES (v_cand5_id, 'jessica.williams@example.com', '+1-555-0205', 'Boston', 'MA', 'US');

  INSERT INTO candidate_preference (
      candidate_id, work_authorization, work_arrangement, willing_to_relocate,
      desired_salary_min, desired_salary_max, salary_currency, salary_period,
      availability_start, open_to_remote
  ) VALUES (
      v_cand5_id, 'US Citizen', 'Hybrid', 'No',
      150000, 180000, 'USD', 'year', 'Immediate', true
  );

  INSERT INTO candidate_experience (
      id, candidate_id, title, company, employment_type,
      start_date, end_date, description, industry
  ) VALUES (
      gen_random_uuid(), v_cand5_id, 'Senior Product Manager', 'HubSpot', 'full_time',
      DATE '2016-01-01', NULL,
      'Led product development for marketing automation suite serving 50k+ customers.',
      'SaaS'
  );

  INSERT INTO candidate_education (
      id, candidate_id, degree, institution, field_of_study, graduation_year, gpa
  ) VALUES (
      gen_random_uuid(), v_cand5_id, 'MBA', 'Harvard Business School',
      'Business Administration', 2015, '3.88'
  );

  INSERT INTO candidate_skill (candidate_id, skill_id, level, years)
  VALUES
    (v_cand5_id, v_skill_product_management, 'expert', 9.0),
    (v_cand5_id, v_skill_agile, 'expert', 8.0);

  INSERT INTO candidate_interest (candidate_id, interest_id)
  VALUES 
    (v_cand5_id, v_interest_saas),
    (v_cand5_id, v_interest_edtech);

  INSERT INTO candidate_resume (id, candidate_id, s3_url, file_type, is_latest)
  VALUES (gen_random_uuid(), v_cand5_id, 's3://rightstaff/resumes/jessica_williams.pdf', 'pdf', true);

  RAISE NOTICE 'Candidate 5 (Jessica Williams) inserted: %', v_cand5_id;

  --------------------------------------------------------------------
  -- 8) CANDIDATE 6: Robert Martinez - UI/UX Designer
  --------------------------------------------------------------------
  INSERT INTO candidate (id, full_name, years_experience, professional_summary)
  VALUES (gen_random_uuid(), 'Robert Martinez', 4.50,
          'Creative UI/UX Designer passionate about creating intuitive user experiences.')
  RETURNING id INTO v_cand6_id;

  INSERT INTO candidate_contact (candidate_id, email, phone, city, region, country)
  VALUES (v_cand6_id, 'robert.martinez@example.com', '+1-555-0206', 'Los Angeles', 'CA', 'US');

  INSERT INTO candidate_preference (
      candidate_id, work_authorization, work_arrangement, willing_to_relocate,
      desired_salary_min, desired_salary_max, salary_currency, salary_period,
      availability_start, open_to_remote
  ) VALUES (
      v_cand6_id, 'US Citizen', 'Remote', 'Yes',
      90000, 115000, 'USD', 'year', '2 weeks', true
  );

  INSERT INTO candidate_experience (
      id, candidate_id, title, company, employment_type,
      start_date, end_date, description, industry
  ) VALUES (
      gen_random_uuid(), v_cand6_id, 'Senior UI/UX Designer', 'Airbnb', 'full_time',
      DATE '2020-09-01', NULL,
      'Designing user interfaces for mobile and web applications with focus on accessibility.',
      'Technology'
  );

  INSERT INTO candidate_education (
      id, candidate_id, degree, institution, field_of_study, graduation_year, gpa
  ) VALUES (
      gen_random_uuid(), v_cand6_id, 'BFA', 'Rhode Island School of Design',
      'Graphic Design', 2020, '3.75'
  );

  INSERT INTO candidate_skill (candidate_id, skill_id, level, years)
  VALUES
    (v_cand6_id, v_skill_ui_ux, 'expert', 4.5);

  INSERT INTO candidate_interest (candidate_id, interest_id)
  VALUES (v_cand6_id, v_interest_healthtech);

  INSERT INTO candidate_resume (id, candidate_id, s3_url, file_type, is_latest)
  VALUES (gen_random_uuid(), v_cand6_id, 's3://rightstaff/resumes/robert_martinez.pdf', 'pdf', true);

  RAISE NOTICE 'Candidate 6 (Robert Martinez) inserted: %', v_cand6_id;

  --------------------------------------------------------------------
  -- 9) CANDIDATE 7: Amanda Lee - Frontend Developer
  --------------------------------------------------------------------
  INSERT INTO candidate (id, full_name, years_experience, professional_summary)
  VALUES (gen_random_uuid(), 'Amanda Lee', 3.50,
          'Frontend Developer specializing in React and modern JavaScript frameworks.')
  RETURNING id INTO v_cand7_id;

  INSERT INTO candidate_contact (candidate_id, email, phone, city, region, country)
  VALUES (v_cand7_id, 'amanda.lee@example.com', '+1-555-0207', 'Denver', 'CO', 'US');

  INSERT INTO candidate_preference (
      candidate_id, work_authorization, work_arrangement, willing_to_relocate,
      desired_salary_min, desired_salary_max, salary_currency, salary_period,
      availability_start, open_to_remote
  ) VALUES (
      v_cand7_id, 'US Citizen', 'Remote', 'No',
      85000, 105000, 'USD', 'year', 'Immediate', true
  );

  INSERT INTO candidate_experience (
      id, candidate_id, title, company, employment_type,
      start_date, end_date, description, industry
  ) VALUES (
      gen_random_uuid(), v_cand7_id, 'Frontend Developer', 'Shopify', 'full_time',
      DATE '2021-06-01', NULL,
      'Building responsive web applications using React and TypeScript.',
      'E-commerce'
  );

  INSERT INTO candidate_education (
      id, candidate_id, degree, institution, field_of_study, graduation_year, gpa
  ) VALUES (
      gen_random_uuid(), v_cand7_id, 'BS', 'University of Colorado',
      'Computer Science', 2021, '3.65'
  );

  INSERT INTO candidate_skill (candidate_id, skill_id, level, years)
  VALUES
    (v_cand7_id, v_skill_javascript, 'advanced', 3.5),
    (v_cand7_id, v_skill_react, 'advanced', 3.0);

  INSERT INTO candidate_resume (id, candidate_id, s3_url, file_type, is_latest)
  VALUES (gen_random_uuid(), v_cand7_id, 's3://rightstaff/resumes/amanda_lee.pdf', 'pdf', true);

  RAISE NOTICE 'Candidate 7 (Amanda Lee) inserted: %', v_cand7_id;

  --------------------------------------------------------------------
  -- 10) CANDIDATE 8: Christopher Brown - Blockchain Developer
  --------------------------------------------------------------------
  INSERT INTO candidate (id, full_name, years_experience, professional_summary)
  VALUES (gen_random_uuid(), 'Christopher Brown', 5.50,
          'Blockchain Developer with expertise in Ethereum smart contracts and DeFi protocols.')
  RETURNING id INTO v_cand8_id;

  INSERT INTO candidate_contact (candidate_id, email, phone, city, region, country)
  VALUES (v_cand8_id, 'chris.brown@example.com', '+1-555-0208', 'Miami', 'FL', 'US');

  INSERT INTO candidate_preference (
      candidate_id, work_authorization, work_arrangement, willing_to_relocate,
      desired_salary_min, desired_salary_max, salary_currency, salary_period,
      availability_start, open_to_remote
  ) VALUES (
      v_cand8_id, 'US Citizen', 'Remote', 'Yes',
      130000, 160000, 'USD', 'year', '1 month', true
  );

  INSERT INTO candidate_experience (
      id, candidate_id, title, company, employment_type,
      start_date, end_date, description, industry
  ) VALUES (
      gen_random_uuid(), v_cand8_id, 'Blockchain Developer', 'ConsenSys', 'full_time',
      DATE '2019-10-01', NULL,
      'Developing smart contracts and decentralized applications on Ethereum.',
      'Blockchain'
  );

  INSERT INTO candidate_education (
      id, candidate_id, degree, institution, field_of_study, graduation_year, gpa
  ) VALUES (
      gen_random_uuid(), v_cand8_id, 'MS', 'Carnegie Mellon University',
      'Computer Science', 2019, '3.90'
  );

  INSERT INTO candidate_skill (candidate_id, skill_id, level, years)
  VALUES
    (v_cand8_id, v_skill_javascript, 'advanced', 5.5),
    (v_cand8_id, v_skill_nodejs, 'advanced', 4.0);

  INSERT INTO candidate_interest (candidate_id, interest_id)
  VALUES (v_cand8_id, v_interest_blockchain);

  INSERT INTO candidate_resume (id, candidate_id, s3_url, file_type, is_latest)
  VALUES (gen_random_uuid(), v_cand8_id, 's3://rightstaff/resumes/chris_brown.pdf', 'pdf', true);

  RAISE NOTICE 'Candidate 8 (Christopher Brown) inserted: %', v_cand8_id;

  --------------------------------------------------------------------
  -- 11) CANDIDATE 9: Nina Patel - Database Administrator
  --------------------------------------------------------------------
  INSERT INTO candidate (id, full_name, years_experience, professional_summary)
  VALUES (gen_random_uuid(), 'Nina Patel', 10.00,
          'Senior DBA specializing in PostgreSQL, MongoDB, and database performance optimization.')
  RETURNING id INTO v_cand9_id;

  INSERT INTO candidate_contact (candidate_id, email, phone, city, region, country)
  VALUES (v_cand9_id, 'nina.patel@example.com', '+1-555-0209', 'Chicago', 'IL', 'US');

  INSERT INTO candidate_preference (
      candidate_id, work_authorization, work_arrangement, willing_to_relocate,
      desired_salary_min, desired_salary_max, salary_currency, salary_period,
      availability_start, open_to_remote
  ) VALUES (
      v_cand9_id, 'US Citizen', 'Hybrid', 'No',
      135000, 165000, 'USD', 'year', '2 weeks', true
  );

  INSERT INTO candidate_experience (
      id, candidate_id, title, company, employment_type,
      start_date, end_date, description, industry
  ) VALUES (
      gen_random_uuid(), v_cand9_id, 'Senior Database Administrator', 'Oracle', 'full_time',
      DATE '2015-03-01', NULL,
      'Managing enterprise-scale databases and implementing high-availability solutions.',
      'Technology'
  );

  INSERT INTO candidate_education (
      id, candidate_id, degree, institution, field_of_study, graduation_year, gpa
  ) VALUES (
      gen_random_uuid(), v_cand9_id, 'MS', 'University of Illinois',
      'Database Systems', 2014, '3.82'
  );

  INSERT INTO candidate_skill (candidate_id, skill_id, level, years)
  VALUES
    (v_cand9_id, v_skill_sql, 'expert', 10.0),
    (v_cand9_id, v_skill_mongodb, 'advanced', 5.0),
    (v_cand9_id, v_skill_python, 'advanced', 6.0);

  INSERT INTO candidate_resume (id, candidate_id, s3_url, file_type, is_latest)
  VALUES (gen_random_uuid(), v_cand9_id, 's3://rightstaff/resumes/nina_patel.pdf', 'pdf', true);

  RAISE NOTICE 'Candidate 9 (Nina Patel) inserted: %', v_cand9_id;

  --------------------------------------------------------------------
  -- 12) CANDIDATE 10: James Thompson - Mobile Developer
  --------------------------------------------------------------------
  INSERT INTO candidate (id, full_name, years_experience, professional_summary)
  VALUES (gen_random_uuid(), 'James Thompson', 6.50,
          'Mobile Developer proficient in iOS and Android development with React Native.')
  RETURNING id INTO v_cand10_id;

  INSERT INTO candidate_contact (candidate_id, email, phone, city, region, country)
  VALUES (v_cand10_id, 'james.thompson@example.com', '+1-555-0210', 'Portland', 'OR', 'US');

  INSERT INTO candidate_preference (
      candidate_id, work_authorization, work_arrangement, willing_to_relocate,
      desired_salary_min, desired_salary_max, salary_currency, salary_period,
      availability_start, open_to_remote
  ) VALUES (
      v_cand10_id, 'US Citizen', 'Remote', 'Specific: Pacific Northwest',
      115000, 140000, 'USD', 'year', 'Immediate', true
  );

  INSERT INTO candidate_experience (
      id, candidate_id, title, company, employment_type,
      start_date, end_date, description, industry
  ) VALUES (
      gen_random_uuid(), v_cand10_id, 'Senior Mobile Developer', 'Nike', 'full_time',
      DATE '2018-07-01', NULL,
      'Developing mobile apps for iOS and Android using React Native.',
      'Retail'
  );

  INSERT INTO candidate_education (
      id, candidate_id, degree, institution, field_of_study, graduation_year, gpa
  ) VALUES (
      gen_random_uuid(), v_cand10_id, 'BS', 'Oregon State University',
      'Computer Science', 2018, '3.72'
  );

  INSERT INTO candidate_skill (candidate_id, skill_id, level, years)
  VALUES
    (v_cand10_id, v_skill_react, 'expert', 5.0),
    (v_cand10_id, v_skill_javascript, 'expert', 6.5);

  INSERT INTO candidate_interest (candidate_id, interest_id)
  VALUES (v_cand10_id, v_interest_gaming);

  INSERT INTO candidate_resume (id, candidate_id, s3_url, file_type, is_latest)
  VALUES (gen_random_uuid(), v_cand10_id, 's3://rightstaff/resumes/james_thompson.pdf', 'pdf', true);

  RAISE NOTICE 'Candidate 10 (James Thompson) inserted: %', v_cand10_id;

  --------------------------------------------------------------------
  -- 13) Insert Jobs
  --------------------------------------------------------------------
  INSERT INTO job (id, title, department, location, status)
  VALUES (gen_random_uuid(), 'Full Stack Developer', 'Engineering', 'San Francisco, CA', 'open')
  RETURNING id INTO v_job1_id;

  INSERT INTO job (id, title, department, location, status)
  VALUES (gen_random_uuid(), 'Data Scientist', 'Data Science', 'Remote', 'open')
  RETURNING id INTO v_job2_id;

  INSERT INTO job (id, title, department, location, status)
  VALUES (gen_random_uuid(), 'DevOps Engineer', 'Operations', 'Austin, TX', 'open')
  RETURNING id INTO v_job3_id;

  INSERT INTO job (id, title, department, location, status)
  VALUES (gen_random_uuid(), 'Product Manager', 'Product', 'Boston, MA', 'open')
  RETURNING id INTO v_job4_id;

  INSERT INTO job (id, title, department, location, status)
  VALUES (gen_random_uuid(), 'UI/UX Designer', 'Design', 'Remote', 'open')
  RETURNING id INTO v_job5_id;

  RAISE NOTICE 'Jobs inserted successfully';

  --------------------------------------------------------------------
  -- 14) Create Applications (linking candidates to jobs)
  --------------------------------------------------------------------
  -- Sarah Johnson applies to Full Stack Developer
  INSERT INTO application (id, candidate_id, job_id, status)
  VALUES (gen_random_uuid(), v_cand1_id, v_job1_id, 'applied')
  ON CONFLICT DO NOTHING;

  -- Michael Chen applies to Data Scientist
  INSERT INTO application (id, candidate_id, job_id, status)
  VALUES (gen_random_uuid(), v_cand2_id, v_job2_id, 'shortlist')
  ON CONFLICT DO NOTHING;

  -- Emily Rodriguez applies to DevOps Engineer
  INSERT INTO application (id, candidate_id, job_id, status)
  VALUES (gen_random_uuid(), v_cand3_id, v_job3_id, 'interview')
  ON CONFLICT DO NOTHING;

  -- Jessica Williams applies to Product Manager
  INSERT INTO application (id, candidate_id, job_id, status)
  VALUES (gen_random_uuid(), v_cand5_id, v_job4_id, 'applied')
  ON CONFLICT DO NOTHING;

  -- Robert Martinez applies to UI/UX Designer
  INSERT INTO application (id, candidate_id, job_id, status)
  VALUES (gen_random_uuid(), v_cand6_id, v_job5_id, 'screen')
  ON CONFLICT DO NOTHING;

  -- Amanda Lee also applies to Full Stack Developer
  INSERT INTO application (id, candidate_id, job_id, status)
  VALUES (gen_random_uuid(), v_cand7_id, v_job1_id, 'applied')
  ON CONFLICT DO NOTHING;

  -- David Kim applies to Full Stack Developer
  INSERT INTO application (id, candidate_id, job_id, status)
  VALUES (gen_random_uuid(), v_cand4_id, v_job1_id, 'shortlist')
  ON CONFLICT DO NOTHING;

  RAISE NOTICE 'Applications created successfully';

  RAISE NOTICE '========================================';
  RAISE NOTICE 'Dummy Data Insertion Complete!';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'Total Candidates: 10';
  RAISE NOTICE 'Total Jobs: 5';
  RAISE NOTICE 'Total Applications: 7';
  RAISE NOTICE '========================================';

END
$$ LANGUAGE plpgsql;

-- Display summary
SELECT 
  (SELECT COUNT(*) FROM candidate) as total_candidates,
  (SELECT COUNT(*) FROM job) as total_jobs,
  (SELECT COUNT(*) FROM application) as total_applications,
  (SELECT COUNT(*) FROM skill) as total_skills,
  (SELECT COUNT(*) FROM interest) as total_interests;

COMMIT;

