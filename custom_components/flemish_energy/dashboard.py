"""Provide a managed Lovelace view for verified Flemish Energy sources."""

from typing import Any

from homeassistant.components import frontend
from homeassistant.components.lovelace import LOVELACE_DATA
from homeassistant.components.lovelace.dashboard import LovelaceConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.json import cached_json_fragment

from .const import DOMAIN, STATISTIC

TITLE = "Energy & Costs"
PATH = "flemish-energy"
ICON = "mdi:transmission-tower"

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
        charts = [
            {
                "type": "statistics-graph",
                "title": entry.title,
                "entities": [{"entity": entry.data[STATISTIC], "name": entry.title}],
                "chart_type": "bar",
                "stat_types": ["change"],
                "period": "day",
                "days_to_show": 30,
                "grid_options": {"columns": "full"},
            }
            for entry in sorted(self.sources.values(), key=lambda item: item.title.casefold())
        ]
        return {
            "title": TITLE,
            "views": [
                {
                    "title": TITLE,
                    "path": "energy",
                    "icon": ICON,
                    "type": "sections",
                    "max_columns": 2,
                    "sections": [
                        {
                            "type": "grid",
                            "cards": [
                                {"type": "heading", "heading": "Published usage · 30 days"},
                                *charts,
                            ],
                        },
                        {
                            "type": "grid",
                            "cards": [
                                {"type": "heading", "heading": "Current-rate estimates"},
                                {
                                    "type": "markdown",
                                    "content": ESTIMATES,
                                    "grid_options": {"columns": "full"},
                                },
                            ],
                        },
                    ],
                },
            ],
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
