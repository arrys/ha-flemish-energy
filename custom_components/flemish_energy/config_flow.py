"""Guide the user through checking and pairing their energy sources."""

from collections.abc import Mapping
import logging
from typing import Any

import probatio
from sqlalchemy.exc import SQLAlchemyError

from homeassistant import config_entries
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import list_statistic_ids
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er, selector

from .const import DAYS_AGO, DOMAIN, ENERGY_UNIT, LABEL, PRICE, PRICE_UNIT, STATISTIC
from .coordinator import async_read_estimate

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
            if item["statistic_id"].startswith("fluvius:")
            and item["statistics_unit_of_measurement"] == ENERGY_UNIT
            and item["display_unit_of_measurement"] == ENERGY_UNIT
        }

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show account setup instructions and recheck prerequisites on submit."""
        engie_ready = self._has_loaded_entry("engie_be")
        fluvius_ready = self._has_loaded_entry("fluvius")
        statistics = {}
        errors = {}
        if fluvius_ready:
            try:
                statistics = await self._async_statistics()
            except RECORDER_ERRORS:
                LOGGER.debug("Could not check Fluvius statistics", exc_info=True)
                errors["base"] = "recorder_unavailable"

        if user_input is not None and not errors:
            if not engie_ready or not fluvius_ready:
                errors["base"] = "providers_not_ready"
            elif not statistics:
                errors["base"] = "no_statistics"
            else:
                return self._show_pair_form(statistics)

        return self.async_show_form(
            step_id="user",
            data_schema=probatio.Schema({}),
            description_placeholders={
                "engie_status": "Loaded" if engie_ready else "Needs setup or repair",
                "fluvius_status": "Loaded" if fluvius_ready else "Needs setup or repair",
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
            return await self.async_step_user()
        if not statistics:
            return await self.async_step_user()
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
