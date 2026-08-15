"""FAO-56 single crop coefficient (Kc) catalog and daily curve.

Values are standard FAO-56 reference values for non-stressed, well-managed
crops. Stage lengths are indicative profiles and should be adjusted when
local crop phenology is known. Kc is not a live weather variable: the FAO
reference table supplies Kc_ini, Kc_mid and Kc_end; the daily value is
constructed by the segmented Kc curve.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import date
from typing import Optional

FAO56_SOURCE = "https://www.fao.org/4/x0490e/x0490e0b.htm"

@dataclass(frozen=True)
class CropProfile:
    name: str
    aliases: tuple[str, ...]
    kc_ini: float
    kc_mid: float
    kc_end: float
    stage_days: tuple[int, int, int, int]
    notes: str = "Standard FAO-56 reference values; verify local stage lengths."

# Common FAO-56 crops. Stage lengths are indicative defaults for a 4-stage
# curve and are intentionally exposed in the API so the user can audit them.
CROPS = [
    CropProfile("Wheat", ("wheat",), 0.40, 1.15, 0.41, (20, 30, 50, 20)),
    CropProfile("Maize", ("maize","corn"), 0.30, 1.20, 0.35, (20, 35, 40, 30)),
    CropProfile("Rice", ("rice","paddy"), 1.05, 1.20, 0.90, (30, 30, 60, 30)),
    CropProfile("Potato", ("potato",), 0.50, 1.15, 0.75, (25, 30, 35, 25)),
    CropProfile("Tomato", ("tomato",), 0.60, 1.15, 0.80, (35, 40, 45, 25)),
    CropProfile("Soybean", ("soybean","soy"), 0.40, 1.15, 0.50, (20, 30, 45, 25)),
    CropProfile("Groundnut", ("groundnut","peanut"), 0.40, 1.15, 0.60, (25, 35, 45, 25)),
    CropProfile("Chickpea", ("chickpea","gram","chana"), 0.40, 1.00, 0.35, (20, 30, 40, 30)),
    CropProfile("Cotton", ("cotton",), 0.35, 1.20, 0.50, (30, 50, 55, 45)),
    CropProfile("Sorghum", ("sorghum",), 0.35, 1.10, 0.65, (20, 30, 40, 30)),
    CropProfile("Millet", ("millet","pearl millet"), 0.30, 1.00, 0.30, (15, 25, 40, 25)),
    CropProfile("Beans, green", ("green bean","beans","green beans"), 0.50, 1.05, 0.90, (20, 30, 25, 20)),
    CropProfile("Peas, fresh", ("pea","peas","fresh pea"), 0.50, 1.15, 1.10, (20, 30, 30, 20)),
    CropProfile("Onion, dry", ("onion","dry onion"), 0.70, 1.05, 0.75, (30, 40, 60, 40)),
    CropProfile("Cabbage", ("cabbage",), 0.70, 1.05, 0.95, (25, 30, 35, 20)),
]

_INDEX = {a: c for c in CROPS for a in c.aliases}

def list_crops():
    return [asdict(c) for c in CROPS]

def find_crop(name: str) -> CropProfile:
    key = " ".join(name.strip().lower().split())
    if key in _INDEX:
        return _INDEX[key]
    for c in CROPS:
        if key == c.name.lower() or key in c.name.lower():
            return c
    raise ValueError(f"Crop '{name}' is not in the FAO-56 catalog. Use /crops to see supported crops.")

def _segment_kc(day_in_crop: int, c: CropProfile) -> tuple[float, str]:
    # day_in_crop is 1-based. FAO segmented curve: horizontal initial,
    # linear development to Kc_mid, horizontal mid-season, linear decline.
    ini, dev, mid, late = c.stage_days
    total = sum(c.stage_days)
    if day_in_crop < 1 or day_in_crop > total:
        return (None, "outside-growing-period")
    if day_in_crop <= ini:
        return c.kc_ini, "initial"
    d = day_in_crop - ini
    if d <= dev:
        frac = d / dev
        return c.kc_ini + frac*(c.kc_mid-c.kc_ini), "development"
    d -= dev
    if d <= mid:
        return c.kc_mid, "mid-season"
    d -= mid
    frac = d / late
    return c.kc_mid + frac*(c.kc_end-c.kc_mid), "late-season"

def kc_for_date(crop: str, sowing_date: date, target_date: date):
    c=find_crop(crop)
    day=(target_date-sowing_date).days+1
    kc,stage=_segment_kc(day,c)
    return {
        "crop":c.name,"sowing_date":sowing_date,"target_date":target_date,
        "crop_day":day,"kc":None if kc is None else round(float(kc),4),
        "growth_stage":stage,"kc_ini":c.kc_ini,"kc_mid":c.kc_mid,"kc_end":c.kc_end,
        "stage_days":list(c.stage_days),"season_length_days":sum(c.stage_days),
        "source":"FAO Irrigation and Drainage Paper 56, Table 12",
        "source_url":FAO56_SOURCE,
        "standard_conditions":"non-stressed, well-managed crop; standard FAO-56 reference conditions",
    }
