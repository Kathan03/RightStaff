// ═══════════════════════════════════════════════════════════════
// Candidate Types
// ═══════════════════════════════════════════════════════════════

export interface ParsedCandidate {
  full_name: string;
  email: string;
  phone: string | null;
  location: string | null;
  years_experience: number | null;
  professional_summary: string;
  skills: string[];
}

export interface UploadResumeResponse {
  temp_id: string;
  parsed_data: ParsedCandidate;
  message: string;
}

export interface CreateCandidateRequest {
  temp_id: string;
  full_name: string;
  email?: string;
  phone?: string;
  location?: string;
  years_experience?: number;
  professional_summary?: string;
}

export interface CreateCandidateResponse {
  candidate_id: string;
  status: string;
  message: string;
}

// ═══════════════════════════════════════════════════════════════
// Job Types
// ═══════════════════════════════════════════════════════════════

export interface Job {
  id: string;
  title: string;
  description: string;
  company_name?: string;
  location?: string;
  salary_min?: number;
  salary_max?: number;
  required_skills: string[];
  must_have_skills?: string[];
  min_years_experience?: number;
  max_years_experience?: number;
  status: string;
  created_at?: string;
}

export interface CreateJobRequest {
  title: string;
  description: string;
  required_skills: string[];
  must_have_skills?: string[];
  min_years_experience?: number;
  max_years_experience?: number;
  location?: string;
}

export interface CreateJobResponse {
  job_id: string;
  title: string;
  status: string;
}

export interface ApplyToJobRequest {
  candidate_id: string;
}

export interface ApplyToJobResponse {
  application_id: string;
  candidate_id: string;
  job_id: string;
  status: string;
  applied_at: string;
  message: string;
}

export interface Applicant {
  application_id: string;
  candidate_id: string;
  full_name: string;
  email?: string;
  phone?: string;
  location?: string;
  years_experience?: number;
  professional_summary?: string;
  status: string;
  applied_at: string;
}

export interface ApplicantsResponse {
  job_id: string;
  job_title: string;
  total_applicants: number;
  applicants: Applicant[];
}

// ═══════════════════════════════════════════════════════════════
// Ranking Types
// ═══════════════════════════════════════════════════════════════

export interface RankedCandidate {
  candidate_id: string;
  full_name: string;  // Added: Display name instead of ID
  final_score: number;
  band: string;
  confidence: number;
  summary: string;
  reasons: string[];
  evidence_snippets: Array<{
    text: string;
    source: string;
    relevance: number;
  }>;
  score_breakdown: {
    dense_score?: number;
    structured_score?: number;
    pairwise_score?: number;
    completeness_score?: number;
  };
}

export interface RankingResponse {
  job_id: string;
  ranked_candidates: RankedCandidate[];
  metadata: {
    total_candidates: number;
    high_confidence: number;
    medium_confidence: number;
    low_confidence: number;
  };
}

// ═══════════════════════════════════════════════════════════════
// Chat Types
// ═══════════════════════════════════════════════════════════════

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatResponse {
  type: 'token' | 'done' | 'error';
  content?: string;
  citations?: string[];
  message?: string;
}
