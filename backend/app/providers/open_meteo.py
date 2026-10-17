import uuid
import httpx
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from backend.app.core.config import settings
from backend.app.schemas.schemas import EvidenceItemSchema, EvidenceType
from backend.app.providers.base import WeatherProvider


class OpenMeteoProvider(WeatherProvider):
    """
    Open-Meteo Archive & Weather Observation Provider.
    Free, no-API-key required provider covering historical observations and current
    measurements across any latitude/longitude coordinates (including throughout India).
    Used as credible empirical weather observation corroborator.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        self._base_url = (base_url or settings.OPEN_METEO_BASE_URL).rstrip("/")
        self._timeout = timeout or settings.OPEN_METEO_TIMEOUT_SECONDS

    @property
    def provider_name(self) -> str:
        return "Open-Meteo Weather Observation Archive"

    async def is_healthy(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                url = f"{self._base_url}?latitude=28.61&longitude=77.20&start_date=2024-01-01&end_date=2024-01-01&hourly=temperature_2m"
                resp = await client.get(url)
                return resp.status_code == 200
        except Exception:
            return False

    async def get_observations(
        self,
        latitude: float,
        longitude: float,
        target_time: Optional[datetime] = None,
        district_id: Optional[str] = None
    ) -> List[EvidenceItemSchema]:
        now = datetime.now(timezone.utc)
        target = target_time or now
        date_str = target.strftime("%Y-%m-%d")

        url = (
            f"{self._base_url}?latitude={latitude}&longitude={longitude}"
            f"&start_date={date_str}&end_date={date_str}"
            f"&hourly=rain,precipitation,temperature_2m,windspeed_10m"
        )

        items: List[EvidenceItemSchema] = []

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    hourly = data.get("hourly", {})
                    times = hourly.get("time", [])
                    rains = hourly.get("rain", [])
                    precips = hourly.get("precipitation", [])
                    temps = hourly.get("temperature_2m", [])
                    winds = hourly.get("windspeed_10m", [])

                    # Find nearest hour
                    target_hour_str = target.strftime("%Y-%m-%dT%H:00")
                    idx = 0
                    if target_hour_str in times:
                        idx = times.index(target_hour_str)
                    elif times:
                        idx = min(len(times) - 1, target.hour)

                    rain_val = rains[idx] if idx < len(rains) else 0.0
                    precip_val = precips[idx] if idx < len(precips) else 0.0
                    temp_val = temps[idx] if idx < len(temps) else None
                    wind_val = winds[idx] if idx < len(winds) else None
                    time_matched = times[idx] if idx < len(times) else date_str

                    obs_dt = None
                    try:
                        obs_dt = datetime.fromisoformat(time_matched).replace(tzinfo=timezone.utc)
                    except Exception:
                        obs_dt = target

                    items.append(
                        EvidenceItemSchema(
                            id=str(uuid.uuid4()),
                            provider_name=self.provider_name,
                            source_url=url,
                            evidence_type=EvidenceType.OBSERVATION,
                            published_at=obs_dt,
                            observed_at=obs_dt,
                            retrieved_at=now,
                            latitude=latitude,
                            longitude=longitude,
                            coverage_area=f"Lat {latitude:.4f}, Lon {longitude:.4f}",
                            raw_value=f"Rain: {rain_val}mm, Precip: {precip_val}mm, Temp: {temp_val}°C, Wind: {wind_val}km/h",
                            unit="mm",
                            summary=(
                                f"Observed precipitation at {time_matched}: {precip_val} mm "
                                f"(Rain: {rain_val} mm, Temp: {temp_val}°C, Wind: {wind_val} km/h)"
                            ),
                            data_quality_notes="Real-world station/reanalysis empirical observation record",
                            retrieval_status="SUCCESS"
                        )
                    )
                else:
                    items.append(
                        EvidenceItemSchema(
                            id=str(uuid.uuid4()),
                            provider_name=self.provider_name,
                            source_url=url,
                            evidence_type=EvidenceType.OBSERVATION,
                            retrieved_at=now,
                            latitude=latitude,
                            longitude=longitude,
                            summary=f"Open-Meteo observation query returned HTTP {resp.status_code}",
                            data_quality_notes=f"HTTP_ERROR: {resp.status_code}",
                            retrieval_status="FAILED"
                        )
                    )
        except Exception as e:
            items.append(
                EvidenceItemSchema(
                    id=str(uuid.uuid4()),
                    provider_name=self.provider_name,
                    source_url=url,
                    evidence_type=EvidenceType.OBSERVATION,
                    retrieved_at=now,
                    latitude=latitude,
                    longitude=longitude,
                    summary=f"Failed to retrieve observations: {str(e)}",
                    data_quality_notes="NETWORK_TIMEOUT_OR_CONNECTION_ERROR",
                    retrieval_status="ERROR"
                )
            )

        return items

    async def get_warnings(
        self,
        latitude: float,
        longitude: float,
        district_id: Optional[str] = None
    ) -> List[EvidenceItemSchema]:
        # Open-Meteo archive does not issue civil emergency warnings
        return []
