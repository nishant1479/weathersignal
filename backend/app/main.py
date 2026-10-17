from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.core.database import get_db, init_db
from backend.app.schemas.schemas import (
    ReportCreate, ReportResponse, InvestigationResponse,
    FinalDecisionSchema, ReviewSubmission, ProviderHealth, VerificationStatus, ReportStatus
)
from backend.app.repositories.repositories import ReportRepository, InvestigationRepository
from backend.app.models.models import FinalDecisionModel

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="WeatherSignal Agentic Weather Verification System API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await init_db()


@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/ready", tags=["System"])
async def ready(db: AsyncSession = Depends(get_db)):
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    imd_configured = bool(settings.IMD_API_KEY and settings.IMD_API_KEY.strip())
    llm_configured = bool(settings.LLM_PROVIDER in ["deterministic", "mock"] or (settings.LLM_API_KEY and settings.LLM_API_KEY.strip()))

    overall = "ready" if db_ok else "not_ready"

    return {
        "status": overall,
        "database": "connected" if db_ok else "disconnected",
        "providers": {
            "imd": "configured" if imd_configured else "not_configured (limited mode)",
            "open_meteo": "ready (public fallback)",
            "geocoding": settings.GEOCODING_PROVIDER,
            "llm": f"{settings.LLM_PROVIDER} ({'configured' if llm_configured else 'missing_key'})"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/api/v1/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED, tags=["Reports"])
async def submit_report(report_in: ReportCreate, db: AsyncSession = Depends(get_db)):
    repo = ReportRepository(db)
    created = await repo.create_report(report_in)
    return created


@app.get("/api/v1/reports", response_model=List[ReportResponse], tags=["Reports"])
async def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    repo = ReportRepository(db)
    return await repo.list_reports(skip=skip, limit=limit)


@app.get("/api/v1/reports/{report_id}", response_model=ReportResponse, tags=["Reports"])
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)):
    repo = ReportRepository(db)
    report = await repo.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.post("/api/v1/reports/{report_id}/investigate", tags=["Investigation"])
async def investigate_report(report_id: str, db: AsyncSession = Depends(get_db)):
    repo = ReportRepository(db)
    report = await repo.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    from backend.app.graph.workflow import run_investigation_workflow
    investigation = await run_investigation_workflow(report_id=report.id, db=db)
    return {
        "message": "Investigation completed",
        "investigation_id": investigation.id,
        "report_id": report.id,
        "status": investigation.status,
        "overall_status": investigation.overall_status
    }


@app.get("/api/v1/investigations/{investigation_id}", tags=["Investigation"])
async def get_investigation(investigation_id: str, db: AsyncSession = Depends(get_db)):
    inv_repo = InvestigationRepository(db)
    inv = await inv_repo.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    decision_data = None
    if inv.decision:
        decision_data = {
            "investigation_id": inv.decision.investigation_id,
            "overall_status": inv.decision.overall_status,
            "per_claim_status": inv.decision.per_claim_status,
            "rationale": inv.decision.rationale,
            "supporting_evidence_ids": inv.decision.supporting_evidence_ids,
            "contradicting_evidence_ids": inv.decision.contradicting_evidence_ids,
            "unresolved_questions": inv.decision.unresolved_questions,
            "limitations": inv.decision.limitations,
            "created_at": inv.decision.created_at,
            "review_required": inv.decision.review_required,
            "reviewer_decision": inv.decision.reviewer_decision,
            "reviewer_reason": inv.decision.reviewer_reason,
            "reviewer_id": inv.decision.reviewer_id,
            "reviewed_at": inv.decision.reviewed_at
        }

    claims_data = []
    if inv.report and inv.report.claims:
        for c in inv.report.claims:
            claims_data.append({
                "id": c.id,
                "report_id": c.report_id,
                "claim_text": c.claim_text,
                "event_type": c.event_type,
                "normalized_location": c.normalized_location,
                "event_time_start": c.event_time_start,
                "event_time_end": c.event_time_end,
                "severity": c.severity,
                "ambiguities": c.ambiguities,
                "extraction_model": c.extraction_model,
                "extraction_version": c.extraction_version
            })

    return {
        "id": inv.id,
        "report_id": inv.report_id,
        "status": inv.status,
        "overall_status": inv.overall_status,
        "created_at": inv.created_at,
        "completed_at": inv.completed_at,
        "report": {
            "id": inv.report.id,
            "original_text": inv.report.original_text,
            "place_text": inv.report.place_text,
            "event_time": inv.report.event_time,
            "latitude": inv.report.latitude,
            "longitude": inv.report.longitude
        } if inv.report else None,
        "claims": claims_data,
        "decision": decision_data
    }


