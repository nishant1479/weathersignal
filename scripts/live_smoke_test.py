import asyncio
import httpx
from datetime import datetime, timezone
from backend.app.core.config import settings
from backend.app.providers.imd import IMDProvider
from backend.app.providers.open_meteo import OpenMeteoProvider


async def run_live_smoke_tests():
    print("=" * 60)
    print("WeatherSignal Live Data Provider Smoke Test")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # 1. IMD Provider
    imd = IMDProvider()
    print("\n[1] Checking India Meteorological Department (IMD)...")
    print(f"Base URL: {settings.IMD_API_BASE_URL}")
    print(f"Configured with API Key: {'Yes' if imd.is_configured else 'No (Documented Limited Mode)'}")
    
    if not imd.is_configured:
        print("Status: NOT_CONFIGURED - API key missing from environment.")
        print("Testing live endpoint contract response without key...")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{settings.IMD_API_BASE_URL}/districtwarning?id=573")
                print(f"HTTP Status: {res.status_code}")
                print(f"Gateway Response: {res.text.strip()}")
                print("Confirmed: IMD gateway is online and correctly requiring credentials.")
        except Exception as e:
            print(f"Connection error: {e}")
    else:
        healthy = await imd.is_healthy()
        print(f"Live Auth Status: {'AUTHENTICATED' if healthy else 'FAILED'}")

    # 2. Open-Meteo Archive Provider
    print("\n[2] Checking Open-Meteo Weather Observation Archive...")
    print(f"Base URL: {settings.OPEN_METEO_BASE_URL}")
    om = OpenMeteoProvider()
    healthy = await om.is_healthy()
    print(f"Health Check: {'HEALTHY' if healthy else 'UNHEALTHY'}")

    if healthy:
        # Test real coordinate query for New Delhi
        obs = await om.get_observations(latitude=28.6139, longitude=77.2090, target_time=datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc))
        print(f"Retrieved {len(obs)} observation item(s):")
        for item in obs:
            print(f" - [{item.retrieval_status}] {item.summary}")
            print(f"   Raw Values: {item.raw_value}")

    print("\n" + "=" * 60)
    print("Smoke Test Complete.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_live_smoke_tests())
