# Real-Time ETo Forecasting System v5

7-day real-time reference evapotranspiration forecasting with two selectable methods:

1. Hargreaves-Samani
2. FAO-56 Penman-Monteith

## Workflow

Location -> Geocoding -> Forecast weather -> Both ETo methods -> Selected method -> 7-day result -> Excel

Both methods are calculated for every forecast day so their values can be compared. The dropdown controls which method is designated as the primary/selected ETo forecast.

## FAO-56 Penman-Monteith inputs

The system retrieves Tmax, Tmin, RHmax, RHmin, wind speed at 10 m, shortwave radiation and surface pressure from Open-Meteo. Wind speed is converted from 10 m to 2 m according to FAO-56. Net radiation is calculated from forecast shortwave radiation and longwave radiation terms; daily soil heat flux G is taken as approximately zero.

The implementation follows the FAO-56 daily reference evapotranspiration formulation for the grass reference surface.

## Run

```powershell
pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000`.


## v6: Crop ET (ETc) forecasting

The system now extends ETo to crop evapotranspiration using the FAO-56 single crop coefficient approach:

`ETc = Kc × ETo`

Inputs:
- Location
- ETo method: Hargreaves-Samani or FAO-56 Penman-Monteith
- Crop
- Date of sowing
- ET forecast start date

The system calculates crop day from the sowing date, derives the daily Kc from the FAO segmented Kc curve, multiplies it by the selected ETo, and returns seven daily ETc values.

### Important scientific distinction
FAO-56 Kc values are not a live weather feed. They are reference crop coefficients. The live part is the meteorological forecast used for ETo. The daily Kc is generated from FAO-56 Kc_ini, Kc_mid and Kc_end plus crop growth-stage lengths. The included stage lengths are indicative defaults and should be replaced by locally observed/validated phenology when available.

Official FAO source: https://www.fao.org/4/x0490e/x0490e0b.htm
