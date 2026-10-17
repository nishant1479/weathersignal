export interface Report {
  id: string;
  original_text: string;
  submitted_at: string;
  event_time?: string | null;
  place_text?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  status: string;
}

export interface Claim {
  id: string;
  report_id: string;
  claim_text: string;
  event_type: string;
  normalized_location?: string | null;
  event_time_start?: string | null;
  event_time_end?: string | null;
  severity?: string | null;
  ambiguities: string[];
  extraction_model: string;
}

export interface EvidenceAssessment {
  id: string;
  claim_id: string;
  evidence_id: string;
  relationship: string;
  geographic_relevance: number;
  temporal_relevance: number;
  event_match: boolean;
  reason: string;
  assessment_method: string;
}

export interface EvidenceItem {
  id: string;
  provider_name: string;
  source_url?: string | null;
  evidence_type: string;
  published_at?: string | null;
  observed_at?: string | null;
  retrieved_at: string;
  latitude?: number | null;
  longitude?: number | null;
  coverage_area?: string | null;
  raw_value?: string | null;
  unit?: string | null;
  summary?: string | null;
  data_quality_notes?: string | null;
  retrieval_status: string;
  assessments?: EvidenceAssessment[];
}

export interface FinalDecision {
  investigation_id: string;
  overall_status: string;
  per_claim_status: Record<string, string>;
  rationale: string;
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  unresolved_questions: string[];
  limitations: string[];
  created_at: string;
  review_required: boolean;
  reviewer_decision?: string | null;
  reviewer_reason?: string | null;
  reviewer_id?: string | null;
  reviewed_at?: string | null;
}

export interface InvestigationDetail {
  id: string;
  report_id: string;
  status: string;
  overall_status?: string | null;
  created_at: string;
  completed_at?: string | null;
  report?: Report | null;
  claims: Claim[];
  decision?: FinalDecision | null;
}

export interface ProviderStatus {
  provider_name: string;
  configured: boolean;
  status: string;
  message: string;
  last_checked_at: string;
}

export interface ReviewQueueItem {
  investigation_id: string;
  report_id: string;
  report_text?: string | null;
  created_at: string;
  overall_status?: string | null;
  rationale?: string | null;
  unresolved_questions: string[];
  limitations: string[];
}
