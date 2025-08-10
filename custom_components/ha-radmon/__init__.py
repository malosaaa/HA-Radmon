"""The Radmon.org Scraper integration."""
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.dt import utcnow

from .api import RadmonScraper, RadmonScraperApiClientError
from .const import CONF_STATION_NAME, DEFAULT_SCAN_INTERVAL_MINUTES, DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = ["sensor"]

class RadmonDataUpdateCoordinator(DataUpdateCoordinator):
    """A custom DataUpdateCoordinator for Radmon to track update status."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.consecutive_errors = 0
        self.last_update_status = "OK"
        # CORRECTED: Renamed from last_update_timestamp to last_update_time to match the sensor key
        self.last_update_time: datetime | None = None

    async def _async_update_data(self) -> Any:
        # CORRECTED: Sets the correct attribute name
        self.last_update_time = utcnow()
        try:
            data = await self.update_method()
            self.consecutive_errors = 0
            self.last_update_status = "OK"
            return data
        except RadmonScraperApiClientError as err:
            self.consecutive_errors += 1
            self.last_update_status = str(err)
            _LOGGER.warning("Update failed for %s, consecutive errors: %d. Error: %s", self.name, self.consecutive_errors, err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Radmon.org Scraper from a config entry."""
    station_name = entry.data[CONF_STATION_NAME]
    session = async_get_clientsession(hass)
    client = RadmonScraper(station_name=station_name, session=session)

    coordinator = RadmonDataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"Radmon Scraper {station_name}",
        update_method=client.async_get_data,
        update_interval=timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES),
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok