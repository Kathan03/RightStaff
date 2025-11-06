SET search_path = rightstaff, public;

CREATE OR REPLACE FUNCTION rightstaff.set_latest_resume(p_candidate_id uuid, p_resume_id uuid)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM rightstaff.candidate_resume
    WHERE id = p_resume_id AND candidate_id = p_candidate_id
  ) THEN
    RAISE EXCEPTION 'Resume % does not belong to candidate %', p_resume_id, p_candidate_id;
  END IF;

  UPDATE rightstaff.candidate_resume
  SET is_latest = false
  WHERE candidate_id = p_candidate_id AND is_latest = true;

  UPDATE rightstaff.candidate_resume
  SET is_latest = true
  WHERE id = p_resume_id;
END $$;
