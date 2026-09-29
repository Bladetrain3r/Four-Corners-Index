"""Every live request the pipeline makes, paired with the fixture that stands in for it and the parser that reads it."""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pipeline import desnz, ecb, eia, ember, eurostat, worldbank
from pipeline.common import SourceError

EU27 = ("BE", "BG", "CZ", "DK", "DE", "EE", "IE", "EL", "ES", "FR", "HR", "IT", "CY", "LV", "LT", "LU", "HU", "MT",
        "NL", "AT", "PL", "PT", "RO", "SI", "SK", "FI", "SE")
_ES = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
_EIA = "https://api.eia.gov/v2"
_EMBER = "https://files.ember-energy.org/public-downloads"
_HICP_GEOS = "&".join(f"geo={g}" for g in ("EU", "EA", "DE", "FR", "IT", "ES", "PL", "NL"))


def _geos(codes: tuple[str, ...]) -> str:
    return "&".join(f"geo={g}" for g in ("EU27_2020", *codes))


def _eia_url(route: str, **q: str) -> str:
    return f"{_EIA}/{route}/data/?api_key={{key}}&" + "&".join(f"{k}={v}" for k, v in q.items())


@dataclass(frozen=True)
class Request:
    source: str
    name: str
    url: str  # may contain {key}; the key is added at fetch time and never stored
    fixture: str  # file under fixtures/<source>/
    parse: Callable[[bytes, str, str, list[dict[str, Any]] | None], list[dict[str, Any]]]  # (raw, retrieved_at, kind, gaps) -> points
    key_env: str | None = None
    role: str = "primary"  # 'cross_check' requests feed G3 only


def _es(dataset: str) -> Callable[..., list[dict[str, Any]]]:
    return lambda raw, at, kind, gaps: eurostat.parse(raw, dataset, at)


