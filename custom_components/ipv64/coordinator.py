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

from .config_flow import get_account_info
from .const import CONF_API_KEY, DOMAIN, GET_DOMAIN_URL, TIMEOUT, UPDATE_URL

_LOGGER = logging.getLogger(__name__)


class IPv64DataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator for IPv64."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize IPv64 data updater."""
        _LOGGER.debug("Initialize IPv64 data updater")
        intervale = entry.options.get(CONF_SCAN_INTERVAL, 23)
        if intervale == 0:
            _LOGGER.info("IPv64 data updater disabled")

        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN}-{entry.entry_id}",
            update_interval=timedelta(intervale) if intervale > 0 else None,
        )

    async def _async_update_data(self):
        """Update the data from IPv64."""
        _LOGGER.debug("Update the data from IPv64")

        result_account_info = {}

        if isinstance(self.data, dict):
            self.data.update({CONF_DOMAIN: self.config_entry.data[CONF_DOMAIN]})
        else:
            self.data = {CONF_DOMAIN: self.config_entry.data[CONF_DOMAIN]}

        session: aiohttp.ClientSession = async_get_clientsession(self.hass)
        headers = {"Authorization": f"Bearer {self.config_entry.data[CONF_TOKEN]}"}

        async with async_timeout.timeout(TIMEOUT):
            result_account_info = await get_account_info(
                self.config_entry.data,
                {},
                session,
                headers=headers,
            )
        async with async_timeout.timeout(TIMEOUT):
            try:
                params = {"key": self.config_entry.data[CONF_API_KEY], CONF_HOST: self.config_entry.data[CONF_DOMAIN]}
                resp = await session.get(UPDATE_URL, params=params, raise_for_status=True)
                account_result = await resp.text()

                self.data.update({"update_result": account_result})

            except aiohttp.ClientResponseError as error:
                if error.status == 429:
                    _LOGGER.error(
                        "Your number of updates has been reached %i of %i. Error: %s | Status: %i",
                        result_account_info["dyndns_updates"],
                        result_account_info["daily_update_limit"],
                        error.message,
                        error.status,
                    )
                else:
                    _LOGGER.error("Your 'API Key' is incorrect. Error: %s | Status: %i", error.message, error.status)

        async with async_timeout.timeout(TIMEOUT):
            try:
                resp = await session.get(
                    GET_DOMAIN_URL,
                    headers=headers,
                    raise_for_status=True,
                )
                result = await resp.json()
                result_dict = {
                    "daily_update_limit": result_account_info["daily_update_limit"],
                    "dyndns_updates_today": result_account_info["dyndns_updates"],
                    "wildcard": result["subdomains"][self.config_entry.data[CONF_DOMAIN]]["wildcard"],
                    "total_updates_number": f"{result['subdomains'][self.config_entry.data[CONF_DOMAIN]]['updates']}",
                    CONF_IP_ADDRESS: result["subdomains"][self.config_entry.data[CONF_DOMAIN]]["records"][0]["content"],
                    "last_update": result["subdomains"][self.config_entry.data[CONF_DOMAIN]]["records"][0]["last_update"],
                }
                self.data.update(result_dict)
            except aiohttp.ClientResponseError as error:
                errors = {
                    "Account Update Token": "incorrect",
                    "daily_update_limit": "unlivable",
                    "dyndns_updates_today": "unlivable",
                    "wildcard": self.data["wildcard"] if self.data and "wildcard" in self.data else "unlivable",
                    "total_updates_number": f"{self.data['total_updates_number']}"
                    if self.data and "total_updates_number" in self.data
                    else "unlivable",
                    CONF_IP_ADDRESS: self.data[CONF_IP_ADDRESS] if self.data and CONF_IP_ADDRESS in self.data else "unlivable",
                    "last_update": self.data["last_update"] if self.data and "last_update" in self.data else "unlivable",
                }
                self.data.update(errors)
                _LOGGER.error("Your 'Account Update Token' is incorrect. Error: %s | Status: %i", error.message, error.status)
        return self.data
