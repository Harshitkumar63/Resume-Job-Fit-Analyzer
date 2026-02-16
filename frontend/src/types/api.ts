/**
 * TypeScript types mirroring the FastAPI Pydantic schemas.
 *
 * Single source of truth for API contract types on the frontend.
 * Keep in sync with backend app/schemas/resume.py.
 */

// ── Request Types ────────────────────────────────────────────

export interface JobDescription {
  title: string;
  description: string;
  required_skills: string[];
  preferred_skills: string[];
  min_experience_years: number | null;
}

export interface MatchRequest {
  resume_id: string;
  job_description: JobDescription;
}

// ── Response Types ───────────────────────────────────────────

export interface UploadResponse {
  resume_id: string;
  filename: string;
  skill_count: number;
  experience_years: number | null;
  message: string;
}

export interface SkillMatch {
  skill: string;
  similarity_score: number;
  matched: boolean;
}

export interface ScoreBreakdown {
  semantic_score: number;
  graph_score: number;
  experience_score: number;
  semantic_weight: number;
  graph_weight: number;
  experience_weight: number;
}

export interface MatchResult {
  resume_id: string;
  job_title: string;
  overall_score: number;
  fit_label: string;
  score_breakdown: ScoreBreakdown;
  matched_skills: SkillMatch[];
  missing_skills: string[];
  explanation: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  models_loaded: boolean;
}

// ── UI State Types ───────────────────────────────────────────

export type AnalysisStep = "upload" | "processing" | "results";

export interface AnalysisState {
  step: AnalysisStep;
  uploadResponse: UploadResponse | null;
  matchResult: MatchResult | null;
  error: string | null;
  isLoading: boolean;
}
