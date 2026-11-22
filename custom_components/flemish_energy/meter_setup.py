"""The account and meter fields used by setup and reauthentication."""

import probatio

from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector

from .fluvius.api import FluviusApiClient
from .fluvius.const import (
    CONF_EAN,
    CONF_EMAIL,
    CONF_METER_SERIAL,
    CONF_METER_TYPE,
    CONF_PASSWORD,
    METER_TYPE_OPTIONS,
)
from .fluvius.http import async_create_fluvius_session

METER_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_EMAIL): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.EMAIL)
        ),
        probatio.Required(CONF_PASSWORD): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
        probatio.Required(CONF_EAN): selector.TextSelector(),
        probatio.Required(CONF_METER_SERIAL): selector.TextSelector(),
        probatio.Required(CONF_METER_TYPE, default="electricity"): selector.SelectSelector(
            selector.SelectSelectorConfig(options=list(METER_TYPE_OPTIONS), translation_key="meter_type")
        ),
    }
)

METER_DETAILS_SCHEMA = probatio.Schema(
    {
        field: validator
        for field, validator in METER_SCHEMA.schema.items()
        if field.schema not in (CONF_EMAIL, CONF_PASSWORD)
    }
)


async def async_check_meter(hass: HomeAssistant, data: dict) -> int:
    """Check the login and count the daily summaries available for the meter."""
    session = async_create_fluvius_session(hass)
    try:
        client = FluviusApiClient(
            session=session,
            email=data[CONF_EMAIL],
            password=data[CONF_PASSWORD],
            ean=data[CONF_EAN],
            meter_serial=data[CONF_METER_SERIAL],
            meter_type=data[CONF_METER_TYPE],
        )
        return len(await client.fetch_daily_summaries())
    finally:
        await session.close()
