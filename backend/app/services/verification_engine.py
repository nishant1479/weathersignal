import uuid
import re
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timezone
from backend.app.schemas.schemas import (
    ClaimItem, EvidenceItemSchema, EvidenceAssessmentSchema,
    EvidenceRelationship, VerificationStatus, EvidenceType, AssessmentMethod
)
from backend.app.services.geo_temporal import evaluate_geographic_relevance, evaluate_temporal_relevance


class VerificationEngine:
    """
    Applies deterministic, non-negotiable verification rules:
    - Forecast alone cannot establish that an event occurred.
    - Warning alone cannot prove that a reported impact occurred.
    - Missing observation is NOT contradictory evidence.
    - Readings outside relevant time windows cannot confirm events.
    - Supported rainfall + unsupported flooding = PARTIALLY_CORROBORATED or UNVERIFIED (never fully CORROBORATED).
    - If providers fail or abstain, return honest UNVERIFIED or NEEDS_REVIEW.
    """

    @classmethod
    def match_evidence_to_claim(
        cls,
        claim: ClaimItem,
        evidence: EvidenceItemSchema,
        report_lat: Optional[float],
        report_lon: Optional[float]
    ) -> EvidenceAssessmentSchema:
        geo_rel = evaluate_geographic_relevance(
            report_lat, report_lon,
            evidence.latitude, evidence.longitude
        )
        temp_rel = evaluate_temporal_relevance(
            claim.event_time_start, evidence.observed_at or evidence.published_at
        )

        relationship = EvidenceRelationship.UNKNOWN
        event_match = False
        reason = ""

        # Check provider failure or unconfigured state
        if evidence.retrieval_status in ["NOT_CONFIGURED", "FAILED", "ERROR"]:
            return EvidenceAssessmentSchema(
                id=str(uuid.uuid4()),
                claim_id=claim.id,
                evidence_id=evidence.id,
                relationship=EvidenceRelationship.UNKNOWN,
                geographic_relevance=geo_rel,
                temporal_relevance=temp_rel,
                event_match=False,
                reason=f"Source returned {evidence.retrieval_status}: {evidence.summary}",
                assessment_method=AssessmentMethod.DETERMINISTIC
            )

        # Non-negotiable rule: Forecast alone is not observation of an event happening
        if evidence.evidence_type == EvidenceType.FORECAST:
            return EvidenceAssessmentSchema(
                id=str(uuid.uuid4()),
                claim_id=claim.id,
                evidence_id=evidence.id,
                relationship=EvidenceRelationship.CONTEXT_ONLY,
                geographic_relevance=geo_rel,
                temporal_relevance=temp_rel,
                event_match=True,
                reason="Forecast indicates anticipated conditions, but does not confirm physical occurrence.",
                assessment_method=AssessmentMethod.DETERMINISTIC
            )

        # Rule: Warning indicates meteorological hazard/risk, but not direct ground damage
        if evidence.evidence_type == EvidenceType.WARNING:
            if claim.event_type in ["rainfall", "wind_storm", "heatwave"]:
                relationship = EvidenceRelationship.SUPPORTS if (geo_rel > 0.3 and temp_rel > 0.3) else EvidenceRelationship.CONTEXT_ONLY
                reason = "Official warning issued for this meteorological hazard in the region."
            else:
                relationship = EvidenceRelationship.CONTEXT_ONLY
                reason = "Civil warning establishes regional risk, but cannot verify localized ground impact."
            return EvidenceAssessmentSchema(
                id=str(uuid.uuid4()),
                claim_id=claim.id,
                evidence_id=evidence.id,
                relationship=relationship,
                geographic_relevance=geo_rel,
                temporal_relevance=temp_rel,
                event_match=True,
                reason=reason,
                assessment_method=AssessmentMethod.DETERMINISTIC
            )

        # Rule: Empirical Observation
        if evidence.evidence_type == EvidenceType.OBSERVATION:
            raw_str = (evidence.raw_value or "").lower()
            summary_str = (evidence.summary or "").lower()

            # Rainfall check
            if claim.event_type == "rainfall":
                event_match = True
                # Extract numeric rain or precip
                precip_match = re.search(r"precip:\s*([0-9.]+)", raw_str) or re.search(r"actual rainfall:\s*([0-9.]+)", summary_str)
                rain_val = 0.0
                if precip_match:
                    try:
                        rain_val = float(precip_match.group(1))
                    except Exception:
                        rain_val = 0.0
                elif "rain:" in raw_str:
                    m = re.search(r"rain:\s*([0-9.]+)", raw_str)
                    if m:
                        rain_val = float(m.group(1))

                if geo_rel >= 0.3 and temp_rel >= 0.3:
                    if rain_val > 2.5:  # Measurable rainfall threshold
                        relationship = EvidenceRelationship.SUPPORTS
                        reason = f"Observation confirms measurable precipitation ({rain_val} mm) in relevant temporal/spatial window."
                    elif rain_val == 0.0 and geo_rel >= 0.7 and temp_rel >= 0.8:
                        relationship = EvidenceRelationship.CONTRADICTS
                        reason = "High-confidence nearby station observed 0.0 mm precipitation during the claimed window."
                    else:
                        relationship = EvidenceRelationship.CONTEXT_ONLY
                        reason = f"Recorded precipitation was minor ({rain_val} mm) or station spatial/temporal alignment is moderate."
                else:
                    relationship = EvidenceRelationship.IRRELEVANT
                    reason = "Observation outside required spatial or temporal radius."

            # Flooding check
            elif claim.event_type == "flooding":
                event_match = False
                # Atmospheric stations measure rain, not street ponding or drainage capacity
                relationship = EvidenceRelationship.CONTEXT_ONLY
                reason = "Weather station records atmospheric rain, which is a contributing factor, but not direct proof of ground flooding."

            # Heatwave check
            elif claim.event_type == "heatwave":
                event_match = True
                temp_match = re.search(r"temp:\s*([0-9.]+)", raw_str)
                temp_val = float(temp_match.group(1)) if temp_match else 0.0
                if geo_rel >= 0.3 and temp_rel >= 0.3:
                    if temp_val >= 40.0:
                        relationship = EvidenceRelationship.SUPPORTS
                        reason = f"Recorded temperature of {temp_val}°C indicates heatwave conditions."
                    elif temp_val < 32.0 and geo_rel >= 0.7:
                        relationship = EvidenceRelationship.CONTRADICTS
                        reason = f"Station recorded moderate temperature ({temp_val}°C), contradicting extreme heat."
                    else:
                        relationship = EvidenceRelationship.CONTEXT_ONLY
                        reason = f"Station recorded {temp_val}°C."
                else:
                    relationship = EvidenceRelationship.IRRELEVANT
                    reason = "Outside spatial or temporal proximity."

            # Wind storm check
            elif claim.event_type == "wind_storm":
                event_match = True
                wind_match = re.search(r"wind:\s*([0-9.]+)", raw_str)
                wind_val = float(wind_match.group(1)) if wind_match else 0.0
                if geo_rel >= 0.3 and temp_rel >= 0.3:
                    if wind_val >= 45.0:
                        relationship = EvidenceRelationship.SUPPORTS
                        reason = f"Recorded high wind speed ({wind_val} km/h) corroborates storm report."
                    else:
                        relationship = EvidenceRelationship.CONTEXT_ONLY
                        reason = f"Station recorded moderate wind speed ({wind_val} km/h)."
                else:
                    relationship = EvidenceRelationship.IRRELEVANT
                    reason = "Outside spatial or temporal proximity."

            else:
                relationship = EvidenceRelationship.CONTEXT_ONLY
                reason = "Observation provides general environmental context."

        return EvidenceAssessmentSchema(
            id=str(uuid.uuid4()),
            claim_id=claim.id,
            evidence_id=evidence.id,
            relationship=relationship,
            geographic_relevance=geo_rel,
            temporal_relevance=temp_rel,
            event_match=event_match,
            reason=reason,
            assessment_method=AssessmentMethod.DETERMINISTIC
        )

    @classmethod
    def synthesize_decision(
        cls,
        investigation_id: str,
        claims: List[ClaimItem],
        evidence_items: List[EvidenceItemSchema],
        assessments: List[EvidenceAssessmentSchema]
    ) -> Tuple[VerificationStatus, Dict[str, VerificationStatus], str, List[str], List[str], List[str], List[str], bool]:
        """
        Synthesizes overall and per-claim verification outcomes.
        Returns:
        (overall_status, per_claim_status, rationale, supporting_ids, contradicting_ids, unresolved_questions, limitations, review_required)
        """
        per_claim_status: Dict[str, VerificationStatus] = {}
        supporting_ids: List[str] = []
        contradicting_ids: List[str] = []
        unresolved_questions: List[str] = []
        limitations: List[str] = []
        review_required = False

        # Check for unconfigured / failed providers
        failed_or_missing = [e for e in evidence_items if e.retrieval_status in ["NOT_CONFIGURED", "FAILED", "ERROR"]]
        for f in failed_or_missing:
            limitations.append(f"Source '{f.provider_name}' status: {f.retrieval_status} ({f.summary})")

        successful_evidence = [e for e in evidence_items if e.retrieval_status == "SUCCESS"]

        for claim in claims:
            claim_assessments = [a for a in assessments if a.claim_id == claim.id]
            claim_supports = [a for a in claim_assessments if a.relationship == EvidenceRelationship.SUPPORTS]
            claim_contradicts = [a for a in claim_assessments if a.relationship == EvidenceRelationship.CONTRADICTS]

            for s in claim_supports:
                if s.evidence_id not in supporting_ids:
                    supporting_ids.append(s.evidence_id)
            for c in claim_contradicts:
                if c.evidence_id not in contradicting_ids:
                    contradicting_ids.append(c.evidence_id)

            if claim_contradicts:
                per_claim_status[claim.id] = VerificationStatus.CONTRADICTED
            elif claim_supports:
                per_claim_status[claim.id] = VerificationStatus.CORROBORATED
            else:
                per_claim_status[claim.id] = VerificationStatus.UNVERIFIED
                if claim.event_type == "flooding":
                    unresolved_questions.append(
                        f"Ground waterlogging/flooding for claim '{claim.claim_text}' cannot be verified solely from atmospheric precipitation sensors."
                    )
                else:
                    unresolved_questions.append(
                        f"Insufficient station or satellite observation data to verify '{claim.claim_text}'."
                    )

        statuses = list(per_claim_status.values())

        # Determine overall status
        if not successful_evidence:
            overall_status = VerificationStatus.UNVERIFIED
            rationale = "No successful weather observations were retrievable from configured providers. The report remains unverified."
        elif VerificationStatus.CONTRADICTED in statuses:
            if VerificationStatus.CORROBORATED in statuses:
                overall_status = VerificationStatus.NEEDS_REVIEW
                review_required = True
                rationale = "Material contradiction detected alongside corroborated claims. Human review required."
            else:
                overall_status = VerificationStatus.CONTRADICTED
                rationale = "Available reliable empirical observations contradict the reported event conditions."
        elif all(s == VerificationStatus.CORROBORATED for s in statuses):
            overall_status = VerificationStatus.CORROBORATED
            rationale = "All decomposed claims are corroborated by consistent, geographically and temporally relevant observations."
        elif VerificationStatus.CORROBORATED in statuses:
            overall_status = VerificationStatus.PARTIALLY_CORROBORATED
            rationale = (
                "Meteorological claims (such as rainfall) are corroborated by empirical records, "
                "but ground-level impacts (such as road flooding) lack independent sensor verification."
            )
        else:
            overall_status = VerificationStatus.UNVERIFIED
            rationale = "Available evidence is insufficient to verify the material claims."

        # High ambiguity or escalation rule
        for c in claims:
            if c.ambiguities:
                for amb in c.ambiguities:
                    if amb not in unresolved_questions:
                        unresolved_questions.append(amb)

        if len(claims) > 1 and overall_status == VerificationStatus.PARTIALLY_CORROBORATED:
            # If severe flooding or damage claimed, flag for review
            if any(c.event_type == "flooding" and c.severity == "severe" for c in claims):
                review_required = True
                overall_status = VerificationStatus.NEEDS_REVIEW
                rationale += " Flagged for human review due to severe reported impact."

        return (
            overall_status,
            per_claim_status,
            rationale,
            supporting_ids,
            contradicting_ids,
            unresolved_questions,
            limitations,
            review_required
        )
