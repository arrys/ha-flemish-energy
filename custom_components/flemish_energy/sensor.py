"""Expose estimates based on measured usage and the current ENGIE rate."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up a separately labeled estimate for each energy stream."""
    async_add_entities([EstimateSensor(entry.runtime_data, entry)])


class EstimateSensor(CoordinatorEntity, SensorEntity):
    """Show the value of published energy at the current rate."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Use a persistent ID and the label the user entered."""
        super().__init__(coordinator)
        self._attr_name = entry.title
        self._attr_unique_id = f"{entry.entry_id}_estimate"

    @property
    def extra_state_attributes(self):
        """Expose the date, usage, and rate behind the estimate."""
        return self.coordinator.data

    @property
    def native_value(self) -> float | None:
        """Estimate the amount in EUR when both sources have data."""
        usage = self.coordinator.data["usage_kwh"]
        rate = self.coordinator.data["rate_eur_per_kwh"]
        if usage is None or rate is None:
            return None
        return round(usage * rate, 2)
