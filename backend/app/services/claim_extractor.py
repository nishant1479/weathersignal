import re
import uuid
from typing import List, Tuple, Optional
from datetime import datetime
from backend.app.schemas.schemas import ClaimItem


class ClaimExtractor:
    """
    Decomposes user weather reports into structured, testable claims.
    Supports deterministic extraction with zero external API dependencies,
    as well as LLM-assisted extraction when configured.
    """

    RAIN_KEYWORDS = ["rain", "heavy rain", "downpour", "rainfall", "shower", "cloudburst", "drizzle"]
    FLOOD_KEYWORDS = ["flood", "flooding", "waterlogging", "submerged", "water logged", "inundated", "deluge"]
    HEAT_KEYWORDS = ["heatwave", "heat wave", "extreme heat", "scorching", "hot"]
    WIND_KEYWORDS = ["cyclone", "storm", "gale", "strong wind", "thunderstorm", "gusts"]

    @classmethod
    def extract_deterministic(
        cls,
        report_id: str,
        text: str,
        default_place: Optional[str] = None,
        default_time: Optional[datetime] = None
    ) -> List[ClaimItem]:
        claims: List[ClaimItem] = []
        lower = text.lower()

        # Check rainfall claims
        has_rain = any(k in lower for k in cls.RAIN_KEYWORDS)
        if has_rain:
            severity = "heavy" if ("heavy" in lower or "cloudburst" in lower or "downpour" in lower) else "moderate"
            claims.append(
                ClaimItem(
                    id=str(uuid.uuid4()),
                    report_id=report_id,
                    claim_text="Rainfall occurred in the reported area",
                    event_type="rainfall",
                    normalized_location=default_place,
                    event_time_start=default_time,
                    event_time_end=default_time,
                    severity=severity,
                    ambiguities=[] if default_place else ["Location not specifically stated"],
                    extraction_model="deterministic_rules",
                    extraction_version="1.0"
                )
            )

        # Check flooding/waterlogging claims
        has_flood = any(k in lower for k in cls.FLOOD_KEYWORDS)
        if has_flood:
            claims.append(
                ClaimItem(
                    id=str(uuid.uuid4()),
                    report_id=report_id,
                    claim_text="Waterlogging / Flooding occurred at ground level",
                    event_type="flooding",
                    normalized_location=default_place,
                    event_time_start=default_time,
                    event_time_end=default_time,
                    severity="severe" if "submerged" in lower else "moderate",
                    ambiguities=["Flooding requires distinct ground evidence beyond rainfall measurements"],
                    extraction_model="deterministic_rules",
                    extraction_version="1.0"
                )
            )

        # Check heatwave claims
        has_heat = any(k in lower for k in cls.HEAT_KEYWORDS)
        if has_heat:
            claims.append(
                ClaimItem(
                    id=str(uuid.uuid4()),
                    report_id=report_id,
                    claim_text="Abnormally high temperatures or heatwave conditions occurred",
                    event_type="heatwave",
                    normalized_location=default_place,
                    event_time_start=default_time,
                    event_time_end=default_time,
                    severity="high",
                    ambiguities=[] if default_place else ["Location unspecified"],
                    extraction_model="deterministic_rules",
                    extraction_version="1.0"
                )
            )

        # Check wind/cyclone claims
        has_wind = any(k in lower for k in cls.WIND_KEYWORDS)
        if has_wind:
            claims.append(
                ClaimItem(
                    id=str(uuid.uuid4()),
                    report_id=report_id,
                    claim_text="High wind or severe thunderstorm activity occurred",
                    event_type="wind_storm",
                    normalized_location=default_place,
                    event_time_start=default_time,
                    event_time_end=default_time,
                    severity="high" if "cyclone" in lower else "moderate",
                    ambiguities=[] if default_place else ["Location unspecified"],
                    extraction_model="deterministic_rules",
                    extraction_version="1.0"
                )
            )

        # Fallback if no specific weather keyword matches
        if not claims:
            claims.append(
                ClaimItem(
                    id=str(uuid.uuid4()),
                    report_id=report_id,
                    claim_text=text[:200],
                    event_type="general_weather",
                    normalized_location=default_place,
                    event_time_start=default_time,
                    event_time_end=default_time,
                    severity="unknown",
                    ambiguities=["Event type not categorized by automated keywords"],
                    extraction_model="deterministic_rules",
                    extraction_version="1.0"
                )
            )

        return claims
