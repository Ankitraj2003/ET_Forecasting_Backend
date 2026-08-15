import time
from datetime import date, timedelta
import requests

URL = "https://api.open-meteo.com/v1/forecast"
CACHE, TTL = {}, 600


def get_daily_forecast(latitude: float, longitude: float, start_date: date, days: int = 7):
    if days != 7:
        raise ValueError("This project currently supports exactly 7 forecast days.")
    end_date = start_date + timedelta(days=days - 1)
    key = (round(latitude, 4), round(longitude, 4), start_date.isoformat())
    cached = CACHE.get(key)
    if cached and time.time() - cached["time"] < TTL:
        return cached["data"]
    try:
        r = requests.get(URL, params={
            "latitude": latitude, "longitude": longitude,
            "daily": "temperature_2m_max,temperature_2m_min,relative_humidity_2m_max,relative_humidity_2m_min,wind_speed_10m_mean,shortwave_radiation_sum,surface_pressure_mean",
            "temperature_unit": "celsius", "wind_speed_unit": "kmh",
            "pressure_unit": "hPa", "timezone": "auto",
            "start_date": start_date.isoformat(), "end_date": end_date.isoformat(),
        }, timeout=20)
        r.raise_for_status()
    except requests.RequestException as exc:
        raise ValueError(f"Weather forecast service is unavailable: {exc}")
    data = r.json()
    if data.get("error"):
        raise ValueError(data.get("reason", "Weather API returned an error."))
    daily = data.get("daily")
    if not daily:
        raise ValueError("Weather API returned no daily forecast data.")

    fields = ["time", "temperature_2m_max", "temperature_2m_min",
              "relative_humidity_2m_max", "relative_humidity_2m_min",
              "wind_speed_10m_mean", "shortwave_radiation_sum", "surface_pressure_mean"]
    if not all(k in daily for k in fields):
        raise ValueError("Weather API returned incomplete Penman-Monteith variables.")
    arrays = [daily[k] for k in fields]
    if not all(len(x) == days for x in arrays):
        raise ValueError("Weather API returned an unexpected number of days.")

    rows = []
    for vals in zip(*arrays):
        d, high, low, rhmax, rhmin, wind, rs, pressure = vals
        if any(v is None for v in vals[1:]):
            raise ValueError(f"Missing meteorological data for {d}.")
        dt = date.fromisoformat(d)
        rows.append({
            "date": dt, "day_of_year": dt.timetuple().tm_yday,
            "tmax": float(high), "tmin": float(low),
            "rh_max": float(rhmax), "rh_min": float(rhmin),
            # Open-Meteo returns km/h here; PM requires m/s at 10 m.
            "wind_speed_10m": float(wind) / 3.6,
            "solar_radiation": float(rs),
            # Open-Meteo returns hPa here; PM pressure is kPa.
            "pressure_kpa": float(pressure) / 10.0,
        })
    CACHE[key] = {"data": rows, "time": time.time()}
    return rows
