"""API for Radmon.org Scraper."""
import asyncio
import logging
import socket
from typing import Any, Dict

import aiohttp
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

# The commonly accepted conversion factor for an SBM-20 Geiger tube.
# This is used to calculate the dose rate from CPM, as it's not provided on the page.
SBM20_CONVERSION_FACTOR = 0.0057  # µSv/h per CPM

class RadmonScraperApiClientError(Exception):
    """Exception to indicate a general API error."""

class RadmonScraperCannotConnect(RadmonScraperApiClientError):
    """Exception to indicate a connection error."""

class RadmonScraperInvalidStation(RadmonScraperApiClientError):
    """Exception to indicate an invalid station ID or missing data on the page."""

class RadmonScraper:
    """A class for scraping radiation data from Radmon.org's station article page."""

    def __init__(self, station_name: str, session: aiohttp.ClientSession):
        """Initialize the scraper."""
        self._station_name = station_name
        self._session = session
        self._url = f"https://radmon.org/index.php?option=com_content&view=article&id=30&station={self._station_name}"

    async def async_get_data(self) -> Dict[str, Any]:
        """Fetch and parse data from the Radmon.org station page."""
        try:
            async with self._session.get(self._url) as response:
                if response.status == 404:
                    raise RadmonScraperInvalidStation(f"Station '{self._station_name}' not found (404 error).")
                response.raise_for_status()
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                # --- Data Extraction Logic ---
                scraped_data = {}

                # 1. Extract CPM and Last Updated from <h2 class="serif">
                h2_tag = soup.find("h2", class_="serif")
                if not h2_tag:
                    raise RadmonScraperInvalidStation("Could not find the data header (h2 tag) on the page.")

                h2_text = h2_tag.get_text(strip=True)
                # Example text: "15 CPM on 2025-08-09 19:14:01"
                parts = h2_text.split(" CPM on ")
                if len(parts) != 2:
                    raise RadmonScraperInvalidStation(f"Unexpected data format in h2 tag: {h2_text}")

                cpm_value = float(parts[0])
                scraped_data["cpm"] = cpm_value
                scraped_data["last_updated"] = parts[1]

                # 2. Calculate Dose Rate (uSv/h) from CPM
                # The page indicates an SBM-20 tube, so we use its conversion factor.
                scraped_data["usv_ph"] = round(cpm_value * SBM20_CONVERSION_FACTOR, 4)

                # 3. Extract Location from <h3 class="serif">
                h3_tag = soup.find("h3", class_="serif")
                if h3_tag and h3_tag.contents:
                    # The location is the first part of the h3, before the <br> tag
                    location_text = h3_tag.contents[0].strip()
                    scraped_data["location"] = location_text
                else:
                    scraped_data["location"] = self._station_name # Fallback

                return scraped_data

        except asyncio.TimeoutError as exception:
            raise RadmonScraperCannotConnect("Timeout error fetching data") from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise RadmonScraperCannotConnect("Error connecting to Radmon.org") from exception
        except Exception as exception:
            _LOGGER.error("An unexpected error occurred during scraping: %s", exception)
            raise RadmonScraperApiClientError from exception