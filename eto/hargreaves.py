import math

def extraterrestrial_radiation(latitude_deg: float, day_of_year: int) -> float:
    if not -90 <= latitude_deg <= 90:
        raise ValueError("Latitude must be between -90 and 90 degrees.")
    if not 1 <= day_of_year <= 366:
        raise ValueError("day_of_year must be between 1 and 366.")
    phi = math.radians(latitude_deg)
    dr = 1 + 0.033 * math.cos((2 * math.pi / 365) * day_of_year)
    delta = 0.409 * math.sin((2 * math.pi / 365) * day_of_year - 1.39)
    x = max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta)))
    omega_s = math.acos(x)
    g_sc = 0.0820
    ra = ((24 * 60 / math.pi) * g_sc * dr *
          (omega_s * math.sin(phi) * math.sin(delta) +
           math.cos(phi) * math.cos(delta) * math.sin(omega_s)))
    return max(0.0, ra)

def calculate_eto(latitude: float, day_of_year: int, tmax: float, tmin: float) -> dict:
    if not math.isfinite(tmax) or not math.isfinite(tmin):
        raise ValueError("Tmax and Tmin must be finite numbers.")
    if tmax < tmin:
        raise ValueError("Tmax cannot be lower than Tmin.")
    ra = extraterrestrial_radiation(latitude, day_of_year)
    tmean = (tmax + tmin) / 2
    eto = 0.0023 * ra * (tmean + 17.8) * math.sqrt(max(0.0, tmax - tmin))
    return {"ra": ra, "eto": max(0.0, eto)}
