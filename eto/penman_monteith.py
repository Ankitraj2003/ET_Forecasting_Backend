import math


def _svp(t_c: float) -> float:
    return 0.6108 * math.exp((17.27 * t_c) / (t_c + 237.3))


def saturation_vapor_pressure(tmax: float, tmin: float) -> float:
    return (_svp(tmax) + _svp(tmin)) / 2.0


def actual_vapor_pressure(tmax: float, tmin: float, rh_max: float, rh_min: float) -> float:
    if not 0 <= rh_min <= 100 or not 0 <= rh_max <= 100:
        raise ValueError("Relative humidity must be between 0 and 100%.")
    if rh_max < rh_min:
        raise ValueError("RH max cannot be lower than RH min.")
    # FAO-56 Eq. 19 for daily data.
    return (_svp(tmin) * rh_max / 100.0 + _svp(tmax) * rh_min / 100.0) / 2.0


def slope_vapor_pressure_curve(tmean: float) -> float:
    return 4098.0 * _svp(tmean) / ((tmean + 237.3) ** 2)


def psychrometric_constant(pressure_kpa: float) -> float:
    if pressure_kpa <= 0:
        raise ValueError("Atmospheric pressure must be positive.")
    return 0.000665 * pressure_kpa


def net_radiation_from_solar(
    latitude: float,
    day_of_year: int,
    solar_radiation_mj_m2_day: float,
    tmax: float,
    tmin: float,
    ea_kpa: float,
    elevation_m: float = 0.0,
) -> dict:
    """FAO-56 daily Rn from measured/forecast shortwave radiation.

    Rs is in MJ m-2 day-1. Clear-sky radiation is calculated from Ra and
    elevation. Rso is capped at 0.75 Ra + elevation correction as recommended
    by FAO-56 Eq. 37.
    """
    from eto.hargreaves import extraterrestrial_radiation

    if solar_radiation_mj_m2_day < 0:
        raise ValueError("Solar radiation cannot be negative.")
    ra = extraterrestrial_radiation(latitude, day_of_year)
    rso = (0.75 + 2e-5 * elevation_m) * ra
    rs = solar_radiation_mj_m2_day
    rns = (1 - 0.23) * rs

    sigma = 4.903e-9
    tmax_k = tmax + 273.16
    tmin_k = tmin + 273.16
    cloud_term = 1.35 * min(rs / rso, 1.0) - 0.35 if rso > 0 else 0.0
    rnl = sigma * ((tmax_k**4 + tmin_k**4) / 2) * (0.34 - 0.14 * math.sqrt(max(ea_kpa, 0.0))) * cloud_term
    rn = rns - rnl
    return {"ra": ra, "rso": rso, "rns": rns, "rnl": rnl, "rn": rn}


def calculate_eto(
    latitude: float,
    day_of_year: int,
    tmax: float,
    tmin: float,
    rh_max: float,
    rh_min: float,
    wind_speed_10m: float,
    solar_radiation_mj_m2_day: float,
    pressure_kpa: float,
    elevation_m: float = 0.0,
) -> dict:
    """FAO-56 reference ETo, daily timestep, grass reference surface."""
    values = [tmax, tmin, rh_max, rh_min, wind_speed_10m, solar_radiation_mj_m2_day, pressure_kpa, elevation_m]
    if not all(math.isfinite(float(x)) for x in values):
        raise ValueError("All Penman-Monteith inputs must be finite numbers.")
    if tmax < tmin:
        raise ValueError("Tmax cannot be lower than Tmin.")
    if wind_speed_10m < 0:
        raise ValueError("Wind speed cannot be negative.")

    tmean = (tmax + tmin) / 2.0
    # FAO-56 Eq. 47 conversion from 10 m wind speed to 2 m.
    u2 = wind_speed_10m * 4.87 / math.log(67.8 * 10.0 - 5.42)
    es = saturation_vapor_pressure(tmax, tmin)
    ea = actual_vapor_pressure(tmax, tmin, rh_max, rh_min)
    delta = slope_vapor_pressure_curve(tmean)
    gamma = psychrometric_constant(pressure_kpa)
    radiation = net_radiation_from_solar(
        latitude, day_of_year, solar_radiation_mj_m2_day,
        tmax, tmin, ea, elevation_m
    )
    rn = radiation["rn"]
    g = 0.0
    numerator = 0.408 * delta * (rn - g) + gamma * (900.0 / (tmean + 273.0)) * u2 * (es - ea)
    denominator = delta + gamma * (1.0 + 0.34 * u2)
    eto = numerator / denominator if denominator > 0 else 0.0

    return {
        "eto": max(0.0, eto), "tmean": tmean, "u2": u2,
        "es": es, "ea": ea, "delta": delta, "gamma": gamma,
        "rn": rn, "rns": radiation["rns"], "rnl": radiation["rnl"],
        "ra": radiation["ra"], "rso": radiation["rso"]
    }
