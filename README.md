# WeatherSignal --- Agentic Weather Verification System

WeatherSignal accepts weather-related reports and investigates whether the material claims are supported by credible, real-world evidence.

## System Overview

WeatherSignal is a **verification assistant**, not a weather forecasting portal and not an autonomous emergency authority.
- Separates compound reports into testable atomic claims (e.g., rainfall, flooding, heatwave, wind storm).
- Resolves location and time coordinates using OpenStreetMap Nominatim.
- Retrieves real observations and bulletins from configured providers:
  - **India Meteorological Department (IMD)**: Official Indian meteorological portal.
  - **Open-Meteo Weather Observation Archive**: Empirical weather measurements worldwide including across India.
- Evaluates evidence using deterministic Python guardrails (Haversine spatial distance, temporal decay, forecast-vs-observation separation).
- Persists all investigation states, claims, evidence items, and decisions to SQLite/PostgreSQL.
- Surfaces a responsive dashboard for report submission, timeline inspection, and human analyst reviews.

---

## Result Categories

- `CORROBORATED`: Relevant, reliable evidence supports the material claim(s).
- `CONTRADICTED`: Relevant, reliable evidence materially conflicts with a claim.
- `UNVERIFIED`: Available evidence is insufficient to decide.
- `NEEDS_REVIEW`: Ambiguity, major conflict, high impact, or unverified severe claims require human review.
- `PARTIALLY_CORROBORATED`: Some claims (e.g. rainfall) are supported, while others (e.g. ground road flooding) remain unverified.

---

## Quickstart & Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- Docker (optional)

### 1. Environment Setup

```bash
cp .env.example .env
```

### 2. Backend Setup & Run

```bash
# In project root
python3 -m venv venv
source venv/bin/activate
pip install -r <(cat << 'EOF'
fastapi
uvicorn[standard]
pydantic
pydantic-settings
sqlalchemy[asyncio]
aiosqlite
greenlet
httpx
langgraph
langchain
langchain-core
pytest
pytest-asyncio
EOF
)

# Start backend on http://localhost:8000
PYTHONPATH=. uvicorn backend.app.main:app --reload --port 8000
```

### 3. Frontend Setup & Run

```bash
cd frontend
npm install
npm run dev
# Dashboard available at http://localhost:5173
```

---

## Running Automated Tests

```bash
source venv/bin/activate
PYTHONPATH=. pytest -v backend/tests
```

### Running Live Provider Smoke Test

WeatherSignal includes an opt-in live provider smoke test:

```bash
source venv/bin/activate
PYTHONPATH=. python scripts/live_smoke_test.py
```

This verifies:
1. Live IMD gateway connectivity and credential requirement response (`401 API key missing`).
2. Open-Meteo live observation data query for coordinates.

---

## Docker Deployment

To build and start with Docker Compose:

```bash
docker compose up --build
```

---

## API Endpoints

- `GET /health` --- Application liveness check
- `GET /ready` --- Readiness status of database and weather providers
- `POST /api/v1/reports` --- Submit a new report
- `GET /api/v1/reports` --- List submitted reports
- `POST /api/v1/reports/{report_id}/investigate` --- Start LangGraph investigation workflow
- `GET /api/v1/investigations/{investigation_id}` --- Get investigation details and decision
- `GET /api/v1/investigations/{investigation_id}/evidence` --- Retrieve gathered evidence and claim assessments
- `GET /api/v1/review-queue` --- Cases requiring human analyst review
- `POST /api/v1/investigations/{investigation_id}/review` --- Record authorized human override/decision
- `GET /api/v1/providers/status` --- Health and configuration status of connected providers
