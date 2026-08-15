from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field

class DailyETo(BaseModel):
    date: date
    day_of_year: int
    tmax_c: float = Field(...)
    tmin_c: float = Field(...)
    tmean_c: float = Field(...)
    rh_max_pct: float = Field(...)
    rh_min_pct: float = Field(...)
    wind_speed_10m_m_s: float = Field(...)
    solar_radiation_mj_m2_day: float = Field(...)
    pressure_kpa: float = Field(...)
    ra_mj_m2_day: float = Field(...)
    hargreaves_samani_eto_mm_day: float = Field(...)
    penman_monteith_eto_mm_day: float = Field(...)
    eto_mm_day: float = Field(...)
    selected_method: str = Field(...)
    pm_net_radiation_mj_m2_day: float = Field(...)
    pm_vapor_pressure_deficit_kpa: float = Field(...)
    pm_wind_speed_2m_m_s: float = Field(...)

class ForecastResponse(BaseModel):
    location_input: str
    resolved_location: str
    country: Optional[str] = None
    timezone: Optional[str] = None
    latitude: float
    longitude: float
    method: str
    weather_source: str
    forecast_days: int
    forecast: List[DailyETo]


class DailyETc(DailyETo):
    crop: str
    sowing_date: date
    crop_day: int
    growth_stage: str
    kc: Optional[float] = None
    etc_mm_day: Optional[float] = None
    kc_source: str

class ETcForecastResponse(BaseModel):
    location_input: str
    resolved_location: str
    country: Optional[str] = None
    timezone: Optional[str] = None
    latitude: float
    longitude: float
    method: str
    crop: str
    sowing_date: date
    forecast_start_date: date
    kc_source: str
    forecast_days: int
    forecast: List[DailyETc]
