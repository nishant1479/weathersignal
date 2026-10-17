import uuid
import httpx
from datetime import datetime, timezone
from typing import List, Optional
from backend.app.core.config import settings
from backend.app.schemas.schemas import EvidenceItemSchema, EvidenceType
from backend.app.providers.base import WeatherProvider


class IMDProvider(WeatherProvider):
    """
    India Meteorological Department (IMD) API Client.
    Official portal: https://api.imd.gov.in/public/index.php
    Official API Reference: https://api.imd.gov.in/public/api_reference.html

    Endpoints used:
    - /districtwarning?id={id}
    - /districtrainfall?id={id}
    - /districtnowcast?id={id}
    - /aws_data?id={id}
    - /stationnowcast?id={id}

    Authentication:
    Requires 'x-api-key' or controlled registered key. If unconfigured or missing,
    the provider honestly reports NOT_CONFIGURED and abstains, never faking data.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        self._base_url = (base_url or settings.IMD_API_BASE_URL).rstrip("/")
        self._api_key = api_key if api_key is not None else settings.IMD_API_KEY
        self._timeout = timeout or settings.IMD_TIMEOUT_SECONDS

    @property
    def provider_name(self) -> str:
        return "India Meteorological Department (IMD)"

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    async def is_healthy(self) -> bool:
        if not self.is_configured:
            return False
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                headers = {"x-api-key": self._api_key}
                resp = await client.get(f"{self._base_url}/districtwarning?id=573", headers=headers)
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
        """
        Retrieves real observations from IMD endpoints if configured.
        Returns explicit UNVERIFIED/NOT_CONFIGURED item if key is not configured.
        """
        now = datetime.now(timezone.utc)
        if not self.is_configured:
            return [
                EvidenceItemSchema(
                    id=str(uuid.uuid4()),
                    provider_name=self.provider_name,
                    source_url=f"{self._base_url}/districtrainfall",
                    evidence_type=EvidenceType.OBSERVATION,
                    retrieved_at=now,
                    latitude=latitude,
                    longitude=longitude,
                    summary="IMD provider is not configured with an API key. Operating in documented limited mode.",
                    data_quality_notes="MISSING_CREDENTIALS: Registration at api.imd.gov.in required.",
                    retrieval_status="NOT_CONFIGURED"
                )
            ]

        items: List[EvidenceItemSchema] = []
        target_id = district_id or "164"  # Default sample or resolved district ID
        url = f"{self._base_url}/districtrainfall?id={target_id}"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                headers = {"x-api-key": self._api_key}
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    # Example payload fields from official reference:
                    # {"OBJ_ID": "164", "District": "ADILABAD", "Date": "2023-01-31", "Daily Actual": "0.00", "Daily Normal": "0.10"}
                    daily_actual = data.get("Daily Actual", "0.0")
                    district_name = data.get("District", "Unknown")
                    date_str = data.get("Date")

                    observed_dt = None
                    if date_str:
                        try:
                            observed_dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                        except Exception:
                            observed_dt = None

                    items.append(
                        EvidenceItemSchema(
                            id=str(uuid.uuid4()),
                            provider_name=self.provider_name,
                            source_url=url,
                            evidence_type=EvidenceType.OBSERVATION,
                            published_at=observed_dt,
                            observed_at=observed_dt,
                            retrieved_at=now,
                            coverage_area=f"District: {district_name}",
                            raw_value=str(daily_actual),
                            unit="mm",
                            summary=f"IMD Daily Actual Rainfall for {district_name}: {daily_actual} mm",
                            data_quality_notes="Official IMD daily district rainfall measurement",
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
                            summary=f"IMD API returned HTTP {resp.status_code}: {resp.text[:200]}",
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
                    summary=f"IMD connection error: {str(e)}",
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
        now = datetime.now(timezone.utc)
        if not self.is_configured:
            return [
                EvidenceItemSchema(
                    id=str(uuid.uuid4()),
                    provider_name=self.provider_name,
                    source_url=f"{self._base_url}/districtwarning",
                    evidence_type=EvidenceType.WARNING,
                    retrieved_at=now,
                    latitude=latitude,
                    longitude=longitude,
                    summary="IMD warning endpoint not queried: API key not configured.",
                    data_quality_notes="MISSING_CREDENTIALS",
                    retrieval_status="NOT_CONFIGURED"
                )
            ]

        target_id = district_id or "573"
        url = f"{self._base_url}/districtwarning?id={target_id}"
        items: List[EvidenceItemSchema] = []

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                headers = {"x-api-key": self._api_key}
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    items.append(
                        EvidenceItemSchema(
                            id=str(uuid.uuid4()),
                            provider_name=self.provider_name,
                            source_url=url,
                            evidence_type=EvidenceType.WARNING,
                            retrieved_at=now,
                            summary=f"IMD District Warning for ID {target_id}: {str(data)[:200]}",
                            data_quality_notes="Official IMD district warning bulletin",
                            retrieval_status="SUCCESS"
                        )
                    )
                else:
                    items.append(
                        EvidenceItemSchema(
                            id=str(uuid.uuid4()),
                            provider_name=self.provider_name,
                            source_url=url,
                            evidence_type=EvidenceType.WARNING,
                            retrieved_at=now,
                            summary=f"IMD API warning returned HTTP {resp.status_code}",
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
                    evidence_type=EvidenceType.WARNING,
                    retrieved_at=now,
                    summary=f"IMD warning connection error: {str(e)}",
                    data_quality_notes="NETWORK_TIMEOUT_OR_CONNECTION_ERROR",
                    retrieval_status="ERROR"
                )
            )

        return items
