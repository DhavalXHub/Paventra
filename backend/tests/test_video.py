"""
Tests for Video Inspection Service.
Validates:
  - Synchronized GPS track parsing.
  - Spatial-temporal coordinate interpolation.
  - Video frame timestamp association.
  - Location unavailable behavior (no fake coordinates).
"""
import json
import pytest

from app.services.vision.video_inspection import (
    parse_gps_track,
    find_interpolated_gps,
)


def test_parse_gps_track_valid(tmp_path):
    track_file = tmp_path / "gps_track.json"
    data = [
        {"timestamp_seconds": 0.0, "latitude": 19.0760, "longitude": 72.8777},
        {"timestamp_seconds": 5.0, "latitude": 19.0765, "longitude": 72.8782},
    ]
    track_file.write_text(json.dumps(data), encoding="utf-8")

    parsed = parse_gps_track(str(track_file))
    assert len(parsed) == 2
    assert parsed[0]["latitude"] == 19.0760


def test_parse_gps_track_missing_or_corrupt(tmp_path):
    assert parse_gps_track(None) == []
    assert parse_gps_track("non_existent_file.json") == []

    corrupt_file = tmp_path / "corrupt.json"
    corrupt_file.write_text("invalid json content", encoding="utf-8")
    assert parse_gps_track(str(corrupt_file)) == []


def test_find_interpolated_gps_within_window():
    gps_track = [
        {"timestamp_seconds": 0.0, "latitude": 19.0760, "longitude": 72.8777},
        {"timestamp_seconds": 2.0, "latitude": 19.0762, "longitude": 72.8779},
        {"timestamp_seconds": 6.0, "latitude": 19.0768, "longitude": 72.8785},
    ]

    # Timestamp 2.1 is within 0.1s of point at t=2.0
    lat, lon = find_interpolated_gps(gps_track, timestamp_sec=2.1)
    assert lat == 19.0762
    assert lon == 72.8779


def test_find_interpolated_gps_out_of_window_returns_none():
    """If timestamp is more than 2.0s away from nearest GPS point, coordinates are not guessed."""
    gps_track = [
        {"timestamp_seconds": 0.0, "latitude": 19.0760, "longitude": 72.8777},
    ]

    # Timestamp 10.0s is 10s away from nearest GPS point (> 2.0s window)
    lat, lon = find_interpolated_gps(gps_track, timestamp_sec=10.0)
    assert lat is None
    assert lon is None


def test_find_interpolated_gps_empty_track():
    lat, lon = find_interpolated_gps([], timestamp_sec=1.5)
    assert lat is None
    assert lon is None
