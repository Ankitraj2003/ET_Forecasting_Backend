from eto.hargreaves import calculate_eto, extraterrestrial_radiation

def test_ra_positive():
    assert extraterrestrial_radiation(30.97, 227) > 0

def test_eto_nonnegative():
    result = calculate_eto(30.97, 227, 34, 26)
    assert result["eto"] >= 0

def test_equal_temperature():
    result = calculate_eto(30.97, 227, 30, 30)
    assert result["eto"] == 0.0

def test_invalid_temperature_range():
    try:
        calculate_eto(30.97, 227, 25, 30)
        assert False
    except ValueError:
        assert True

def test_invalid_latitude():
    try:
        extraterrestrial_radiation(100, 227)
        assert False
    except ValueError:
        assert True

def test_invalid_day_of_year():
    try:
        extraterrestrial_radiation(30.97, 0)
        assert False
    except ValueError:
        assert True
