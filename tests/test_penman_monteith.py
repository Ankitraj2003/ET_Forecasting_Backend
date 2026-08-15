from eto.penman_monteith import calculate_eto

def test_penman_monteith_nonnegative():
    r = calculate_eto(30.97, 227, 34, 26, 85, 45, 3.0, 20.0, 100.0, 250)
    assert r["eto"] >= 0

def test_penman_monteith_u2_conversion():
    r = calculate_eto(30.97, 227, 34, 26, 85, 45, 3.0, 20.0, 100.0, 250)
    assert 2.0 < r["u2"] < 2.7

def test_invalid_rh():
    try:
        calculate_eto(30.97, 227, 34, 26, 120, 45, 3, 20, 100, 250)
        assert False
    except ValueError:
        assert True
