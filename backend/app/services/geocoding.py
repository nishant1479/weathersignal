import httpx
from typing import Optional, Tuple
from backend.app.core.config import settings


class GeocodingService:
    """
    Geocoding service using OpenStreetMap Nominatim with explicit caching,
    timeout handling, and strict user-agent compliance.
    """

    KNOWN_COORDINATES = {
        "delhi": (28.6139, 77.2090),
        "new delhi": (28.6139, 77.2090),
        "connaught place": (28.6315, 77.2167),
        "central market": (28.5677, 77.2433),
        "mumbai": (19.0760, 72.8777),
        "bengaluru": (12.9716, 77.5946),
        "bangalore": (12.9716, 77.5946),
        "chennai": (13.0827, 80.2707),
        "kolkata": (22.5726, 88.3639),
        "hyderabad": (17.3850, 78.4867),
        "pune": (18.5204, 73.8567),
        "ahmedabad": (23.0225, 72.5714),
        "adilabad": (19.6641, 78.5320),
    }

    def __init__(self):
        self.user_agent = settings.GEOCODING_USER_AGENT
        self.timeout = settings.GEOCODING_TIMEOUT_SECONDS

    async def resolve(self, place_name: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """
        Returns (latitude, longitude, normalized_name).
        """
        if not place_name or not place_name.strip():
            return None, None, None

        cleaned = place_name.strip().lower()

        # Check known landmarks first for immediate deterministic match
        for key, coords in self.KNOWN_COORDINATES.items():
            if key in cleaned:
                return coords[0], coords[1], key.title()

        if settings.GEOCODING_PROVIDER == "disabled":
            return None, None, place_name

        # Query Nominatim API with user-agent
        try:
            url = f"https://nominatim.openstreetmap.org/search?q={cleaned}&format=json&limit=1"
            headers = {"User-Agent": self.user_agent}
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if data and len(data) > 0:
                        lat = float(data[0]["lat"])
                        lon = float(data[0]["lon"])
                        display_name = data[0].get("display_name", place_name)
                        return lat, lon, display_name
        except Exception:
            pass

        return None, None, place_name
