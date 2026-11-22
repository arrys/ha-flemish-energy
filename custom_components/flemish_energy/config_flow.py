"""Guide the user through checking and pairing their energy sources."""

from collections.abc import Mapping
import logging
import re
from typing import Any

import probatio
from sqlalchemy.exc import SQLAlchemyError

from homeassistant import config_entries
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import list_statistic_ids
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er, selector

from .const import (
    DAYS_AGO,
    DOMAIN,
    ENERGY_UNIT,
    ENTRY_KIND,
    FLUVIUS_METER,
    LABEL,
    PRICE,
    PRICE_UNIT,
    STATISTIC,
)
from .coordinator import async_read_estimate
from .fluvius.api import FluviusApiError, FluviusAuthenticationError
from .fluvius.const import (
    CONF_EAN,
    CONF_EMAIL,
    CONF_METER_SERIAL,
    CONF_METER_TYPE,
    CONF_PASSWORD,
)
from .meter_setup import METER_SCHEMA, async_check_meter

LOGGER = logging.getLogger(__name__)
RECORDER_ERRORS = (HomeAssistantError, SQLAlchemyError)


class FlemishEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create one verified estimate per consumption or injection statistic."""

    VERSION = 1

    _pair: dict[str, Any]
    _preview: dict[str, str]

    def _has_loaded_entry(self, domain: str) -> bool:
        return any(
            entry.state is config_entries.ConfigEntryState.LOADED
            for entry in self.hass.config_entries.async_entries(domain)
        )

    async def _async_statistics(self) -> dict[str, str]:
        metadata = await get_instance(self.hass).async_add_executor_job(
            list_statistic_ids, self.hass, None, "sum"
        )
        return {
            item["statistic_id"]: item["name"] or item["statistic_id"]
            for item in metadata
            if item["statistic_id"].startswith((f"{DOMAIN}:", "fluvius:"))
            and "_sharing_" not in item["statistic_id"]
            and item["statistics_unit_of_measurement"] == ENERGY_UNIT
            and item["display_unit_of_measurement"] == ENERGY_UNIT
        }

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Start with a short checklist and let the user choose the next task."""
        meters = sum(
            entry.data.get(ENTRY_KIND) == FLUVIUS_METER
            and entry.state is config_entries.ConfigEntryState.LOADED
            for entry in self._async_current_entries()
        )
        return self.async_show_menu(
            step_id="user",
            menu_options=["meter", "readiness"],
            description_placeholders={
                "meter_count": str(meters),
                "engie_status": "Connected" if self._has_loaded_entry("engie_be") else "Needs setup",
            },
        )

    async def async_step_meter(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Verify the Mijn Fluvius login and meter before saving."""
        return await self._async_meter_form("meter", user_input)

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Let the user update the login when Fluvius rejects it."""
        return await self.async_step_meter_reauth()

    async def async_step_meter_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        return await self._async_meter_form("meter_reauth", user_input)

    async def _async_meter_form(
        self, step_id: str, user_input: dict[str, Any] | None
    ) -> config_entries.ConfigFlowResult:
        reauth_entry = self._get_reauth_entry() if step_id == "meter_reauth" else None
        errors = {}
        previous = reauth_entry.data if reauth_entry else {}
        defaults = previous if reauth_entry else getattr(self, "_meter", {})
        suggested = {key: value for key, value in defaults.items() if key != CONF_PASSWORD}
        if user_input is not None:
            data = {
                **user_input,
                CONF_EMAIL: user_input[CONF_EMAIL].strip(),
                CONF_EAN: "".join(user_input[CONF_EAN].split()),
                CONF_METER_SERIAL: user_input[CONF_METER_SERIAL].strip().upper(),
                ENTRY_KIND: FLUVIUS_METER,
            }
            suggested.update({key: value for key, value in data.items() if key != CONF_PASSWORD})
            if not re.fullmatch(r"[0-9]{18}", data[CONF_EAN]):
                errors[CONF_EAN] = "invalid_ean"
            if not re.fullmatch(r"[A-Z0-9-]+", data[CONF_METER_SERIAL]):
                errors[CONF_METER_SERIAL] = "invalid_serial"
            if reauth_entry and any(
                data[key] != previous[key]
                for key in (CONF_EAN, CONF_METER_SERIAL, CONF_METER_TYPE)
            ):
                errors["base"] = "wrong_meter"
            if not errors:
                try:
                    count = await async_check_meter(self.hass, data)
                except FluviusAuthenticationError:
                    errors["base"] = "fluvius_auth"
                except FluviusApiError:
                    errors["base"] = "fluvius_connection"
                else:
                    if reauth_entry and count:
                        return self.async_update_reload_and_abort(reauth_entry, data=data)
                    if not count:
                        errors["base"] = "fluvius_empty"
                    else:
                        self._meter = data
                        self._meter_count = count
                        return await self.async_step_meter_verified()

        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(METER_SCHEMA, suggested),
            errors=errors,
        )

    async def async_step_meter_verified(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show the successful verification before saving the meter."""
        return self.async_show_menu(
            step_id="meter_verified",
            menu_options=["save_meter", "meter"],
            description_placeholders={
                "reading_count": str(self._meter_count),
                "serial_suffix": self._meter[CONF_METER_SERIAL][-4:],
            },
        )

    async def async_step_save_meter(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Create a meter entry using the verified identifiers."""
        data = self._meter
        ean = data[CONF_EAN]
        serial = data[CONF_METER_SERIAL]
        await self.async_set_unique_id(f"{ean}_{serial.lower().replace('-', '_')}")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=f"Fluvius {data[CONF_METER_TYPE]} · {serial[-4:]}", data=data
        )

    async def async_step_readiness(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Explain which source has to be connected before pairing."""
        engie_ready = self._has_loaded_entry("engie_be")
        statistics = {}
        errors = {}
        try:
            statistics = await self._async_statistics()
        except RECORDER_ERRORS:
            LOGGER.debug("Could not check Fluvius statistics", exc_info=True)
            errors["base"] = "recorder_unavailable"

        if user_input is not None and not errors:
            if not engie_ready:
                errors["base"] = "providers_not_ready"
            elif not statistics:
                errors["base"] = "no_statistics"
            else:
                return self._show_pair_form(statistics)

        return self.async_show_form(
            step_id="readiness",
            data_schema=probatio.Schema({}),
            description_placeholders={
                "engie_status": "Loaded" if engie_ready else "Needs setup or repair",
                "statistic_count": "—" if errors.get("base") == "recorder_unavailable" else str(len(statistics)),
            },
            errors=errors,
        )

    async def async_step_pair(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Check that the actual selected data can produce an estimate."""
        try:
            statistics = await self._async_statistics()
        except RECORDER_ERRORS:
            LOGGER.debug("Could not refresh Fluvius statistics", exc_info=True)
            return await self.async_step_readiness()
        if not statistics:
            return await self.async_step_readiness()
        if user_input is None:
            return self._show_pair_form(statistics, getattr(self, "_pair", None))

        errors = {}
        statistic_id = user_input[STATISTIC]
        label = user_input[LABEL].strip()
        entity = er.async_get(self.hass).async_get(user_input[PRICE])
        if statistic_id not in statistics:
            errors[STATISTIC] = "invalid_statistic"
        if not label:
            errors[LABEL] = "empty_label"
        if entity is None or entity.platform != "engie_be":
            errors[PRICE] = "invalid_price"
        if user_input[DAYS_AGO] not in range(1, 15):
            errors[DAYS_AGO] = "invalid_days"
        if errors:
            return self._show_pair_form(statistics, user_input, errors)

        pair = {**user_input, LABEL: label, DAYS_AGO: int(user_input[DAYS_AGO])}
        try:
            reading = await async_read_estimate(self.hass, pair)
        except RECORDER_ERRORS:
            LOGGER.debug("Could not read the selected Fluvius statistic", exc_info=True)
            return self._show_pair_form(
                statistics, user_input, {"base": "recorder_unavailable"}
            )

        usage = reading["usage_kwh"]
        rate = reading["rate_eur_per_kwh"]
        if usage is None:
            errors[DAYS_AGO] = "no_readings_for_day"
        if rate is None:
            errors[PRICE] = "price_unavailable"
        if errors:
            return self._show_pair_form(statistics, user_input, errors)

        self._pair = pair
        self._preview = {
            "label": label,
            "day": reading["usage_date"],
            "usage": f"{usage:.3f}",
            "rate": str(rate),
            "estimate": f"{usage * rate:.2f}",
        }
        return await self.async_step_review()

    def _show_pair_form(
        self,
        statistics: Mapping[str, str],
        user_input: dict[str, Any] | None = None,
        errors: dict[str, str] | None = None,
    ) -> config_entries.ConfigFlowResult:
        schema = probatio.Schema(
            {
                probatio.Required(LABEL): selector.TextSelector(),
                probatio.Required(STATISTIC): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=key, label=name)
                            for key, name in sorted(
                                statistics.items(), key=lambda item: (item[1], item[0])
                            )
                        ]
                    )
                ),
                probatio.Required(PRICE): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        filter=selector.EntityFilterSelectorConfig(
                            domain="sensor",
                            integration="engie_be",
                            unit_of_measurement=PRICE_UNIT,
                        )
                    )
                ),
                probatio.Required(DAYS_AGO, default=3): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=14, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="pair",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    async def async_step_review(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show verified values and let the user save or edit the pairing."""
        return self.async_show_menu(
            step_id="review",
            menu_options=["save", "pair"],
            description_placeholders=self._preview,
        )

    async def async_step_save(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Save the verified pairing."""
        await self.async_set_unique_id(self._pair[STATISTIC])
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=self._pair[LABEL], data=self._pair)