def _wb(raw: bytes, at: str, kind: str, gaps: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return worldbank.parse_csv_extract(raw, at, gaps) if kind == "fixture" else worldbank.parse_xlsx(raw, at, gaps)


REQUESTS: tuple[Request, ...] = (
    Request("eurostat", "nrg_pc_204", f"{_ES}/nrg_pc_204?{_geos(EU27)}&currency=EUR&nrg_cons=KWH2500-4999&sinceTimePeriod=2015-S1&format=JSON",
            "nrg_pc_204_household.json", _es("nrg_pc_204")),
    Request("eurostat", "nrg_pc_205", f"{_ES}/nrg_pc_205?{_geos(EU27)}&currency=EUR&nrg_cons=MWH2000-19999&sinceTimePeriod=2015-S1&format=JSON",
            "nrg_pc_205_nonhousehold.json", _es("nrg_pc_205")),
    Request("eurostat", "nrg_pc_205_ic", f"{_ES}/nrg_pc_205?{_geos(EU27)}&currency=EUR&nrg_cons=MWH500-1999&sinceTimePeriod=2015-S1&format=JSON",
            "nrg_pc_205_band_ic.json", _es("nrg_pc_205")),  # Eurostat's own headline non-household band, shown beside ID
    Request("eurostat", "nrg_pc_204_c", f"{_ES}/nrg_pc_204_c?{_geos(EU27)}&currency=EUR&nrg_cons=KWH2500-4999&sinceTimePeriod=2017&format=JSON",
            "nrg_pc_204_c_components.json", _es("nrg_pc_204_c")),
    Request("eurostat", "prc_hicp_minr", f"{_ES}/prc_hicp_minr?{_HICP_GEOS}&coicop18=CP0451&unit=I25&unit=RCH_A&sinceTimePeriod=2020-01&format=JSON",
            "prc_hicp_minr_CP0451.json", _es("prc_hicp_minr")),
    Request("eurostat", "nrg_cb_e", f"{_ES}/nrg_cb_e?{_geos(EU27)}&nrg_bal=FC&nrg_bal=ID&siec=E7000&unit=GWH&sinceTimePeriod=2013&format=JSON",
            "nrg_cb_e_consumption.json", _es("nrg_cb_e")),
    Request("eia", "retail_price", _eia_url("electricity/retail-sales", frequency="monthly", **{
        "data[0]": "price", "facets[stateid][]": "US", "start": "2015-01", "length": "5000"}) + "&facets[sectorid][]=RES&facets[sectorid][]=IND",
            "retail_sales_us_monthly_2025-01_onwards.json", lambda raw, at, kind, gaps: eia.parse_retail_price(raw, at, gaps=gaps), "EIA_API_KEY"),
    Request("eia", "henry_hub_daily", _eia_url("natural-gas/pri/fut", frequency="daily", **{
        "data[0]": "value", "facets[series][]": "RNGWHHD", "start": "2015-01-01", "length": "5000"}),
            "henry_hub_spot_daily_2026-09.json", lambda raw, at, kind, gaps: eia.parse_henry_hub(raw, at, "daily", gaps=gaps), "EIA_API_KEY"),
    Request("eia", "henry_hub_monthly", _eia_url("natural-gas/pri/fut", frequency="monthly", **{
        "data[0]": "value", "facets[series][]": "RNGWHHD", "start": "2015-01", "length": "5000"}),
            "henry_hub_spot_monthly_2025-10_onwards.json", lambda raw, at, kind, gaps: eia.parse_henry_hub(raw, at, "monthly", gaps=gaps), "EIA_API_KEY"),
    Request("eia", "generation_cross_check", _eia_url("electricity/electric-power-operational-data", frequency="monthly", **{
        "data[0]": "generation", "facets[location][]": "US", "facets[sectorid][]": "99", "start": "2015-01", "length": "5000"})
            + "".join(f"&facets[fueltypeid][]={f}" for f in ("ALL", "NG", "COL", "NUC", "WND", "SUN", "HYC", "PET", "BIO", "GEO", "OTH", "HPS")),
            "operational_data_us_generation_monthly_2026-05_onwards.json", lambda raw, at, kind, gaps: eia.parse_generation(raw, at), "EIA_API_KEY", "cross_check"),
    Request("ember", "monthly_generation", f"{_EMBER}/generation/outputs/release_generation_monthly_global.csv",
            "monthly_generation_global_sample.csv", lambda raw, at, kind, gaps: ember.parse_generation(raw, at, "monthly")),
    Request("ember", "yearly_generation", f"{_EMBER}/generation/outputs/release_generation_yearly_global.csv",
            "yearly_generation_global_sample.csv", lambda raw, at, kind, gaps: ember.parse_generation(raw, at, "yearly")),
    Request("ember", "prices_monthly", f"{_EMBER}/price/outputs/european_wholesale_electricity_price_data_monthly.csv",
            "price_monthly_sample.csv", lambda raw, at, kind, gaps: ember.parse_prices(raw, at, "monthly", gaps=gaps)),
    Request("ember", "prices_daily", f"{_EMBER}/price/outputs/european_wholesale_electricity_price_data_daily.csv",
            "price_daily_sample.csv", lambda raw, at, kind, gaps: ember.parse_prices(raw, at, "daily", gaps=gaps)),
    Request("ecb", "exr_monthly", "https://data-api.ecb.europa.eu/service/data/EXR/M.USD+CNY+ZAR+GBP.EUR.SP00.A?startPeriod=2015-01&format=csvdata&detail=dataonly",
            "exr_monthly_usd_cny_zar_2022-01.csv", lambda raw, at, kind, gaps: ecb.parse(raw, at)),
    Request("ecb", "exr_daily", "https://data-api.ecb.europa.eu/service/data/EXR/D.USD+CNY+ZAR+GBP.EUR.SP00.A?startPeriod=2015-01-01&format=csvdata&detail=dataonly",
            "exr_daily_usd_cny_zar_2026-06-01.csv", lambda raw, at, kind, gaps: ecb.parse(raw, at)),
    Request("worldbank", "pink_sheet_monthly", "resolve:pink_sheet",
            "pink_sheet_monthly_gas_coal_last36.csv", _wb),
    Request("desnz", "qep_562", "resolve:desnz_domestic", "table_562_medium_domestic_eu_uk.csv",
            lambda raw, at, kind, gaps: desnz.parse(raw, at, "5.6.2", kind, gaps=gaps)),
    Request("desnz", "qep_542", "resolve:desnz_nondomestic", "table_542_medium_nondomestic_eu_uk.csv",
            lambda raw, at, kind, gaps: desnz.parse(raw, at, "5.4.2", kind, gaps=gaps)),
)


def resolve_pink_sheet_url(landing_html: bytes) -> str:
    """The workbook's URL embeds a document id that changes; take the link from the landing page."""
    hits = re.findall(rb'href="([^"]*CMO-Historical-Data-Monthly\.xlsx)"', landing_html)
    if not hits:
        raise SourceError("worldbank", "no CMO-Historical-Data-Monthly.xlsx link on the commodity-markets page")
    url = hits[0].decode()
    return url if url.startswith("https://") else "https://www.worldbank.org" + url


def resolve_govuk_url(api_json: bytes, title_prefix: str) -> str:
    """The workbook's URL embeds an id that changes every release; take it from the GOV.UK content API attachments."""
    try:
        attachments = json.loads(api_json)["details"]["attachments"]
    except (ValueError, KeyError, TypeError) as exc:
        raise SourceError("desnz", f"GOV.UK content API response has no attachments ({exc!r})") from exc
    hits = [a["url"] for a in attachments if a.get("title", "").startswith(title_prefix) and a.get("url", "").endswith(".xlsx")]
    if not hits:
        raise SourceError("desnz", f"no .xlsx attachment titled {title_prefix!r} on the GOV.UK dataset page")
    return hits[0]


_GOVUK = "https://www.gov.uk/api/content/government/statistical-data-sets"
RESOLVERS: dict[str, tuple[str, Callable[[bytes], str]]] = {
    "pink_sheet": ("https://www.worldbank.org/en/research/commodity-markets", resolve_pink_sheet_url),
    "desnz_domestic": (f"{_GOVUK}/international-domestic-energy-prices", lambda b: resolve_govuk_url(b, "Domestic electricity prices in the EU")),
    "desnz_nondomestic": (f"{_GOVUK}/international-non-domestic-energy-prices", lambda b: resolve_govuk_url(b, "Non-domestic electricity prices in the EU")),
}
