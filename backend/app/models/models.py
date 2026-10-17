import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, DateTime, Float, Boolean, JSON, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.schemas.schemas import (
    VerificationStatus, EvidenceType, EvidenceRelationship, AssessmentMethod, ReportStatus
)


def utc_now():
    return datetime.now(timezone.utc)


def gen_uuid():
    return str(uuid.uuid4())


class ReportModel(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    original_text = Column(Text, nullable=False)
    submitted_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=True)
    place_text = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    attachment_reference = Column(String(512), nullable=True)
    status = Column(SQLEnum(ReportStatus), default=ReportStatus.PENDING, nullable=False)

    claims = relationship("ClaimModel", back_populates="report", cascade="all, delete-orphan")
    investigations = relationship("InvestigationModel", back_populates="report", cascade="all, delete-orphan")


class ClaimModel(Base):
    __tablename__ = "claims"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    report_id = Column(String(36), ForeignKey("reports.id"), nullable=False)
    claim_text = Column(Text, nullable=False)
    event_type = Column(String(100), nullable=False)
    normalized_location = Column(String(255), nullable=True)
    event_time_start = Column(DateTime(timezone=True), nullable=True)
    event_time_end = Column(DateTime(timezone=True), nullable=True)
    severity = Column(String(50), nullable=True)
    ambiguities = Column(JSON, default=list, nullable=False)
    extraction_model = Column(String(100), default="deterministic", nullable=False)
    extraction_version = Column(String(50), default="1.0", nullable=False)

    report = relationship("ReportModel", back_populates="claims")
    assessments = relationship("EvidenceAssessmentModel", back_populates="claim", cascade="all, delete-orphan")


class InvestigationModel(Base):
    __tablename__ = "investigations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    report_id = Column(String(36), ForeignKey("reports.id"), nullable=False)
    status = Column(SQLEnum(ReportStatus), default=ReportStatus.PENDING, nullable=False)
    overall_status = Column(SQLEnum(VerificationStatus), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    report = relationship("ReportModel", back_populates="investigations")
    evidence_items = relationship("EvidenceItemModel", back_populates="investigation", cascade="all, delete-orphan")
    decision = relationship("FinalDecisionModel", uselist=False, back_populates="investigation", cascade="all, delete-orphan")


class EvidenceItemModel(Base):
    __tablename__ = "evidence_items"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    investigation_id = Column(String(36), ForeignKey("investigations.id"), nullable=False)
    provider_name = Column(String(100), nullable=False)
    source_url = Column(String(512), nullable=True)
    evidence_type = Column(SQLEnum(EvidenceType), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    observed_at = Column(DateTime(timezone=True), nullable=True)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_to = Column(DateTime(timezone=True), nullable=True)
    retrieved_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    coverage_area = Column(String(255), nullable=True)
    raw_value = Column(String(255), nullable=True)
    unit = Column(String(50), nullable=True)
    summary = Column(Text, nullable=True)
    raw_payload_reference = Column(Text, nullable=True)
    data_quality_notes = Column(Text, nullable=True)
    retrieval_status = Column(String(50), default="SUCCESS", nullable=False)

    investigation = relationship("InvestigationModel", back_populates="evidence_items")
    assessments = relationship("EvidenceAssessmentModel", back_populates="evidence", cascade="all, delete-orphan")


class EvidenceAssessmentModel(Base):
    __tablename__ = "evidence_assessments"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id"), nullable=False)
    evidence_id = Column(String(36), ForeignKey("evidence_items.id"), nullable=False)
    rel_type = Column("relationship", SQLEnum(EvidenceRelationship), nullable=False)
    geographic_relevance = Column(Float, default=0.0, nullable=False)
    temporal_relevance = Column(Float, default=0.0, nullable=False)
    event_match = Column(Boolean, default=False, nullable=False)
    reason = Column(Text, nullable=False)
    assessment_method = Column(SQLEnum(AssessmentMethod), default=AssessmentMethod.DETERMINISTIC, nullable=False)

    claim = relationship("ClaimModel", back_populates="assessments")
    evidence = relationship("EvidenceItemModel", back_populates="assessments")


class FinalDecisionModel(Base):
    __tablename__ = "final_decisions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    investigation_id = Column(String(36), ForeignKey("investigations.id"), unique=True, nullable=False)
    overall_status = Column(SQLEnum(VerificationStatus), nullable=False)
    per_claim_status = Column(JSON, default=dict, nullable=False)
    rationale = Column(Text, nullable=False)
    supporting_evidence_ids = Column(JSON, default=list, nullable=False)
    contradicting_evidence_ids = Column(JSON, default=list, nullable=False)
    unresolved_questions = Column(JSON, default=list, nullable=False)
    limitations = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    review_required = Column(Boolean, default=False, nullable=False)
    reviewer_decision = Column(SQLEnum(VerificationStatus), nullable=True)
    reviewer_reason = Column(Text, nullable=True)
    reviewer_id = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    investigation = relationship("InvestigationModel", back_populates="decision")
