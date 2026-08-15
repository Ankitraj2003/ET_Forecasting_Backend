
from datetime import date, timedelta
from eto.crop_coefficients import find_crop, kc_for_date

def test_wheat_lookup():
    c=find_crop("wheat")
    assert c.kc_mid == 1.15

def test_kc_initial_stage():
    d=date(2026,1,1)
    x=kc_for_date("wheat",d,d)
    assert x["kc"] == 0.4
    assert x["growth_stage"] == "initial"

def test_kc_outside_growing_period():
    d=date(2026,1,1)
    x=kc_for_date("wheat",d,d+timedelta(days=200))
    assert x["kc"] is None
    assert x["growth_stage"] == "outside-growing-period"
