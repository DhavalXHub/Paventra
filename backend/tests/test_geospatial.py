"""Unit tests for geospatial services and coordinate validation."""
from app.services.geospatial.distance import (
    haversine_distance, validate_coordinates, coordinates_within_radius
)


def test_validate_coordinates():
    assert validate_coordinates(28.6139, 77.2090) is True
    assert validate_coordinates(-90.0, 180.0) is True
    assert validate_coordinates(91.0, 50.0) is False
    assert validate_coordinates(20.0, 181.0) is False
    assert validate_coordinates(None, 77.0) is False


def test_haversine_known_distance():
    # Delhi to Mumbai distance is ~1150 km
    delhi_lat, delhi_lon = 28.6139, 77.2090
    mumbai_lat, mumbai_lon = 19.0760, 72.8777
    dist_m = haversine_distance(delhi_lat, delhi_lon, mumbai_lat, mumbai_lon)
    # Check between 1100 km and 1200 km
    assert 1_100_000 <= dist_m <= 1_200_000


def test_coordinates_within_radius():
    # Same point: distance 0
    p1 = (19.0760, 72.8777)
    assert coordinates_within_radius(p1[0], p1[1], p1[0], p1[1], radius_meters=10.0) is True
    
    # Point ~100m away
    p2 = (19.0769, 72.8777)
    assert coordinates_within_radius(p1[0], p1[1], p2[0], p2[1], radius_meters=200.0) is True
    assert coordinates_within_radius(p1[0], p1[1], p2[0], p2[1], radius_meters=10.0) is False
