"""Geocoding module — maps FSA (Forward Sortation Area) codes to lat/lng.

Currently uses a static lookup table for the ~10 FSAs in Vancouver Granville.
To migrate to an API (e.g., Canada Post, OpenCage), replace the body of
geocode_fsa() and update geocode_record() if the API returns precise coords.
"""

import math

# Approximate centroid lat/lng for each FSA in Vancouver Granville
_FSA_CENTROIDS: dict[str, tuple[float, float]] = {
    "V6H": (49.2640, -123.1380),  # Fairview
    "V6J": (49.2660, -123.1480),  # Kitsilano East
    "V6L": (49.2500, -123.1620),  # Kerrisdale North
    "V6M": (49.2380, -123.1550),  # Kerrisdale
    "V6P": (49.2280, -123.1500),  # Marpole
    "V5V": (49.2630, -123.0870),  # Mount Pleasant East
    "V5W": (49.2410, -123.0750),  # South Vancouver North
    "V5X": (49.2260, -123.0930),  # South Vancouver
    "V5Y": (49.2680, -123.1020),  # Mount Pleasant
    "V5Z": (49.2580, -123.1130),  # Riley Park
}

# ~200m offset radius in degrees (~0.0018 lat, ~0.0025 lng at this latitude)
_OFFSET_RADIUS_LAT = 0.0018
_OFFSET_RADIUS_LNG = 0.0025


def geocode_fsa(fsa: str) -> tuple[float, float] | None:
    """Return (lat, lng) centroid for a given FSA, or None if unknown."""
    return _FSA_CENTROIDS.get(fsa.upper().strip())


def geocode_record(postal_code: str, record_id: int) -> tuple[float, float] | None:
    """Geocode a record with a small deterministic offset to avoid marker stacking.

    Uses hash of record_id to place the marker within ~200m of the FSA centroid.
    """
    fsa = postal_code[:3].upper().strip()
    centroid = _FSA_CENTROIDS.get(fsa)
    if centroid is None:
        return None

    angle = (hash(record_id) % 360) * math.pi / 180
    # Scale radius by a second hash-derived factor (0.3–1.0) for more spread
    radius_factor = 0.3 + (hash(record_id * 7) % 70) / 100
    lat = centroid[0] + _OFFSET_RADIUS_LAT * radius_factor * math.cos(angle)
    lng = centroid[1] + _OFFSET_RADIUS_LNG * radius_factor * math.sin(angle)

    return (round(lat, 6), round(lng, 6))
