"""Coordinator for IPv64."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import ipaddress
import logging

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DOMAIN,
    CONF_IP_ADDRESS,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    CONF_TTL,
    CONF_TYPE,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .config_flow import APIKeyError, get_account_info
from .const import (
    CHECKIP_URL,
    CONF_API_ECONOMY,
    CONF_API_KEY,
    CONF_DAILY_UPDATE_LIMIT,
    CONF_DYNDNS_UPDATES,
    DOMAIN,
    GET_DOMAIN_URL,
    TIMEOUT,
    UPDATE_URL,
)

_LOGGER = logging.getLogger(__name__)


async def get_domain(session: aiohttp.ClientSession, headers: dict, data):
    """Fetches domain information from the IPv64.net API."""  # noqa: D401
    if not isinstance(data, dict):
        data = dict(data)
    async with asyncio.timeout(TIMEOUT):
        try:
            resp_get_domain = await session.get(GET_DOMAIN_URL, headers=headers, raise_for_status=True)
            result_get_domain = await resp_get_domain.json()
            subdomains: dict = result_get_domain["subdomains"]
            if not subdomains:
                return

            sub_domains_list = []

            for subdomain, values in subdomains.items():
                records: list = values["records"]
                if len(records) < 1 or subdomain != data[CONF_DOMAIN]:
                    continue
                for record in records:
                    more_result_dict = {
                        CONF_DOMAIN: subdomain if not record["praefix"] else f'{record["praefix"]}.{subdomain}',
                        CONF_IP_ADDRESS: record["content"],
                        CONF_TYPE: record[CONF_TYPE],
                        CONF_TTL: record[CONF_TTL],
                        "failover_policy": record["failover_policy"],
                        "deactivated": record["deactivated"],
                        "last_update": record["last_update"],
                    }
                    sub_domains_list.append(more_result_dict)
            data["subdomains"] = sub_domains_list
        except aiohttp.ClientResponseError as error:
            errors = {
                "Account Update Token": "incorrect",
                CONF_IP_ADDRESS: data[CONF_IP_ADDRESS] if data and CONF_IP_ADDRESS in data else "unlivable",
                "last_update": data["last_update"] if data and "last_update" in data else "unlivable",
            }
            data.update(errors)
            _LOGGER.error(
                "Your 'Update Token' is incorrect. Error: %s | Status: %i",
                error.message,
                error.status,
            )


class IPv64DataUpdateCoordinator(DataUpdateCoordinator):
    """DataUpdateCoordinator for IPv64."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize IPv64 data updater."""
        _LOGGER.debug("Initialize IPv64 data updater")
        if (intervale := entry.options.get(CONF_SCAN_INTERVAL, 23)) == 0:
            _LOGGER.info("IPv64 data updater disabled")

        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN}-{entry.entry_id}",
            update_interval=timedelta(minutes=intervale) if intervale > 0 else None,
        )

    async def async_update(self, call: ServiceCall):
        """Update IPv64 data from IPv64.net API."""
        _LOGGER.debug("update IP Address from Service")
        economy = call.data.get("economy", False)
        await self._async_update_data(is_economy=economy)

    async def _async_update_data(self, is_economy=False):
        """Update the data from IPv64.net. This method is a coroutine. It will update the data from IPv64."""
        _LOGGER.debug("Update the data from IPv64.net")

        result_account_info = {}

        if isinstance(self.data, dict):
            self.data.update({CONF_DOMAIN: self.config_entry.data[CONF_DOMAIN]})
        else:
            self.data = {CONF_DOMAIN: self.config_entry.data[CONF_DOMAIN]}

        session: aiohttp.ClientSession = async_get_clientsession(self.hass)
        headers_api = {"Authorization": f"Bearer {self.config_entry.data[CONF_API_KEY]}"}

        try:
            result_account_info = await get_account_info(session, headers_api, self.config_entry.data)
            self.data.update(result_account_info)
        except APIKeyError:
            result_account_info[CONF_DYNDNS_UPDATES] = "unlivable"
            result_account_info[CONF_DAILY_UPDATE_LIMIT] = "unlivable"

        await get_domain(session, headers_api, self.data)

        ip_is_changed = False

        if (
            hasattr(self.config_entry, "options")
            and CONF_API_ECONOMY in self.config_entry.options
            and self.config_entry.options[CONF_API_ECONOMY]
        ) or is_economy:
            ip_is_changed = await self.check_ip_equal(session)
        else:
            ip_is_changed = True

        if ip_is_changed:
            headers_token = {"Authorization": f"Bearer {self.config_entry.data[CONF_TOKEN]}"}
            async with asyncio.timeout(TIMEOUT):
                try:
                    resp = await session.get(
                        f"{UPDATE_URL}?domain={self.config_entry.data[CONF_DOMAIN]}",
                        headers=headers_token,
                        raise_for_status=True,
                    )
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
                    elif error.status == 401:
                        _LOGGER.error("Error: %s | Status: %i", error.message, error.status)
                    else:
                        _LOGGER.error(
                            "Your 'Update Token' is incorrect. Error: %s | Status: %i",
                            error.message,
                            error.status,
                        )
                    self.data.update({"update_result": "fail"})
        return self.data

    async def check_ip_equal(self, session) -> bool:
        """Check if the ip is equal to the current ip."""
        _LOGGER.debug("Economy-Modus")
        ip_changed = True
        async with asyncio.timeout(TIMEOUT):
            try:
                request = await session.get(CHECKIP_URL, raise_for_status=True)
                ip1_obj = ipaddress.ip_address(self.data[CONF_IP_ADDRESS])
                ip2_obj = ipaddress.ip_address((await request.text()).strip())
                ip_changed = ip1_obj != ip2_obj
            except (
                ValueError,
                KeyError,
                aiohttp.ClientResponseError,
                aiohttp.ClientConnectorError,
            ):
                pass
        return ip_changed
