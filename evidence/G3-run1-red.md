# G3 run 1 (RED) — 2026-09-29

First run of `python -m checks.cross_check` against the tolerances committed in 85d3655. Kept unedited so the history shows what failed before any amendment. **49 of 58 rows passed, 9 failed.**

| check | item | ours | theirs | tolerance | pass | note |
|---|---|---|---|---|---|---|
| eurostat_household_all_taxes_eu27 | 2024-S1 | 0.2916 | 0.2916 | abs 0.0001 | PASS |  |
| eurostat_household_all_taxes_eu27 | 2024-S2 | 0.2887 | 0.2887 | abs 0.0001 | PASS |  |
| eurostat_household_all_taxes_eu27 | 2025-S1 | 0.2879 | 0.2879 | abs 0.0001 | PASS |  |
| eurostat_household_all_taxes_eu27 | 2025-S2 | 0.2896 | 0.2896 | abs 0.0001 | PASS |  |
| eurostat_household_excl_taxes_eu27 | 2024-S1 | 0.2222 | 0.2222 | abs 0.0001 | PASS |  |
| eurostat_household_excl_taxes_eu27 | 2024-S2 | 0.2175 | 0.2175 | abs 0.0001 | PASS |  |
| eurostat_household_excl_taxes_eu27 | 2025-S1 | 0.2075 | 0.2075 | abs 0.0001 | PASS |  |
| eurostat_household_excl_taxes_eu27 | 2025-S2 | 0.2059 | 0.2059 | abs 0.0001 | PASS |  |
| eurostat_nonhousehold_excl_taxes_eu27_all_bands | 2024-S1 | 0.1512 | 0.1575 | abs 0.0001 | FAIL |  |
| eurostat_nonhousehold_excl_taxes_eu27_all_bands | 2024-S2 | 0.1563 | 0.1629 | abs 0.0001 | FAIL |  |
| eurostat_nonhousehold_excl_taxes_eu27_all_bands | 2025-S1 | 0.1514 | 0.157 | abs 0.0001 | FAIL |  |
| eurostat_nonhousehold_excl_taxes_eu27_all_bands | 2025-S2 | 0.1452 | 0.1511 | abs 0.0001 | FAIL |  |
| eia_us_retail_price_epm | residential 2026-07 | 0.1831 | 0.1831 | abs 0.0001 | PASS | EPM cents/kWh / 100 |
| eia_us_retail_price_epm | residential 2025-07 | 0.1745 | 0.1745 | abs 0.0001 | PASS | EPM cents/kWh / 100 |
| eia_us_retail_price_epm | industrial 2026-07 | 0.0977 | 0.0977 | abs 0.0001 | PASS | EPM cents/kWh / 100 |
| eia_us_retail_price_epm | industrial 2025-07 | 0.0933 | 0.0933 | abs 0.0001 | PASS | EPM cents/kWh / 100 |
| eia_henry_hub_monthly_vs_daily | 2026-08 mean of 21 daily prices | 2.78524 | 2.78 | abs 0.01 | PASS |  |
| ember_yearly_demand_vs_sum_of_monthly | EU 2025 | 2606.42 | 2774.43 | rel 1.000% | FAIL | diff 6.056% |
| ember_yearly_demand_vs_sum_of_monthly | US 2025 | 4532.15 | 4532.14 | rel 1.000% | PASS | diff 0.000% |
| ember_yearly_demand_vs_sum_of_monthly | CN 2025 | 10369.1 | 10486.3 | rel 1.000% | FAIL | diff 1.117% |
| ember_yearly_demand_vs_sum_of_monthly | RU 2025 | 1148.79 | 1177.3 | rel 1.000% | FAIL | diff 2.421% |
| ember_yearly_demand_vs_sum_of_monthly | ZA 2025 | 222.69 | 236.84 | rel 1.000% | FAIL | diff 5.974% |
| ember_eu_price_monthly_vs_daily | DE 2026-06 (30 days, 0 gaps) | 111.132 | 111.13 | max(rel 3%, abs 2.0) | PASS | diff +0.00 EUR/MWh |
| ember_eu_price_monthly_vs_daily | FR 2026-06 (30 days, 0 gaps) | 66.2523 | 66.25 | max(rel 3%, abs 2.0) | PASS | diff +0.00 EUR/MWh |
| ember_eu_price_monthly_vs_daily | IT 2026-06 (30 days, 0 gaps) | 132.268 | 132.27 | max(rel 3%, abs 2.0) | PASS | diff -0.00 EUR/MWh |
| ember_eu_price_monthly_vs_daily | ES 2026-06 (30 days, 0 gaps) | 69.5833 | 69.58 | max(rel 3%, abs 2.0) | PASS | diff +0.00 EUR/MWh |
| ember_eu_price_monthly_vs_daily | PL 2026-06 (30 days, 0 gaps) | 114.516 | 114.52 | max(rel 3%, abs 2.0) | PASS | diff -0.00 EUR/MWh |
| ember_eu_price_monthly_vs_daily | NL 2026-06 (29 days, 1 gaps) | 107.021 | 107.02 | max(rel 3%, abs 2.0) | PASS | diff +0.00 EUR/MWh |
| ember_us_generation_vs_eia | US 2026-05 (ours = Ember) | 365.153 | 354.691 | Ember 0%..8% above EIA | PASS | Ember is +2.95% vs EIA |
| ember_us_generation_vs_eia | US 2026-06 (ours = Ember) | 410.15 | 399.671 | Ember 0%..8% above EIA | PASS | Ember is +2.62% vs EIA |
| ember_us_generation_vs_eia | US 2026-07 (ours = Ember) | 467.936 | 453.744 | Ember 0%..8% above EIA | PASS | Ember is +3.13% vs EIA |
| ember_eu_demand_vs_eurostat_inland_demand | EU 2025 vs inland demand (ID) | 2774.43 | 2664.06 | rel 6.000% | PASS | diff 4.143% |
| ember_eu_demand_vs_eurostat_inland_demand | EU 2025 vs final consumption (FC), information only | 2774.43 | 2412.06 | info | PASS | diff 15.0%: Ember's Demand is not FC |
| ember_russia_demand_vs_so_ups | RU 2025 (low_confidence tier) | 1177.3 | 1177.3 | rel 0.500% | PASS | diff 0.000% |
| ember_china_demand_vs_nea | CN 2026-08 | 1020.1 | 1033.2 | rel 3.000% | PASS | diff 1.268% |
| ecb_monthly_vs_daily_mean | USD 2026-06 (22 days) | 1.1518 | 1.1518 | rel 0.000% | PASS | diff 0.000% |
| ecb_monthly_vs_daily_mean | USD 2026-07 (23 days) | 1.14175 | 1.14175 | rel 0.000% | PASS | diff 0.000% |
| ecb_monthly_vs_daily_mean | USD 2026-08 (21 days) | 1.15931 | 1.15931 | rel 0.000% | PASS | diff 0.000% |
| ecb_monthly_vs_daily_mean | CNY 2026-06 (22 days) | 7.80446 | 7.80446 | rel 0.000% | PASS | diff 0.000% |
| ecb_monthly_vs_daily_mean | CNY 2026-07 (23 days) | 7.73706 | 7.73706 | rel 0.000% | PASS | diff 0.000% |
| ecb_monthly_vs_daily_mean | CNY 2026-08 (21 days) | 7.80916 | 7.80916 | rel 0.000% | PASS | diff 0.000% |
| ecb_monthly_vs_daily_mean | ZAR 2026-06 (22 days) | 18.8681 | 18.8681 | rel 0.000% | PASS | diff 0.000% |
| ecb_monthly_vs_daily_mean | ZAR 2026-07 (23 days) | 18.8035 | 18.8035 | rel 0.000% | PASS | diff 0.000% |
| ecb_monthly_vs_daily_mean | ZAR 2026-08 (21 days) | 18.7357 | 18.7357 | rel 0.000% | PASS | diff 0.000% |
| worldbank_vs_imf_europe_gas | 36 months, worst 2023-10 | 14.57 | 13.3888 | rel 5% every month | FAIL | 2 months outside; worst diff 8.82% |
| sanity | eurostat_household_eur_per_kwh | 0.1035 | 0.3951 | 0.03..0.8 | PASS | 84 points, min..max shown |
| sanity | eurostat_nonhousehold_eur_per_kwh | 0.1039 | 0.2552 | 0.02..0.6 | PASS | 84 points, min..max shown |
| sanity | eia_us_retail_usd_per_kwh | 0.0821 | 0.1883 | 0.02..0.5 | PASS | 38 points, min..max shown |
| sanity | eia_henry_hub_usd_per_mmbtu | 2.71 | 7.72 | 0.5..40.0 | PASS | 26 points, min..max shown |
| sanity | ember_day_ahead_monthly_eur_per_mwh | 15.35 | 324.79 | -100.0..1000.0 | PASS | 149 points, min..max shown |
| sanity | ember_day_ahead_daily_eur_per_mwh | 6.83 | 235.6 | -600.0..4000.0 | PASS | 183 points, min..max shown |
| sanity | ember_emissions_intensity | 201.14 | 767.244 | 0.0..1300.0 | PASS | 15 points, min..max shown |
| sanity | ember_yearly_intensity | 209.879 | 799.411 | 0.0..1300.0 | PASS | 15 points, min..max shown |
| sanity | ecb_usd_per_eur | 0.982567 | 1.1824 | 0.8..1.6 | PASS | 143 points, min..max shown |
| sanity | ecb_cny_per_eur | 6.85384 | 8.37538 | 5.0..10.0 | PASS | 143 points, min..max shown |
| sanity | ecb_zar_per_eur | 16.2796 | 21.1972 | 10.0..30.0 | PASS | 143 points, min..max shown |
| sanity | worldbank_gas_usd_per_mmbtu | 1.5 | 21.11 | 0.0..100.0 | PASS | 72 points, min..max shown |
| sanity | worldbank_coal_usd_per_t | 90.6 | 162.5 | 0.0..600.0 | PASS | 72 points, min..max shown |

49 of 58 passed