@app.get("/api/v1/investigations/{investigation_id}/evidence", tags=["Investigation"])
async def get_investigation_evidence(investigation_id: str, db: AsyncSession = Depends(get_db)):
    inv_repo = InvestigationRepository(db)
    inv = await inv_repo.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    items = []
    for item in inv.evidence_items:
        assessments = [
            {
                "id": a.id,
                "claim_id": a.claim_id,
                "evidence_id": a.evidence_id,
                "relationship": a.rel_type,
                "geographic_relevance": a.geographic_relevance,
                "temporal_relevance": a.temporal_relevance,
                "event_match": a.event_match,
                "reason": a.reason,
                "assessment_method": a.assessment_method
            }
            for a in item.assessments
        ]
        items.append({
            "id": item.id,
            "provider_name": item.provider_name,
            "source_url": item.source_url,
            "evidence_type": item.evidence_type,
            "published_at": item.published_at,
            "observed_at": item.observed_at,
            "valid_from": item.valid_from,
            "valid_to": item.valid_to,
            "retrieved_at": item.retrieved_at,
            "latitude": item.latitude,
            "longitude": item.longitude,
            "coverage_area": item.coverage_area,
            "raw_value": item.raw_value,
            "unit": item.unit,
            "summary": item.summary,
            "data_quality_notes": item.data_quality_notes,
            "retrieval_status": item.retrieval_status,
            "assessments": assessments
        })

    return {
        "investigation_id": investigation_id,
        "evidence_count": len(items),
        "evidence_items": items
    }


@app.get("/api/v1/review-queue", tags=["Review"])
async def get_review_queue(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    inv_repo = InvestigationRepository(db)
    items = await inv_repo.list_review_queue(skip=skip, limit=limit)
    res = []
    for inv in items:
        res.append({
            "investigation_id": inv.id,
            "report_id": inv.report_id,
            "report_text": inv.report.original_text if inv.report else None,
            "created_at": inv.created_at,
            "overall_status": inv.overall_status,
            "rationale": inv.decision.rationale if inv.decision else None,
            "unresolved_questions": inv.decision.unresolved_questions if inv.decision else [],
            "limitations": inv.decision.limitations if inv.decision else []
        })
    return res


@app.post("/api/v1/investigations/{investigation_id}/review", tags=["Review"])
async def submit_human_review(
    investigation_id: str,
    submission: ReviewSubmission,
    db: AsyncSession = Depends(get_db)
):
    inv_repo = InvestigationRepository(db)
    inv = await inv_repo.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if not inv.decision:
        raise HTTPException(status_code=400, detail="Cannot review an investigation without a completed decision")

    inv.decision.reviewer_decision = submission.decision
    inv.decision.reviewer_reason = submission.reason
    inv.decision.reviewer_id = submission.reviewer_id
    inv.decision.reviewed_at = datetime.now(timezone.utc)
    inv.overall_status = submission.decision
    inv.status = ReportStatus.COMPLETED

    await db.commit()
    await db.refresh(inv)

    return {
        "investigation_id": inv.id,
        "reviewer_decision": inv.decision.reviewer_decision,
        "reviewer_reason": inv.decision.reviewer_reason,
        "reviewed_at": inv.decision.reviewed_at,
        "overall_status": inv.overall_status
    }


@app.get("/api/v1/providers/status", tags=["System"])
async def get_provider_statuses():
    imd_configured = bool(settings.IMD_API_KEY and settings.IMD_API_KEY.strip())
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "provider_name": "India Meteorological Department (IMD)",
            "configured": imd_configured,
            "status": "HEALTHY" if imd_configured else "NOT_CONFIGURED",
            "message": "Live API key present" if imd_configured else "Operating in documented limited mode (x-api-key required for live endpoints)",
            "last_checked_at": now
        },
        {
            "provider_name": "Open-Meteo Historical & Current Archive",
            "configured": True,
            "status": "HEALTHY",
            "message": "Live open access active for global & India coordinates",
            "last_checked_at": now
        },
        {
            "provider_name": "Nominatim Geocoding (OpenStreetMap)",
            "configured": True,
            "status": "HEALTHY",
            "message": "Geocoding and place resolution available with user-agent policy",
            "last_checked_at": now
        }
    ]
