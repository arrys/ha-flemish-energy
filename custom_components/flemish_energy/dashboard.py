"""Provide a managed Lovelace view for verified Flemish Energy sources."""

import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from homeassistant.components import frontend
from homeassistant.components.lovelace import LOVELACE_DATA
from homeassistant.components.lovelace.dashboard import LovelaceConfig
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import list_statistic_ids
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.json import cached_json_fragment

from .const import DOMAIN, ENTRY_KIND, PIDPA_METER, PRICE, STATISTIC, WATER_SENSOR
from .electricity import SERIES, electricity_meter, electricity_series, engie_tariff_rows

LOGGER = logging.getLogger(__name__)

TITLE = "Energy & Costs"
PATH = "flemish-energy"
ICON = "mdi:transmission-tower"
WATER_ICON = "mdi:water"

ESTIMATES = """Each estimate values published usage for the displayed day at the current contract rate.

{% for entity in integration_entities('flemish_energy') | sort %}
{% if state_attr(entity, 'flemish_energy_estimate') %}
{% set day = state_attr(entity, 'usage_date') %}
{% set usage = state_attr(entity, 'usage_kwh') %}
{% set rate = state_attr(entity, 'rate_eur_per_kwh') %}

**{{ (state_attr(entity, 'friendly_name') or entity) | e }}**{% if day %} · {{ day }}{% endif %}

{% if has_value(entity) and usage is not none and rate is not none %}
**€{{ '%.2f' | format(states(entity) | float) }}** · {{ usage | round(3) }} kWh × €{{ rate }}/kWh
{% elif usage is none and (day or rate is not none) %}
Waiting for published readings.
{% elif rate is none and day %}
Waiting for the ENGIE rate.
{% else %}
Estimate unavailable.
{% endif %}
{% endif %}
{% else %}
Add a meter and rate through the Flemish Energy setup wizard.
{% endfor %}
"""


