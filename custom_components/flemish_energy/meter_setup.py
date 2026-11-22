"""The account and meter fields used by setup and reauthentication."""

import aiohttp
import probatio

from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector

from .fluvius.api import FluviusApiClient, FluviusApiError, FluviusAuthenticationError
from .fluvius.auth import FluviusAuthError, FluviusCredentialsError, async_get_bearer_token
from .fluvius.const import (
    CONF_EAN,
    CONF_EMAIL,
    CONF_METER_SERIAL,
    CONF_METER_TYPE,
    CONF_PASSWORD,
    METER_TYPE_OPTIONS,
)
from .fluvius.http import async_create_fluvius_session

LOGIN_FIELDS = {
    probatio.Required(CONF_EMAIL): selector.TextSelector(
        selector.TextSelectorConfig(type=selector.TextSelectorType.EMAIL)
    ),
    probatio.Required(CONF_PASSWORD): selector.TextSelector(
        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
    ),
}

LOGIN_SCHEMA = probatio.Schema(LOGIN_FIELDS)
METER_DETAILS_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_EAN): selector.TextSelector(),
        probatio.Required(CONF_METER_SERIAL): selector.TextSelector(),
        probatio.Required(CONF_METER_TYPE, default="electricity"): selector.SelectSelector(
            selector.SelectSelectorConfig(options=list(METER_TYPE_OPTIONS), translation_key="meter_type")
        ),
    }
)

METER_SCHEMA = LOGIN_SCHEMA.extend(METER_DETAILS_SCHEMA.schema)


async def async_check_login(hass: HomeAssistant, email: str, password: str) -> None:
    """Verify that Mijn Fluvius accepts the account before asking about meters."""
    session = async_create_fluvius_session(hass)
    try:
        await async_get_bearer_token(session, email, password)
    except FluviusCredentialsError as err:
        raise FluviusAuthenticationError("Fluvius rejected the credentials") from err
    except (FluviusAuthError, aiohttp.ClientError, TimeoutError) as err:
        raise FluviusApiError("Cannot verify the Fluvius login") from err
    finally:
        await session.close()


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
