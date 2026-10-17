import pytest
from datetime import datetime, timezone
from backend.app.schemas.schemas import ClaimItem, EvidenceItemSchema, EvidenceType, EvidenceRelationship, VerificationStatus
from backend.app.services.claim_extractor import ClaimExtractor
from backend.app.services.geo_temporal import haversine_distance_km, evaluate_geographic_relevance, evaluate_temporal_relevance
from backend.app.services.verification_engine import VerificationEngine


def test_haversine_distance():
    # Distance between New Delhi (28.6139, 77.2090) and Connaught Place (28.6315, 77.2167) ~2 km
    dist = haversine_distance_km(28.6139, 77.2090, 28.6315, 77.2167)
    assert 1.5 < dist < 3.0


def test_geographic_relevance_decay():
    # Co-located point
    rel_close = evaluate_geographic_relevance(28.6139, 77.2090, 28.6139, 77.2090, max_radius_km=50.0)
    assert rel_close == 1.0

    # Beyond max radius (> 50km)
    rel_far = evaluate_geographic_relevance(28.6139, 77.2090, 19.0760, 72.8777, max_radius_km=50.0)
    assert rel_far == 0.0


def test_temporal_relevance():
    t1 = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
    t2 = datetime(2024, 6, 1, 12, 30, tzinfo=timezone.utc)
    # Within 1 hour -> 1.0
    assert evaluate_temporal_relevance(t1, t2) == 1.0

    # 12 hours later -> 0.0 (beyond 6 hr window)
    t3 = datetime(2024, 6, 2, 0, 0, tzinfo=timezone.utc)
    assert evaluate_temporal_relevance(t1, t3) == 0.0


def test_claim_extraction_multiclaim():
    text = "Heavy rain is flooding roads near the central market at 4:30 PM."
    claims = ClaimExtractor.extract_deterministic(
        report_id="rep-1",
        text=text,
        default_place="central market"
    )
    # Should extract both rainfall and flooding claims separately
    types = [c.event_type for c in claims]
    assert "rainfall" in types
    assert "flooding" in types


def test_verification_rule_forecast_is_not_observation():
    claim = ClaimItem(
        id="c1",
        report_id="rep-1",
        claim_text="Rainfall occurred",
        event_type="rainfall"
    )
    forecast_evidence = EvidenceItemSchema(
        id="e1",
        provider_name="Test Provider",
        evidence_type=EvidenceType.FORECAST,
        retrieved_at=datetime.now(timezone.utc),
        summary="Rain predicted for tomorrow",
        raw_value="15mm"
    )
    assessment = VerificationEngine.match_evidence_to_claim(
        claim=claim,
        evidence=forecast_evidence,
        report_lat=28.6,
        report_lon=77.2
    )
    # Non-negotiable rule: forecast cannot directly support physical occurrence claim
    assert assessment.relationship == EvidenceRelationship.CONTEXT_ONLY


def test_supported_rain_and_unsupported_flooding_partial_corroboration():
    # If rainfall is observed but street flooding has no sensor proof, status must NOT be full CORROBORATED
    claim_rain = ClaimItem(id="c_rain", report_id="rep-1", claim_text="Rainfall occurred", event_type="rainfall")
    claim_flood = ClaimItem(id="c_flood", report_id="rep-1", claim_text="Streets flooded", event_type="flooding")

    ev_rain = EvidenceItemSchema(
        id="e_rain",
        provider_name="Observation Station",
        evidence_type=EvidenceType.OBSERVATION,
        retrieved_at=datetime.now(timezone.utc),
        latitude=28.61,
        longitude=77.20,
        raw_value="precip: 25.0 mm",
        summary="Observed 25mm rain"
    )

    now = datetime.now(timezone.utc)
    ass_rain = VerificationEngine.match_evidence_to_claim(claim_rain, ev_rain, 28.61, 77.20)
    ass_flood = VerificationEngine.match_evidence_to_claim(claim_flood, ev_rain, 28.61, 77.20)

    overall, per_claim, rationale, supp, cont, unres, lim, rev = VerificationEngine.synthesize_decision(
        investigation_id="inv-1",
        claims=[claim_rain, claim_flood],
        evidence_items=[ev_rain],
        assessments=[ass_rain, ass_flood]
    )

    assert per_claim["c_rain"] == VerificationStatus.CORROBORATED
    assert per_claim["c_flood"] == VerificationStatus.UNVERIFIED
    assert overall in [VerificationStatus.PARTIALLY_CORROBORATED, VerificationStatus.NEEDS_REVIEW]
    assert overall != VerificationStatus.CORROBORATED
