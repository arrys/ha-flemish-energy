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
from .estimate import day_window, finite_number, measured_usage

LOGGER = logging.getLogger(__name__)


async def async_read_estimate(
    hass: HomeAssistant, pair: Mapping[str, Any]
) -> dict[str, str | float | None]:
    """Read the same Recorder data and rate for setup and runtime."""
    statistic_id = pair[STATISTIC]
    price_entity = pair[PRICE]
    day, start, end = day_window(datetime.now(UTC), int(pair[DAYS_AGO]))
    results = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        start,
        end,
        {statistic_id},
        "hour",
        None,
        {"change"},
    )
    price_state = hass.states.get(price_entity)
    rate = None
    if (
        price_state
        and price_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == PRICE_UNIT
    ):
        rate = finite_number(price_state.state)

    return {
        "usage_date": day.isoformat(),
        "usage_kwh": measured_usage(results.get(statistic_id, [])),
        "rate_eur_per_kwh": rate,
    }


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
