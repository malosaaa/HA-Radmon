"""Sensor platform for Radmon.org Scraper."""
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_STATION_NAME, DOMAIN

# Descriptions for the main data sensors
SENSOR_TYPES = (
    SensorEntityDescription(key="cpm", name="CPM", native_unit_of_measurement="cpm", icon="mdi:radioactive", state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="usv_ph", name="Dose Rate", native_unit_of_measurement="\u00b5Sv/h", icon="mdi:chart-bell-curve", state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=4),
)
# Descriptions for the diagnostic sensors
DIAGNOSTIC_SENSOR_TYPES = (
    SensorEntityDescription(key="consecutive_errors", name="Consecutive Update Errors", native_unit_of_measurement="errors", icon="mdi:alert-circle-outline", state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
    SensorEntityDescription(key="last_update_status", name="Last Update Status", icon="mdi:check-circle-outline", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
    SensorEntityDescription(key="last_update_time", name="Last Update Time", device_class=SensorDeviceClass.TIMESTAMP, entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    station_name = entry.data[CONF_STATION_NAME]
    entities = [RadmonScrapeSensor(coordinator, description, station_name) for description in SENSOR_TYPES]
    entities.extend([RadmonDiagnosticSensor(coordinator, description, station_name) for description in DIAGNOSTIC_SENSOR_TYPES])
    async_add_entities(entities)

class RadmonScrapeSensor(CoordinatorEntity, RestoreEntity, SensorEntity):
    """Representation of a Radmon.org data sensor."""
    def __init__(self, coordinator, description: SensorEntityDescription, station_name: str):
        super().__init__(coordinator)
        self.entity_description = description
        self._station_name = station_name
        self._attr_name = f"Radmon {station_name} {description.name}"
        self._attr_unique_id = f"{DOMAIN}_{self._station_name}_{self.entity_description.key}".lower()
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._station_name.lower())},
            name=f"Radmon Station {station_name}",
            manufacturer="Radmon.org",
            # ADDED: Credit in the model name
            model="Scraped Station (by TranQuiL)",
            configuration_url=f"https://radmon.org/index.php?option=com_content&view=article&id=30&station={self._station_name}",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) and (self.native_value is None):
            self._attr_native_value = last_state.state
            self.async_write_ha_state()

    @property
    def native_value(self):
        if self.coordinator.data:
            return self.coordinator.data.get(self.entity_description.key)
        return None

    @property
    def extra_state_attributes(self):
        if self.coordinator.data:
            return {"last_updated": self.coordinator.data.get("last_updated"), "location": self.coordinator.data.get("location")}
        return {}

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data:
            self._attr_native_value = self.coordinator.data.get(self.entity_description.key)
            self.async_write_ha_state()

class RadmonDiagnosticSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Radmon.org diagnostic sensor."""
    def __init__(self, coordinator, description: SensorEntityDescription, station_name: str):
        super().__init__(coordinator)
        self.entity_description = description
        self._station_name = station_name
        self._attr_name = f"Radmon {station_name} {description.name}"
        self._attr_unique_id = f"{DOMAIN}_{self._station_name}_{self.entity_description.key}".lower()
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, self._station_name.lower())}, name=f"Radmon Station {station_name}")

    @property
    def native_value(self):
        # This now correctly reads `self.coordinator.last_update_time` because we fixed the coordinator
        return getattr(self.coordinator, self.entity_description.key, None)

    @property
    def icon(self):
        if self.entity_description.key == "last_update_status":
            return "mdi:check-circle-outline" if self.native_value == "OK" else "mdi:alert-circle-outline"
        return self.entity_description.icon