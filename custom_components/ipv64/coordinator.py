"""Coordinator for IPv64"""
from __future__ import annotations

import ipaddress
import logging
from datetime import timedelta

import aiohttp
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DOMAIN, CONF_HOST, CONF_IP_ADDRESS, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .config_flow import APIKeyError, get_account_info
from .const import (
    CHECKIP_URL,
    CONF_API_ECONOMY,
    CONF_API_KEY,
    CONF_DAILY_UPDATE_LIMIT,
    CONF_DYNDNS_UPDATE_TODAY,
    CONF_DYNDNS_UPDATES,
    CONF_WILDCARD,
    DOMAIN,
    GET_DOMAIN_URL,
    TIMEOUT,
    UPDATE_URL,
)

_LOGGER = logging.getLogger(__name__)


async def get_domain(session: aiohttp.ClientSession, headers: dict, result_account_info, data, config_entry):
    if not isinstance(data, dict):
        return dict(data)
    async with async_timeout.timeout(TIMEOUT):
        try:
            resp_get_domain = await session.get(GET_DOMAIN_URL, headers=headers, raise_for_status=True)
            result_get_domain = await resp_get_domain.json()
            result_dict = {
                CONF_DAILY_UPDATE_LIMIT: result_account_info[CONF_DAILY_UPDATE_LIMIT],
                CONF_DYNDNS_UPDATE_TODAY: result_account_info[CONF_DYNDNS_UPDATES],
                CONF_WILDCARD: result_get_domain["subdomains"][config_entry.data[CONF_DOMAIN]][CONF_WILDCARD],
                "total_updates_number": f"{result_get_domain['subdomains'][config_entry.data[CONF_DOMAIN]]['updates']}",
                CONF_IP_ADDRESS: result_get_domain["subdomains"][config_entry.data[CONF_DOMAIN]]["records"][0]["content"],
                "last_update": result_get_domain["subdomains"][config_entry.data[CONF_DOMAIN]]["records"][0]["last_update"],
            }
            data.update(result_dict)

            sub_domains_list = []

            for subdomain, values in result_get_domain["subdomains"].items():
                if subdomain == config_entry.data[CONF_DOMAIN]:
                    continue
                more_result_dict = {
                    CONF_DOMAIN: subdomain,
                    CONF_IP_ADDRESS: values["records"][0]["content"],
                    "last_update": values["records"][0]["last_update"],
                }
                sub_domains_list.append(more_result_dict)
            data["subdomains"] = sub_domains_list
        except aiohttp.ClientResponseError as error:
            errors = {
                "Account Update Token": "incorrect",
                CONF_DAILY_UPDATE_LIMIT: "unlivable",
                CONF_DYNDNS_UPDATE_TODAY: "unlivable",
                CONF_WILDCARD: data[CONF_WILDCARD] if data and CONF_WILDCARD in data else "unlivable",
                "total_updates_number": f"{data['total_updates_number']}"
                if data and "total_updates_number" in data
                else "unlivable",
                CONF_IP_ADDRESS: data[CONF_IP_ADDRESS] if data and CONF_IP_ADDRESS in data else "unlivable",
                "last_update": data["last_update"] if data and "last_update" in data else "unlivable",
            }
            data.update(errors)
            _LOGGER.error("Your 'Account Update Token' is incorrect. Error: %s | Status: %i", error.message, error.status)

    return data


class IPv64DataUpdateCoordinator(DataUpdateCoordinator):
    """DataUpdateCoordinator for IPv64."""

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
            update_interval=timedelta(minutes=intervale) if intervale > 0 else None,
        )

    async def _async_update_data(self):
        """Update the data from IPv64.net"""
        _LOGGER.debug("Update the data from IPv64.net")

        result_account_info = {}

        if isinstance(self.data, dict):
            self.data.update({CONF_DOMAIN: self.config_entry.data[CONF_DOMAIN]})
        else:
            self.data = {CONF_DOMAIN: self.config_entry.data[CONF_DOMAIN]}

        session: aiohttp.ClientSession = async_get_clientsession(self.hass)
        headers = {"Authorization": f"Bearer {self.config_entry.data[CONF_API_KEY]}"}

        try:
            result_account_info = await get_account_info(self.config_entry.data, {}, session, headers=headers)
        except APIKeyError:
            result_account_info[CONF_DYNDNS_UPDATES] = "unlivable"
            result_account_info[CONF_DAILY_UPDATE_LIMIT] = "unlivable"

        self.data = await get_domain(session, headers, result_account_info, self.data, self.config_entry)

        ip_is_not_changed = False

        if (
            hasattr(self.config_entry, "options")
            and CONF_API_ECONOMY in self.config_entry.options
            and self.config_entry.options[CONF_API_ECONOMY]
        ):
            _LOGGER.debug("API-KEY-ECONOMY")
            async with async_timeout.timeout(TIMEOUT):
                try:
                    request = await session.get(CHECKIP_URL, raise_for_status=True)
                    ip1_obj = ipaddress.ip_address(self.data[CONF_IP_ADDRESS])
                    ip2_obj = ipaddress.ip_address((await request.text()).strip())
                    ip_is_not_changed = ip1_obj == ip2_obj
                except (ValueError or KeyError or aiohttp.ClientResponseError or aiohttp.ClientConnectorError):
                    pass

        if not ip_is_not_changed:
            async with async_timeout.timeout(TIMEOUT):
                try:
                    params = {"key": self.config_entry.data[CONF_API_KEY], CONF_HOST: self.config_entry.data[CONF_DOMAIN]}
                    resp = await session.get(UPDATE_URL, params=params, raise_for_status=True)
                    update_result = await resp.text()

                    self.data.update({"update_result": update_result})

                except aiohttp.ClientResponseError as error:
                    if error.status == 429:
                        _LOGGER.error(
                            "Your number of updates has been reached %i of %i. Error: %s | Status: %i",
                            result_account_info[CONF_DYNDNS_UPDATES],
                            result_account_info[CONF_DAILY_UPDATE_LIMIT],
                            error.message,
                            error.status,
                        )
                    else:
                        _LOGGER.error("Your 'API Key' is incorrect. Error: %s | Status: %i", error.message, error.status)
        return self.data
