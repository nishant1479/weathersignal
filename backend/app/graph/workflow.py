import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.schemas.schemas import (
    ClaimItem, EvidenceItemSchema, EvidenceAssessmentSchema,
    VerificationStatus, ReportStatus
)
from backend.app.models.models import (
    ReportModel, ClaimModel, InvestigationModel, EvidenceItemModel,
    EvidenceAssessmentModel, FinalDecisionModel
)
from backend.app.services.claim_extractor import ClaimExtractor
from backend.app.services.geocoding import GeocodingService
from backend.app.services.verification_engine import VerificationEngine
from backend.app.providers.imd import IMDProvider
from backend.app.providers.open_meteo import OpenMeteoProvider
from backend.app.core.config import settings


# LangGraph State Schema
class InvestigationState(Dict[str, Any]):
    report_id: str
    investigation_id: str
    original_text: str
    place_text: Optional[str]
    event_time: Optional[datetime]
    latitude: Optional[float]
    longitude: Optional[float]
    claims: List[Dict[str, Any]]
    evidence_items: List[Dict[str, Any]]
    assessments: List[Dict[str, Any]]
    overall_status: Optional[str]
    per_claim_status: Dict[str, str]
    rationale: str
    supporting_evidence_ids: List[str]
    contradicting_evidence_ids: List[str]
    unresolved_questions: List[str]
    limitations: List[str]
    review_required: bool
    iteration_count: int
    should_retry: bool


async def node_validate_report(state: InvestigationState) -> InvestigationState:
    text = state.get("original_text", "").strip()
    if len(text) < 5:
        state["limitations"].append("Report text is too short to extract meaningful claims.")
    return state


async def node_extract_claims(state: InvestigationState) -> InvestigationState:
    claims = ClaimExtractor.extract_deterministic(
        report_id=state["report_id"],
        text=state["original_text"],
        default_place=state.get("place_text"),
        default_time=state.get("event_time")
    )
    state["claims"] = [c.model_dump() for c in claims]
    return state


async def node_resolve_location_and_time(state: InvestigationState) -> InvestigationState:
    lat = state.get("latitude")
    lon = state.get("longitude")
    place = state.get("place_text")

    if (lat is None or lon is None) and place:
        geocoder = GeocodingService()
        res_lat, res_lon, norm_name = await geocoder.resolve(place)
        if res_lat is not None and res_lon is not None:
            state["latitude"] = res_lat
            state["longitude"] = res_lon
            state["place_text"] = norm_name
        else:
            state["unresolved_questions"].append(f"Could not precisely resolve coordinates for place '{place}'.")
    elif lat is None or lon is None:
        state["unresolved_questions"].append("No geographic location or coordinates provided with report.")

    if state.get("event_time") is None:
        # Default to current time with an explicit limitation note
        now = datetime.now(timezone.utc)
        state["event_time"] = now
        state["limitations"].append("Event time was not specified by reporter; checking latest available observations.")

    return state


async def node_plan_investigation(state: InvestigationState) -> InvestigationState:
    # Determines if coordinates exist to query providers
    state["iteration_count"] = state.get("iteration_count", 0) + 1
    return state


async def node_retrieve_weather_observations(state: InvestigationState) -> InvestigationState:
    lat = state.get("latitude")
    lon = state.get("longitude")
    target_time = state.get("event_time")
    evidence_list: List[Dict[str, Any]] = state.get("evidence_items", [])

    # 1. Official IMD Provider
    imd = IMDProvider()
    imd_items = await imd.get_observations(
        latitude=lat or 0.0,
        longitude=lon or 0.0,
        target_time=target_time
    )
    for it in imd_items:
        evidence_list.append(it.model_dump())

    # 2. Open-Meteo Provider (empirical real observations fallback)
    if lat is not None and lon is not None:
        om = OpenMeteoProvider()
        om_items = await om.get_observations(
            latitude=lat,
            longitude=lon,
            target_time=target_time
        )
        for it in om_items:
            evidence_list.append(it.model_dump())

    state["evidence_items"] = evidence_list
    return state


