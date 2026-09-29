from decimal import Decimal as D

import pytest

from pipeline import index as ix


def test_months_and_month_end():
    assert ix.months("2015-11", "2016-02") == ["2015-11", "2015-12", "2016-01", "2016-02"]
    assert ix.month_end("2016-02").isoformat() == "2016-02-29" and ix.month_end("2015-12").isoformat() == "2015-12-31"


def test_semester_value_applies_to_each_of_its_six_months():
    out: dict = {}
    ix.expand_period("2025-07-01", "2025-12-31", D("0.2896"), out)
    assert sorted(out) == ["2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12"]
    assert set(out.values()) == {D("0.2896")}


def test_weights_are_the_previous_years_demand_shares_over_all_basket_regions():
    demand = {("EU", 2014): D(2), ("US", 2014): D(4), ("CN", 2014): D(10), ("RU", 2014): D(4), ("EU", 2015): D(100)}
    w = ix.demand_shares(demand, ("EU", "US", "CN", "RU"), 2015)  # uses 2014, not 2015
    assert w == {"EU": D("0.1"), "US": D("0.2"), "CN": D("0.5"), "RU": D("0.2")}
    with pytest.raises(KeyError):
        ix.demand_shares(demand, ("EU", "US", "CN", "RU"), 2017)  # no 2016 demand


def test_renormalise_over_included_regions_drops_russia():
    w = {"EU": D("0.1"), "US": D("0.2"), "CN": D("0.5"), "RU": D("0.2")}
    r = ix.renormalise(w, ["EU", "US", "CN"])
    assert r == {"EU": D("0.125"), "US": D("0.25"), "CN": D("0.625")} and sum(r.values()) == 1


def test_combine_matches_a_hand_computation():
    base = {"EU": D("0.1"), "US": D("0.2"), "CN": D("0.5"), "RU": D("0.2")}
    usd = {"EU": D("0.30"), "US": D("0.15"), "CN": D("0.09")}
    c = ix.combine("2015-01", usd, base)
    assert c.level == D("0.131250")  # 0.125*0.30 + 0.25*0.15 + 0.625*0.09
    assert c.contributions == {"CN": D("0.056250"), "EU": D("0.037500"), "US": D("0.037500")}
    assert c.composition == ("CN", "EU", "US") and sum(c.contributions.values()) == c.level
    eq = ix.combine("2015-01", usd, base, equal=True)
    assert eq.level == D("0.180000") and set(eq.weights.values()) == {D("0.333333333333")}


def test_combine_with_one_region_is_that_region():
    c = ix.combine("2016-01", {"EU": D("0.123456")}, {"EU": D("0.1"), "US": D("0.9")})
    assert c.level == D("0.123456") and c.weights == {"EU": D(1)}


def test_carry_forward_limits_and_flags():
    obs = {"2025-12": D("0.29")}
    out = ix.carry_forward(obs, ix.months("2025-11", "2026-05"), limit=3)
    assert "2025-11" not in out  # nothing to carry before the first observation
    assert out["2025-12"] == (D("0.29"), False)
    assert out["2026-03"] == (D("0.29"), True) and "2026-04" not in out
    assert ix.carry_forward(obs, ["2030-01"], None)["2030-01"] == (D("0.29"), True)  # unlimited (China's tariff)


def test_index_form_is_100_at_the_2015_mean_and_scales():
    levels = {m: D("0.2") for m in ix.months("2015-01", "2015-12")} | {"2016-01": D("0.3")}
    idx = ix.index_form(levels)
    assert idx["2015-06"] == D("100.000") and idx["2016-01"] == D("150.000")
    with pytest.raises(ValueError):
        ix.index_form({"2015-01": D("0.2")})


def test_weighted_mean_renormalises_over_countries_present():
    m, w = ix.weighted_mean({"DE": D(100), "FR": D(50)}, {"DE": D(3), "FR": D(1), "ES": D(4)})
    assert m == D("87.5") and w == {"DE": D("0.75"), "FR": D("0.25")}
    with pytest.raises(ValueError):
        ix.weighted_mean({"XX": D(1)}, {"DE": D(1)})


def test_rounding_happens_once_and_half_even():
    assert ix.q6(D("0.1234565")) == D("0.123456") and ix.q6(D("0.1234575")) == D("0.123458")
    assert ix.q3(D("100.0005")) == D("100.000") and ix.q3(D("100.0015")) == D("100.002")
