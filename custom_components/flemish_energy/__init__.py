"""Set up Flemish Energy."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import create_coordinator
from .const import ENTRY_KIND, FLUVIUS_METER
from .dashboard import async_add_dashboard_source, async_remove_dashboard_source
from .fluvius import async_setup_entry as async_setup_meter


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the estimate sensor for this tariff."""
    if entry.data.get(ENTRY_KIND) == FLUVIUS_METER:
        return await async_setup_meter(hass, entry)

    entry.runtime_data = create_coordinator(hass, entry)
    await entry.runtime_data.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    async_add_dashboard_source(hass, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the estimate sensor."""
    if not await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR]):
        return False
    if entry.data.get(ENTRY_KIND) != FLUVIUS_METER:
        async_remove_dashboard_source(hass, entry)
    return True
