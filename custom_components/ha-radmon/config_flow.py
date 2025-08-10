"""Config flow for Radmon.org Scraper."""
import logging
from typing import Any, Dict

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    RadmonScraper,
    RadmonScraperCannotConnect,
    RadmonScraperInvalidStation,
)
from .const import CONF_STATION_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STATION_NAME): str,
    }
)

async def validate_input(hass, data: Dict[str, Any]) -> None:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass)
    client = RadmonScraper(station_name=data[CONF_STATION_NAME], session=session)
    await client.async_get_data()


class RadmonScrapeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Radmon.org Scraper."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            station_name = user_input[CONF_STATION_NAME]
            await self.async_set_unique_id(station_name.lower())
            self._abort_if_unique_id_configured()

            try:
                await validate_input(self.hass, user_input)
            except RadmonScraperCannotConnect:
                errors["base"] = "cannot_connect"
            except RadmonScraperInvalidStation:
                errors["base"] = "invalid_station"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                title = f"Radmon {station_name}"
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )