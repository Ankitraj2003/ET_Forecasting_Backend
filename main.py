from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse

from eto.hargreaves import calculate_eto as calculate_hargreaves
from eto.penman_monteith import calculate_eto as calculate_penman_monteith
from models.schemas import ForecastResponse
from services.geocoding import geocode_location
from services.weather import get_daily_forecast
from services.excel_export import create_forecast_excel, create_etc_forecast_excel
from eto.crop_coefficients import list_crops, find_crop, kc_for_date, FAO56_SOURCE
from models.schemas import ETcForecastResponse

app = FastAPI(
    title="Real-Time ETo Forecasting System",
    version="5.0.0",
    description="7-day reference evapotranspiration forecasting using Hargreaves-Samani or FAO-56 Penman-Monteith."
)

METHODS = {"hargreaves-samani", "penman-monteith"}


def _get_forecast(location: str, start_date: date, method: str = "hargreaves-samani"):
    method = method.strip().lower()
    if method not in METHODS:
        raise HTTPException(400, "Method must be 'hargreaves-samani' or 'penman-monteith'.")
    today = date.today()
    latest = today + timedelta(days=9)
    if start_date < today:
        raise HTTPException(400, "For forecast mode, select today or a future date.")
    if start_date > latest:
        raise HTTPException(400, f"Start date must be between {today.isoformat()} and {latest.isoformat()}.")
    try:
        place = geocode_location(location)
        weather = get_daily_forecast(place["latitude"], place["longitude"], start_date, days=7)
        results = []
        for row in weather:
            hs = calculate_hargreaves(place["latitude"], row["day_of_year"], row["tmax"], row["tmin"])
            pm = calculate_penman_monteith(
                place["latitude"], row["day_of_year"], row["tmax"], row["tmin"],
                row["rh_max"], row["rh_min"], row["wind_speed_10m"],
                row["solar_radiation"], row["pressure_kpa"], place.get("elevation_m", 0.0)
            )
            results.append({
                "date": row["date"], "day_of_year": row["day_of_year"],
                "tmax_c": round(row["tmax"], 2), "tmin_c": round(row["tmin"], 2),
                "tmean_c": round((row["tmax"] + row["tmin"]) / 2, 2),
                "rh_max_pct": round(row["rh_max"], 2), "rh_min_pct": round(row["rh_min"], 2),
                "wind_speed_10m_m_s": round(row["wind_speed_10m"], 3),
                "solar_radiation_mj_m2_day": round(row["solar_radiation"], 3),
                "pressure_kpa": round(row["pressure_kpa"], 3),
                "ra_mj_m2_day": round(hs["ra"], 3),
                "hargreaves_samani_eto_mm_day": round(hs["eto"], 3),
                "penman_monteith_eto_mm_day": round(pm["eto"], 3),
                "eto_mm_day": round(hs["eto"] if method == "hargreaves-samani" else pm["eto"], 3),
                "selected_method": "Hargreaves-Samani" if method == "hargreaves-samani" else "FAO-56 Penman-Monteith",
                "pm_net_radiation_mj_m2_day": round(pm["rn"], 3),
                "pm_vapor_pressure_deficit_kpa": round(pm["es"] - pm["ea"], 4),
                "pm_wind_speed_2m_m_s": round(pm["u2"], 3),
            })
        return {
            "location_input": location, "resolved_location": place["name"],
            "country": place.get("country"), "timezone": place.get("timezone"),
            "latitude": place["latitude"], "longitude": place["longitude"],
            "method": "Hargreaves-Samani" if method == "hargreaves-samani" else "FAO-56 Penman-Monteith",
            "weather_source": "Open-Meteo Forecast API", "forecast_days": len(results),
            "forecast": results,
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"External data service error: {exc}")


def _get_etc_forecast(location: str, crop: str, sowing_date: date, start_date: date, method: str = "hargreaves-samani"):
    data = _get_forecast(location, start_date, method)
    try:
        profile = find_crop(crop)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    results=[]
    for row in data["forecast"]:
        target=date.fromisoformat(str(row["date"]))
        k=kc_for_date(profile.name, sowing_date, target)
        etc = None if k["kc"] is None else round(row["eto_mm_day"] * k["kc"], 3)
        results.append({**row,
            "crop":profile.name,"sowing_date":sowing_date,"crop_day":k["crop_day"],
            "growth_stage":k["growth_stage"],"kc":k["kc"],"etc_mm_day":etc,
            "kc_source":k["source"]})
    return {**{x:data[x] for x in ["location_input","resolved_location","country","timezone","latitude","longitude","method","weather_source"]},
            "crop":profile.name,"sowing_date":sowing_date,"forecast_start_date":start_date,
            "kc_source":"FAO Irrigation and Drainage Paper 56, Table 12",
            "kc_source_url":FAO56_SOURCE,"forecast_days":len(results),"forecast":results,
            "crop_profile":{"kc_ini":profile.kc_ini,"kc_mid":profile.kc_mid,"kc_end":profile.kc_end,
                            "stage_days":list(profile.stage_days),"season_length_days":sum(profile.stage_days)}}


@app.get("/", response_class=HTMLResponse)
def home():
    html = (Path(__file__).parent / "templates" / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/crops")
def crops():
    return {"source":"FAO Irrigation and Drainage Paper 56, Table 12", "source_url":FAO56_SOURCE, "crops":list_crops()}

@app.get("/kc")
def crop_kc(crop: str = Query(..., min_length=2), sowing_date: date = Query(...), target_date: date = Query(...)):
    try:
        return kc_for_date(crop, sowing_date, target_date)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

@app.get("/etc", response_model=ETcForecastResponse)
def etc_forecast(
    location: str = Query(..., min_length=2, max_length=100),
    crop: str = Query(..., min_length=2, max_length=80),
    sowing_date: date = Query(...),
    start_date: date = Query(default_factory=date.today),
    method: str = Query("hargreaves-samani")
):
    if sowing_date > start_date:
        raise HTTPException(400, "Sowing date cannot be after the forecast start date.")
    return _get_etc_forecast(location, crop, sowing_date, start_date, method)

@app.get("/etc/excel")
def etc_excel(
    location: str = Query(..., min_length=2, max_length=100),
    crop: str = Query(..., min_length=2, max_length=80),
    sowing_date: date = Query(...),
    start_date: date = Query(default_factory=date.today),
    method: str = Query("hargreaves-samani")
):
    data=_get_etc_forecast(location, crop, sowing_date, start_date, method)
    content=create_etc_forecast_excel(data)
    safe="".join(c if c.isalnum() else "_" for c in data["crop"]).strip("_") or "crop"
    filename=f"ETc_Forecast_{safe}_{start_date.isoformat()}.xlsx"
    return StreamingResponse(BytesIO(content), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition":f'attachment; filename="{filename}"'})


@app.get("/health")
def health():
    return {"status": "ok", "service": "ETo Forecast Backend", "methods": ["Hargreaves-Samani", "FAO-56 Penman-Monteith"], "version": app.version, "crop_coefficient_source": FAO56_SOURCE}


@app.get("/forecast", response_model=ForecastResponse)
def forecast(
    location: str = Query(..., min_length=2, max_length=100),
    start_date: date = Query(default_factory=date.today),
    method: str = Query("hargreaves-samani")
):
    return _get_forecast(location, start_date, method)


@app.get("/eto")
def single_day_eto(
    location: str = Query(..., min_length=2, max_length=100),
    selected_date: date = Query(default_factory=date.today, alias="date"),
    method: str = Query("hargreaves-samani")
):
    data = _get_forecast(location, selected_date, method)
    return {k: data[k] for k in ["location_input", "resolved_location", "country", "timezone", "latitude", "longitude", "method", "weather_source"]} | data["forecast"][0]


@app.get("/forecast/excel")
def forecast_excel(
    location: str = Query(..., min_length=2, max_length=100),
    start_date: date = Query(default_factory=date.today),
    method: str = Query("hargreaves-samani")
):
    data = _get_forecast(location, start_date, method)
    try:
        content = create_forecast_excel(data)
    except Exception as exc:
        raise HTTPException(500, f"Could not create Excel file: {exc}")
    safe = "".join(c if c.isalnum() else "_" for c in data["resolved_location"]).strip("_") or "location"
    filename = f"ETo_Forecast_{safe}_{start_date.isoformat()}.xlsx"
    return StreamingResponse(BytesIO(content), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
