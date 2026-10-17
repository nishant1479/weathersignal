# Architecture of WeatherSignal

WeatherSignal is an agentic weather verification system built to audit and corroborate or contradict weather claims using verifiable real-world evidence.

```mermaid
flowchart TD
    UserReport["Incoming Report (API / Dashboard)"] --> ValidateReport["Node 1: validate_report"]
    ValidateReport --> ExtractClaims["Node 2: extract_claims (Decompose into testable subclaims)"]
    ExtractClaims --> ResolveLocation["Node 3: resolve_location_and_time (Nominatim / Geocoding)"]
    ResolveLocation --> Plan["Node 4: plan_investigation"]
    Plan --> QueryIMD["Node 5a: IMD Provider (Official Bulletins / Observations)"]
    Plan --> QueryOpenMeteo["Node 5b: Open-Meteo Provider (Empirical Station/Archive Data)"]
    QueryIMD --> MatchEvidence["Node 6: match_evidence (Deterministic Geo/Temporal Matching)"]
    QueryOpenMeteo --> MatchEvidence
    MatchEvidence --> DecideOrReview["Node 7: decide_or_review (Rule Guardrails)"]
    DecideOrReview --> PersistDecision["Persist Investigation & Audit Trail (SQLite/PostgreSQL)"]
    DecideOrReview --> HumanReviewQueue["Review Queue (If ambiguous or severe conflicts)"]
```

## Core Modules

1. **API Layer (`backend/app/main.py`)**:
   - Versioned REST endpoints under `/api/v1/`
   - Health and readiness endpoints (`/health`, `/ready`)
   - Human review actions with mandatory operational rationale.

2. **Data Model (`backend/app/models/models.py` & `schemas.py`)**:
   - Reports, decomposed Claims, Evidence Items, Assessments, and Final Decisions.

3. **Providers (`backend/app/providers/`)**:
   - `IMDProvider`: Official India Meteorological Department API client matching official contracts (`/districtwarning`, `/districtrainfall`, etc.). Requires `x-api-key`. Accurately reports `NOT_CONFIGURED` when key is absent.
   - `OpenMeteoProvider`: Empirical weather observation provider offering public, keyless observation data for any latitude/longitude in India and globally.

4. **Deterministic Engine (`backend/app/services/`)**:
   - Haversine great-circle distance evaluation and temporal decay windows.
   - Verification rules:
     - Forecast $\neq$ Observation.
     - Warning $\neq$ Ground Impact.
     - Supported rainfall + unverified flood = `PARTIALLY_CORROBORATED` (never false full corroboration).
