"""Coordinator for IPv64"""
from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DOMAIN, CONF_HOST, CONF_IP_ADDRESS, CONF_SCAN_INTERVAL, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_API_KEY, DOMAIN, TIMEOUT

_LOGGER = logging.getLogger(__name__)


class IPv64DataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator for IPv64."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize IPv64 data updater."""
        _LOGGER.debug("Initialize IPv64 data updater")
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN}-{entry.entry_id}",
            update_interval=timedelta(minutes=entry.options.get(CONF_SCAN_INTERVAL, 23)),
        )

    async def _async_update_data(self):
        """Update the data from IPv64."""
        _LOGGER.debug("Update the data from IPv64")

        params = {"key": self.config_entry.data[CONF_API_KEY], CONF_HOST: self.config_entry.data[CONF_DOMAIN]}

        url_account_info = "https://ipv64.net/nic/update"
        session: aiohttp.ClientSession = async_get_clientsession(self.hass)
        async with async_timeout.timeout(TIMEOUT):
            try:
                resp = await session.get(
                    url_account_info,
                    params=params,
                    raise_for_status=True,
                )
                account_result = await resp.text()

                self.data = {CONF_DOMAIN: self.config_entry.data[CONF_DOMAIN], "update_result": account_result}

            except aiohttp.ClientResponseError as error:
                _LOGGER.error("Your 'API Key' is incorrect. Error: %s | Status: %i", error.message, error.status)
        if self.data and "update_result" in self.data:
            headers = {"Authorization": f"Bearer {self.config_entry.data[CONF_TOKEN]}"}

            url_domain = "https://ipv64.net/api.php?get_domains"
            async with async_timeout.timeout(TIMEOUT):
                try:
                    resp = await session.get(
                        url_domain,
                        headers=headers,
                        raise_for_status=True,
                    )
                    result = await resp.json()
                    result_dict = {
                        "wildcard": result["subdomains"][self.config_entry.data[CONF_DOMAIN]]["wildcard"],
                        "updates": f"{result['subdomains'][self.config_entry.data[CONF_DOMAIN]]['updates']}/{self.config_entry.data['dyndns_update_limit']}",
                        CONF_IP_ADDRESS: result["subdomains"][self.config_entry.data[CONF_DOMAIN]]["records"][0]["content"],
                        "last_update": result["subdomains"][self.config_entry.data[CONF_DOMAIN]]["records"][0]["last_update"],
                    }
                    self.data.update(result_dict)
                except aiohttp.ClientResponseError as error:
                    errors = {
                        "Account Update Token": "incorrect",
                        "wildcard": self.data["wildcard"] if self.data and "wildcard" in self.data else "unlivable",
                        "updates": f"{self.data['updates']}/{self.data['dyndns_update_limit']}"
                        if self.data and "updates" in self.data and "dyndns_update_limit" in self.data
                        else "unlivable",
                        CONF_IP_ADDRESS: self.data[CONF_IP_ADDRESS]
                        if self.data and CONF_IP_ADDRESS in self.data
                        else "unlivable",
                        "last_update": self.data["last_update"] if self.data and "last_update" in self.data else "unlivable",
                    }
                    self.data.update(errors)
                    _LOGGER.error(
                        "Your 'Account Update Token' is incorrect. Error: %s | Status: %i", error.message, error.status
                    )
        return self.data
