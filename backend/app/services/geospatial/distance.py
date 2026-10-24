"""Geospatial utilities using haversine distance (PostGIS fallback for SQLite)."""
import math
from typing import Optional


EARTH_RADIUS_M = 6_371_000.0


def haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """
    Calculate the great-circle distance between two points in meters.
    Uses the haversine formula.
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return EARTH_RADIUS_M * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def validate_coordinates(lat: Optional[float], lon: Optional[float]) -> bool:
    """Return True if latitude and longitude are within valid ranges."""
    if lat is None or lon is None:
        return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def coordinates_within_radius(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    radius_meters: float,
) -> bool:
    return haversine_distance(lat1, lon1, lat2, lon2) <= radius_meters
