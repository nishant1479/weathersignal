import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.core.database import init_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await init_db()


@pytest.mark.asyncio
async def test_health_and_ready_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res_health = await ac.get("/health")
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "healthy"

        res_ready = await ac.get("/ready")
        assert res_ready.status_code == 200
        data = res_ready.json()
        assert data["database"] == "connected"
        assert "providers" in data


@pytest.mark.asyncio
async def test_submit_report_and_investigate_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Submit report
        report_payload = {
            "original_text": "Heavy rain is flooding roads near the central market at 4:30 PM.",
            "place_text": "central market",
            "latitude": 28.5677,
            "longitude": 77.2433
        }
        res_sub = await ac.post("/api/v1/reports", json=report_payload)
        assert res_sub.status_code == 201
        report = res_sub.json()
        report_id = report["id"]
        assert report["status"] == "PENDING"

        # 2. Trigger investigation workflow
        res_inv = await ac.post(f"/api/v1/reports/{report_id}/investigate")
        assert res_inv.status_code == 200
        inv_data = res_inv.json()
        inv_id = inv_data["investigation_id"]

        # 3. Retrieve investigation detail
        res_detail = await ac.get(f"/api/v1/investigations/{inv_id}")
        assert res_detail.status_code == 200
        detail = res_detail.json()
        assert len(detail["claims"]) >= 2
        assert detail["decision"] is not None
        assert detail["decision"]["overall_status"] in ["PARTIALLY_CORROBORATED", "UNVERIFIED", "CORROBORATED", "NEEDS_REVIEW"]

        # 4. Check evidence
        res_ev = await ac.get(f"/api/v1/investigations/{inv_id}/evidence")
        assert res_ev.status_code == 200
        ev_data = res_ev.json()
        assert ev_data["evidence_count"] >= 1
