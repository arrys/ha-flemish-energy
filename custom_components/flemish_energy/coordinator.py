"""Read published usage and the current ENGIE rate."""

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
import logging
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DAYS_AGO, PRICE, PRICE_UNIT, STATISTIC
from .electricity import TARIFF_METRICS, electricity_meter, engie_tariff_entities
from .estimate import day_window, finite_number, latest_published_usage, measured_usage

LOGGER = logging.getLogger(__name__)
LOOKBACK_DAYS = 14


async def async_read_estimate(
    hass: HomeAssistant, pair: Mapping[str, Any]
) -> dict[str, Any]:
    """Read the same Recorder data and rate for setup and runtime."""
    statistic_id = pair[STATISTIC]
    price_entity = pair[PRICE]
    meter = electricity_meter(statistic_id)
    rates, tax = engie_tariff_entities(hass, meter, [price_entity]) if meter else ({}, None)
    tariff_sources = {
        f"{meter}_{metric}": (metric, rates[tariff])
        for metric, tariff in TARIFF_METRICS.items()
        if tariff in rates
    }
    now = datetime.now(UTC)
    offset = pair.get(DAYS_AGO)
    day, start, end = day_window(now, int(offset) if offset is not None else LOOKBACK_DAYS)
    if offset is None:
        today, end, _ = day_window(now, 0)
    results = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        start,
        end,
        {statistic_id, *tariff_sources},
        "hour",
        None,
        {"change"},
    )
    rows = results.get(statistic_id, [])
    if offset is None:
        latest = latest_published_usage(rows, day, today)
        day, usage = latest if latest is not None else (None, None)
    else:
        usage = measured_usage(rows)

    result = {
        "usage_date": day.isoformat() if day else None,
        "usage_kwh": usage,
        "rate_eur_per_kwh": current_rate(hass, price_entity),
    }
    if day and tariff_sources:
        next_day = day + timedelta(days=1)
        costs = {}
        for source, (metric, entity_id) in tariff_sources.items():
            usage_for_day = latest_published_usage(results.get(source, []), day, next_day)
            rate = current_rate(hass, entity_id)
            if usage_for_day is not None and rate is not None:
                costs[metric] = round(usage_for_day[1] * rate, 2)
        result["electricity_costs"] = costs
        result["electricity_costs_excl_vat"] = bool(tax)
    return result


def current_rate(hass: HomeAssistant, price_entity: str) -> float | None:
    """Get the finite EUR/kWh rate Home Assistant last received."""
    price_state = hass.states.get(price_entity)
    rate = None
    if (
        price_state
        and price_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == PRICE_UNIT
    ):
        rate = finite_number(price_state.state)
    return rate


def create_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> DataUpdateCoordinator:
    """Create the updater for one energy stream."""

    async def async_update():
        return await async_read_estimate(hass, entry.data)

    return DataUpdateCoordinator(
        hass,
        LOGGER,
        config_entry=entry,
        name=entry.title,
        update_interval=timedelta(minutes=15),
        update_method=async_update,
    )
