from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class VerificationStatus(str, Enum):
    CORROBORATED = "CORROBORATED"
    CONTRADICTED = "CONTRADICTED"
    UNVERIFIED = "UNVERIFIED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    PARTIALLY_CORROBORATED = "PARTIALLY_CORROBORATED"


class EvidenceType(str, Enum):
    OBSERVATION = "OBSERVATION"
    FORECAST = "FORECAST"
    WARNING = "WARNING"
    BULLETIN = "BULLETIN"
    USER_REPORT = "USER_REPORT"


class EvidenceRelationship(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    CONTEXT_ONLY = "context_only"
    IRRELEVANT = "irrelevant"
    UNKNOWN = "unknown"


class AssessmentMethod(str, Enum):
    DETERMINISTIC = "deterministic"
    MODEL_ASSISTED = "model_assisted"
    HUMAN = "human"


class ReportStatus(str, Enum):
    PENDING = "PENDING"
    INVESTIGATING = "INVESTIGATING"
    COMPLETED = "COMPLETED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"


# Report Schemas
class ReportCreate(BaseModel):
    original_text: str = Field(..., min_length=5, max_length=2000, description="Raw weather report text")
    event_time: Optional[datetime] = Field(None, description="Reported event time if known")
    place_text: Optional[str] = Field(None, max_length=200, description="Reported location name")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Longitude coordinate")
    attachment_reference: Optional[str] = Field(None, description="Optional path or key to image/file attachment")

    @field_validator("original_text")
    @classmethod
    def strip_text(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Report text cannot be blank or whitespace only")
        return cleaned


class ReportResponse(BaseModel):
    id: str
    original_text: str
    submitted_at: datetime
    event_time: Optional[datetime]
    place_text: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    attachment_reference: Optional[str]
    status: ReportStatus

    class Config:
        from_attributes = True


# Claim Schemas
class ClaimItem(BaseModel):
    id: str
    report_id: str
    claim_text: str
    event_type: str
    normalized_location: Optional[str] = None
    event_time_start: Optional[datetime] = None
    event_time_end: Optional[datetime] = None
    severity: Optional[str] = None
    ambiguities: List[str] = Field(default_factory=list)
    extraction_model: str = "deterministic"
    extraction_version: str = "1.0"

    class Config:
        from_attributes = True


# Evidence Schemas
class EvidenceItemSchema(BaseModel):
    id: str
    provider_name: str
    source_url: Optional[str] = None
    evidence_type: EvidenceType
    published_at: Optional[datetime] = None
    observed_at: Optional[datetime] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    retrieved_at: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    coverage_area: Optional[str] = None
    raw_value: Optional[str] = None
    unit: Optional[str] = None
    summary: Optional[str] = None
    data_quality_notes: Optional[str] = None
    retrieval_status: str = "SUCCESS"

    class Config:
        from_attributes = True


class EvidenceAssessmentSchema(BaseModel):
    id: str
    claim_id: str
    evidence_id: str
    relationship: EvidenceRelationship
    geographic_relevance: float = Field(0.0, ge=0.0, le=1.0)
    temporal_relevance: float = Field(0.0, ge=0.0, le=1.0)
    event_match: bool = False
    reason: str
    assessment_method: AssessmentMethod = AssessmentMethod.DETERMINISTIC

    class Config:
        from_attributes = True


# Final Investigation and Decision Schemas
class FinalDecisionSchema(BaseModel):
    investigation_id: str
    overall_status: VerificationStatus
    per_claim_status: Dict[str, VerificationStatus] = Field(default_factory=dict)
    rationale: str
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    contradicting_evidence_ids: List[str] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    created_at: datetime
    review_required: bool = False
    reviewer_decision: Optional[VerificationStatus] = None
    reviewer_reason: Optional[str] = None

    class Config:
        from_attributes = True


class InvestigationResponse(BaseModel):
    id: str
    report_id: str
    status: ReportStatus
    overall_status: Optional[VerificationStatus] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    claims: List[ClaimItem] = Field(default_factory=list)
    decision: Optional[FinalDecisionSchema] = None

    class Config:
        from_attributes = True


class ReviewSubmission(BaseModel):
    decision: VerificationStatus
    reason: str = Field(..., min_length=5, description="Mandatory reason for reviewer action")
    reviewer_id: Optional[str] = "reviewer_default"


class ProviderHealth(BaseModel):
    provider_name: str
    configured: bool
    status: str
    message: str
    last_checked_at: datetime
