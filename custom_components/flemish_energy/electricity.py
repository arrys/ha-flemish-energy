"""Group Fluvius electricity statistics and match ENGIE tariff sensors."""

import re
from collections.abc import Iterable

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

ELECTRICITY_STATISTIC = re.compile(
    r"(?P<meter>(?:flemish_energy|fluvius):[0-9]{18}"
    r"(?:_[a-z0-9_]+)?_electricity_kwh(?:_until_[a-f0-9]+)?)"
    r"_(?:consumption|injection)_(?:high|low|total)"
)
ENGIE_PRICE = re.compile(
    r"(?P<contract>.+)_(?P<direction>offtake|injection)_"
    r"(?P<slot>peak|offpeak|total_hours)(?P<tax>_excl_vat)?",
    re.IGNORECASE,
)
SERIES = {
    "consumption_high": ("Import · Day / peak", "#b45309"),
    "consumption_low": ("Import · Night / off-peak", "#f5a623"),
    "injection_high": ("Export · Day / peak", "#075985"),
    "injection_low": ("Export · Night / off-peak", "#38bdf8"),
    "consumption_total": ("Import · Total", "#b45309"),
    "injection_total": ("Export · Total", "#075985"),
}
RATE_LABELS = {
    ("offtake", "peak"): "Import · Day / peak",
    ("offtake", "offpeak"): "Import · Night / off-peak",
    ("offtake", "total_hours"): "Import · Single rate",
    ("injection", "peak"): "Export · Day / peak",
    ("injection", "offpeak"): "Export · Night / off-peak",
    ("injection", "total_hours"): "Export · Single rate",
}


def electricity_meter(statistic_id: str) -> str | None:
    """Return the source prefix, including meter serial and history cutoff."""
    match = ELECTRICITY_STATISTIC.fullmatch(statistic_id)
    return match["meter"] if match else None


def electricity_series(meter: str, available: set[str]) -> list[dict[str, str]]:
    """Prefer a complete high/low split and avoid counting its total twice."""
    series = []
    for direction in ("consumption", "injection"):
        tariffs = [f"{direction}_high", f"{direction}_low"]
        total = f"{direction}_total"
        has_split = all(f"{meter}_{metric}" in available for metric in tariffs)
        if not has_split and f"{meter}_{total}" in available:
            tariffs = [total]
        for metric in tariffs:
            entity = f"{meter}_{metric}"
            if entity in available:
                label, color = SERIES[metric]
                series.append({"entity": entity, "name": label, "color": color})
    return series


def engie_tariff_rows(
    hass: HomeAssistant, meter: str, selected_prices: Iterable[str]
) -> list[dict[str, str]]:
    """Find enabled rates from the selected ENGIE agreement and Fluvius EAN."""
    registry = er.async_get(hass)
    ean = meter.split(":", 1)[1][:18]
    contracts = set()
    for entity_id in selected_prices:
        anchor = registry.async_get(entity_id)
        if anchor and anchor.platform == "engie_be":
            match = ENGIE_PRICE.fullmatch(anchor.unique_id)
            if match and re.search(rf"(?<![0-9]){ean}(?![0-9])", match["contract"]):
                contracts.add((anchor.config_entry_id, match["contract"], match["tax"]))
    if len(contracts) != 1:
        return []

    entry_id, contract, tax = contracts.pop()
    if entry_id is None:
        return []
    rates = {}
    for entity in er.async_entries_for_config_entry(registry, entry_id):
        if (
            entity.platform != "engie_be"
            or entity.domain != "sensor"
            or entity.disabled_by is not None
        ):
            continue
        match = ENGIE_PRICE.fullmatch(entity.unique_id)
        if match and match["contract"] == contract and match["tax"] == tax:
            rates[match["direction"].lower(), match["slot"].lower()] = entity.entity_id
    return [
        {"entity": rates[key], "name": label + (" (excl. VAT)" if tax else "")}
        for key, label in RATE_LABELS.items()
        if key in rates
    ]