async def node_retrieve_official_bulletins(state: InvestigationState) -> InvestigationState:
    lat = state.get("latitude")
    lon = state.get("longitude")
    imd = IMDProvider()
    warning_items = await imd.get_warnings(latitude=lat or 0.0, longitude=lon or 0.0)
    for w in warning_items:
        state["evidence_items"].append(w.model_dump())
    return state


async def node_match_evidence(state: InvestigationState) -> InvestigationState:
    claims = [ClaimItem(**c) for c in state["claims"]]
    evidence_items = [EvidenceItemSchema(**e) for e in state["evidence_items"]]
    lat = state.get("latitude")
    lon = state.get("longitude")

    assessments: List[EvidenceAssessmentSchema] = []
    for c in claims:
        for e in evidence_items:
            assessment = VerificationEngine.match_evidence_to_claim(
                claim=c,
                evidence=e,
                report_lat=lat,
                report_lon=lon
            )
            assessments.append(assessment)

    state["assessments"] = [a.model_dump() for a in assessments]
    return state


async def node_decide_or_review(state: InvestigationState) -> InvestigationState:
    claims = [ClaimItem(**c) for c in state["claims"]]
    evidence_items = [EvidenceItemSchema(**e) for e in state["evidence_items"]]
    assessments = [EvidenceAssessmentSchema(**a) for a in state["assessments"]]

    (
        overall_status,
        per_claim_status,
        rationale,
        supporting_ids,
        contradicting_ids,
        unresolved,
        limits,
        review_req
    ) = VerificationEngine.synthesize_decision(
        investigation_id=state["investigation_id"],
        claims=claims,
        evidence_items=evidence_items,
        assessments=assessments
    )

    state["overall_status"] = overall_status.value
    state["per_claim_status"] = {k: v.value for k, v in per_claim_status.items()}
    state["rationale"] = rationale
    state["supporting_evidence_ids"] = supporting_ids
    state["contradicting_evidence_ids"] = contradicting_ids
    for u in unresolved:
        if u not in state["unresolved_questions"]:
            state["unresolved_questions"].append(u)
    for l in limits:
        if l not in state["limitations"]:
            state["limitations"].append(l)
    state["review_required"] = review_req

    return state


def build_investigation_graph():
    graph = StateGraph(InvestigationState)

    graph.add_node("validate_report", node_validate_report)
    graph.add_node("extract_claims", node_extract_claims)
    graph.add_node("resolve_location_and_time", node_resolve_location_and_time)
    graph.add_node("plan_investigation", node_plan_investigation)
    graph.add_node("retrieve_weather_observations", node_retrieve_weather_observations)
    graph.add_node("retrieve_official_bulletins", node_retrieve_official_bulletins)
    graph.add_node("match_evidence", node_match_evidence)
    graph.add_node("decide_or_review", node_decide_or_review)

    graph.set_entry_point("validate_report")
    graph.add_edge("validate_report", "extract_claims")
    graph.add_edge("extract_claims", "resolve_location_and_time")
    graph.add_edge("resolve_location_and_time", "plan_investigation")
    graph.add_edge("plan_investigation", "retrieve_weather_observations")
    graph.add_edge("retrieve_weather_observations", "retrieve_official_bulletins")
    graph.add_edge("retrieve_official_bulletins", "match_evidence")
    graph.add_edge("match_evidence", "decide_or_review")
    graph.add_edge("decide_or_review", END)

    return graph.compile()


investigation_graph = build_investigation_graph()