class EnergyCostsDashboard(LovelaceConfig):
    """Build the dashboard from the integration's loaded entries."""

    def __init__(self, hass: HomeAssistant, path: str) -> None:
        super().__init__(
            hass,
            path,
            {
                "id": path,
                "title": TITLE,
                "icon": ICON,
                "mode": "yaml",
                "require_admin": False,
                "show_in_sidebar": True,
            },
        )
        self.sources: dict[str, ConfigEntry] = {}

    @property
    def mode(self) -> str:
        """Expose the integration-managed view as read-only in Lovelace."""
        return "yaml"

    async def async_get_info(self) -> dict[str, Any]:
        return {"mode": self.mode, "views": 1}

    async def async_load(self, force: bool) -> dict[str, Any]:
        charts = []
        electricity = {}
        water_cards = []
        for entry in sorted(self.sources.values(), key=lambda item: item.title.casefold()):
            if entry.data.get(ENTRY_KIND) == PIDPA_METER:
                entity_id = entry.data[WATER_SENSOR]
                water_cards.append({
                    "type": "tile", "entity": entity_id, "name": entry.title, "icon": WATER_ICON,
                })
                water_cards.append(self._usage_chart(entity_id, entry.title))
                continue
            if meter := electricity_meter(entry.data[STATISTIC]):
                electricity.setdefault(meter, []).append(entry)
            else:
                charts.append(self._usage_chart(entry.data[STATISTIC], entry.title))

        sections = []
        if electricity:
            sections.append({
                "type": "grid",
                "column_span": 2,
                "cards": await self._async_electricity_cards(electricity),
            })
        if charts:
            sections.append({
                "type": "grid",
                "cards": [
                    {"type": "heading", "heading": "Published usage · 30 days"},
                    *charts,
                ],
            })
        if charts or electricity:
            sections.append({
                "type": "grid",
                "cards": [
                    {"type": "heading", "heading": "Current-rate estimates"},
                    {
                        "type": "markdown",
                        "content": ESTIMATES,
                        "grid_options": {"columns": "full"},
                    },
                ],
            })
        if water_cards:
            sections.append({
                "type": "grid",
                "cards": [
                    {"type": "heading", "heading": "Water usage · 30 days", "icon": WATER_ICON},
                    *water_cards,
                ],
            })

        return {
            "title": TITLE,
            "views": [
                {
                    "title": TITLE,
                    "path": "energy",
                    "icon": ICON,
                    "type": "sections",
                    "max_columns": 2,
                    "sections": sections,
                },
            ],
        }

    async def _async_electricity_cards(
        self, meters: dict[str, list[ConfigEntry]]
    ) -> list[dict[str, Any]]:
        """Build one import/export chart per meter from existing Recorder sources."""
        candidates = {f"{meter}_{metric}" for meter in meters for metric in SERIES}
        available = {entry.data[STATISTIC] for entries in meters.values() for entry in entries}
        try:
            metadata = await get_instance(self.hass).async_add_executor_job(
                list_statistic_ids, self.hass, candidates
            )
            available.update(item["statistic_id"] for item in metadata if item["has_sum"])
        except (HomeAssistantError, SQLAlchemyError, ValueError):
            LOGGER.debug("Could not discover related electricity statistics", exc_info=True)

        cards: list[dict[str, Any]] = [
            {"type": "heading", "heading": "Electricity · 30 days", "icon": ICON}
        ]
        for meter, entries in meters.items():
            meter_id = meter.split(":", 1)[1].split("_electricity_", 1)[0]
            title = (
                "Grid import and export"
                if len(meters) == 1
                else f"Grid import and export · Meter …{meter_id[-4:].upper()}"
            )
            cards.append({
                **self._usage_chart(entries[0].data[STATISTIC], title),
                "entities": electricity_series(meter, available),
                "expand_legend": True,
                "min_y_axis": 0,
            })
            if rates := engie_tariff_rows(self.hass, meter, (entry.data[PRICE] for entry in entries)):
                cards.append({
                    "type": "entities",
                    "title": "Current ENGIE tariffs",
                    "show_header_toggle": False,
                    "entities": rates,
                    "grid_options": {"columns": "full"},
                })
        return cards

    @staticmethod
    def _usage_chart(source: str, title: str) -> dict[str, Any]:
        return {
            "type": "statistics-graph",
            "title": title,
            "entities": [{"entity": source, "name": title}],
            "chart_type": "bar",
            "stat_types": ["change"],
            "period": "day",
            "days_to_show": 30,
            "grid_options": {"columns": "full"},
        }

    async def async_json(self, force: bool):
        return cached_json_fragment(await self.async_load(force))

    @callback
    def async_add_source(self, entry: ConfigEntry) -> None:
        self.sources[entry.entry_id] = entry
        self._config_updated()

    @callback
    def async_remove_source(self, entry: ConfigEntry) -> None:
        self.sources.pop(entry.entry_id, None)
        self._config_updated()


@callback
def async_add_dashboard_source(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register one sidebar panel and attach the loaded source."""
    if dashboard := hass.data.get(DOMAIN):
        dashboard.async_add_source(entry)
        return

    dashboards = hass.data[LOVELACE_DATA].dashboards
    path = PATH
    suffix = 2
    while path in dashboards or frontend.async_panel_exists(hass, path):
        path = f"{PATH}-{suffix}"
        suffix += 1

    dashboard = EnergyCostsDashboard(hass, path)
    dashboards[path] = dashboard
    try:
        frontend.async_register_built_in_panel(
            hass,
            "lovelace",
            frontend_url_path=path,
            sidebar_title=TITLE,
            sidebar_icon=ICON,
            show_in_sidebar=True,
            config={"mode": dashboard.mode},
        )
    except ValueError:
        dashboards.pop(path)
        raise

    hass.data[DOMAIN] = dashboard
    dashboard.async_add_source(entry)


@callback
def async_remove_dashboard_source(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the source and unregister the owned panel after the last unload."""
    dashboard = hass.data[DOMAIN]
    dashboard.async_remove_source(entry)
    if dashboard.sources:
        return

    hass.data.pop(DOMAIN)
    hass.data[LOVELACE_DATA].dashboards.pop(dashboard.url_path)
    frontend.async_remove_panel(hass, dashboard.url_path)
