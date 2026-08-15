import time
import requests

URL = "https://geocoding-api.open-meteo.com/v1/search"
CACHE, TTL = {}, 3600

def geocode_location(location: str) -> dict:
    location = location.strip()
    if len(location) < 2:
        raise ValueError("Location must contain at least 2 characters.")
    key = location.lower()
    cached = CACHE.get(key)
    if cached and time.time() - cached["time"] < TTL:
        return cached["data"]
    try:
        r = requests.get(URL, params={
            "name": location, "count": 1, "language": "en", "format": "json"
        }, timeout=15)
        r.raise_for_status()
    except requests.RequestException as exc:
        raise ValueError(f"Geocoding service is unavailable: {exc}")
    results = r.json().get("results", [])
    if not results:
        raise ValueError(f"Location not found: {location}")
    x = results[0]
    data = {
        "name": x.get("name", location),
        "country": x.get("country"),
        "country_code": x.get("country_code"),
        "latitude": float(x["latitude"]),
        "longitude": float(x["longitude"]),
        "timezone": x.get("timezone"),
        "elevation_m": float(x.get("elevation", 0.0) or 0.0),
    }
    CACHE[key] = {"data": data, "time": time.time()}
    return data