async def run_investigation_workflow(report_id: str, db: AsyncSession) -> InvestigationModel:
    stmt = select(ReportModel).where(ReportModel.id == report_id)
    result = await db.execute(stmt)
    report = result.scalars().first()
    if not report:
        raise ValueError(f"Report {report_id} not found")

    investigation = InvestigationModel(
        report_id=report_id,
        status=ReportStatus.INVESTIGATING
    )
    db.add(investigation)
    await db.commit()
    await db.refresh(investigation)

    initial_state: InvestigationState = {
        "report_id": report.id,
        "investigation_id": investigation.id,
        "original_text": report.original_text,
        "place_text": report.place_text,
        "event_time": report.event_time,
        "latitude": report.latitude,
        "longitude": report.longitude,
        "claims": [],
        "evidence_items": [],
        "assessments": [],
        "overall_status": None,
        "per_claim_status": {},
        "rationale": "",
        "supporting_evidence_ids": [],
        "contradicting_evidence_ids": [],
        "unresolved_questions": [],
        "limitations": [],
        "review_required": False,
        "iteration_count": 0,
        "should_retry": False
    }

    final_state = await investigation_graph.ainvoke(initial_state)

    # Persist claims to DB
    for c in final_state["claims"]:
        claim_model = ClaimModel(
            id=c["id"],
            report_id=report.id,
            claim_text=c["claim_text"],
            event_type=c["event_type"],
            normalized_location=c.get("normalized_location"),
            event_time_start=c.get("event_time_start"),
            event_time_end=c.get("event_time_end"),
            severity=c.get("severity"),
            ambiguities=c.get("ambiguities", []),
            extraction_model=c.get("extraction_model", "deterministic_rules"),
            extraction_version=c.get("extraction_version", "1.0")
        )
        db.add(claim_model)

    # Persist evidence items to DB
    for e in final_state["evidence_items"]:
        ev_model = EvidenceItemModel(
            id=e["id"],
            investigation_id=investigation.id,
            provider_name=e["provider_name"],
            source_url=e.get("source_url"),
            evidence_type=e["evidence_type"],
            published_at=e.get("published_at"),
            observed_at=e.get("observed_at"),
            valid_from=e.get("valid_from"),
            valid_to=e.get("valid_to"),
            retrieved_at=e.get("retrieved_at", datetime.now(timezone.utc)),
            latitude=e.get("latitude"),
            longitude=e.get("longitude"),
            coverage_area=e.get("coverage_area"),
            raw_value=e.get("raw_value"),
            unit=e.get("unit"),
            summary=e.get("summary"),
            raw_payload_reference=e.get("raw_payload_reference"),
            data_quality_notes=e.get("data_quality_notes"),
            retrieval_status=e.get("retrieval_status", "SUCCESS")
        )
        db.add(ev_model)

    # Persist assessments
    for a in final_state["assessments"]:
        ass_model = EvidenceAssessmentModel(
            id=a["id"],
            claim_id=a["claim_id"],
            evidence_id=a["evidence_id"],
            rel_type=a["relationship"],
            geographic_relevance=a["geographic_relevance"],
            temporal_relevance=a["temporal_relevance"],
            event_match=a["event_match"],
            reason=a["reason"],
            assessment_method=a["assessment_method"]
        )
        db.add(ass_model)

    # Persist decision
    overall_status_val = VerificationStatus(final_state["overall_status"])
    decision_model = FinalDecisionModel(
        investigation_id=investigation.id,
        overall_status=overall_status_val,
        per_claim_status=final_state["per_claim_status"],
        rationale=final_state["rationale"],
        supporting_evidence_ids=final_state["supporting_evidence_ids"],
        contradicting_evidence_ids=final_state["contradicting_evidence_ids"],
        unresolved_questions=final_state["unresolved_questions"],
        limitations=final_state["limitations"],
        review_required=final_state["review_required"]
    )
    db.add(decision_model)

    investigation.overall_status = overall_status_val
    investigation.status = ReportStatus.NEEDS_REVIEW if final_state["review_required"] else ReportStatus.COMPLETED
    investigation.completed_at = datetime.now(timezone.utc)
    report.status = investigation.status

    await db.commit()
    await db.refresh(investigation)
    return investigation
