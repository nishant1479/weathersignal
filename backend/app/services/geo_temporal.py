import math
from datetime import datetime
from typing import Optional


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between two points on the Earth in kilometers.
    """
    R = 6371.0  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def evaluate_geographic_relevance(
    rep_lat: Optional[float],
    rep_lon: Optional[float],
    ev_lat: Optional[float],
    ev_lon: Optional[float],
    max_radius_km: float = 50.0
) -> float:
    """
    Returns a score from 0.0 (irrelevant) to 1.0 (exact location).
    """
    if rep_lat is None or rep_lon is None or ev_lat is None or ev_lon is None:
        return 0.5  # Neutral when coordinate is coarse or region-level

    dist = haversine_distance_km(rep_lat, rep_lon, ev_lat, ev_lon)
    if dist <= 5.0:
        return 1.0
    if dist >= max_radius_km:
        return 0.0
    # Linear decay between 5km and max_radius_km
    return max(0.0, 1.0 - ((dist - 5.0) / (max_radius_km - 5.0)))


def evaluate_temporal_relevance(
    target_time: Optional[datetime],
    observed_time: Optional[datetime],
    window_hours: float = 6.0
) -> float:
    """
    Returns 1.0 for same hour, decaying to 0.0 outside the temporal window.
    """
    if not target_time or not observed_time:
        return 0.5  # Neutral when timestamps are unspecified

    # Normalize tz
    t1 = target_time.timestamp()
    t2 = observed_time.timestamp()
    diff_hours = abs(t1 - t2) / 3600.0

    if diff_hours <= 1.0:
        return 1.0
    if diff_hours >= window_hours:
        return 0.0
    return max(0.0, 1.0 - (diff_hours / window_hours))
