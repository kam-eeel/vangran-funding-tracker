"""Geocoding module — resolves postal codes to lat/lng coordinates.

Called once per record at insert time. Results are stored in the
record_locations table and never re-fetched.
"""


def geocode_record(postal_code: str) -> tuple[float, float] | None:
    """Geocode a postal code. Called during record ingestion.

    Returns (lat, lng) or None if the postal code could not be resolved.

    # TODO: Pick a geocoding provider and implement this function.
    #
    # Option A — OpenCage (https://opencagedata.com/)
    #   - Sign up for an API key, store in env var OPENCAGE_API_KEY
    #   - pip install opencage
    #   - Call: geocoder.geocode(postal_code + ", Canada")
    #   - Extract result[0]['geometry']['lat'], result[0]['geometry']['lng']
    #
    # Option B — Google Geocoding API
    #   - Enable Geocoding API in GCP console, store key in GOOGLE_GEOCODING_KEY
    #   - pip install googlemaps
    #   - Call: gmaps.geocode(postal_code + ", Canada")
    #
    # Option C — Canada Post / Nominatim / etc.
    #
    # Whichever you choose:
    #   1. Make the HTTP request with the full postal code
    #   2. Parse lat/lng from the response
    #   3. Return (lat, lng) on success, None on failure
    #   4. Handle rate limits / errors gracefully (return None, log warning)
    """
    return None  # TODO: replace with real implementation
