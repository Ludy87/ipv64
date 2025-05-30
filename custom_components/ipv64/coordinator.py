"""Coordinator for IPv64."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

import aiohttp

from homeassistant.components.persistent_notification import async_create
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DOMAIN, CONF_IP_ADDRESS, CONF_SCAN_INTERVAL, CONF_TOKEN, CONF_TTL, CONF_TYPE
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .config_flow import APIKeyError, get_account_info
from .const import (
    CHECKIP_URL,
    CONF_API_ECONOMY,
    CONF_API_KEY,
    CONF_DAILY_UPDATE_LIMIT,
    CONF_DYNDNS_UPDATES,
    CONF_REMAINING_UPDATES,
    DOMAIN,
    GET_DOMAIN_URL,
    RETRY_ATTEMPTS,
    RETRY_DELAY,
    TIMEOUT,
    UPDATE_URL,
)

_LOGGER = logging.getLogger(__name__)


async def get_domain(session: aiohttp.ClientSession, headers: dict[str, str], data: dict[str, Any]) -> None:
    """Fetch domain information from the IPv64.net API."""
    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with session.get(GET_DOMAIN_URL, headers=headers, timeout=TIMEOUT) as resp:
                resp.raise_for_status()
                result = await resp.json()
                subdomains = result.get("subdomains", {})
                if not subdomains:
                    _LOGGER.warning("No subdomains found for account")
                    data["subdomains"] = []
                    return

                sub_domains_list = []
                for subdomain, values in subdomains.items():
                    if subdomain != data.get(CONF_DOMAIN):
                        continue
                    records = values.get("records", [])
                    for record in records:
                        sub_domains_list.append(
                            {
                                CONF_DOMAIN: subdomain if not record.get("prefix", "") else f'{record["prefix"]}.{subdomain}',
                                CONF_IP_ADDRESS: record["content"],
                                CONF_TYPE: record["type"],
                                CONF_TTL: str(record["ttl"]),
                                "failover_policy": str(record["failover_policy"]),
                                "deactivated": bool(record["deactivated"]),
                                "last_update": record["last_update"],
                            }
                        )
                data["subdomains"] = sub_domains_list
                return
        except aiohttp.ClientResponseError as error:
            if attempt == RETRY_ATTEMPTS - 1:
                _LOGGER.error(
                    "Failed to fetch domains after %d attempts: %s | Status: %d",
                    RETRY_ATTEMPTS,
                    error.message,
                    error.status,
                )
                data["subdomains"] = []
                data["error"] = "Failed to fetch domains"
                return
            _LOGGER.warning(
                "Failed to fetch domains, retrying (%d/%d): %s",
                attempt + 1,
                RETRY_ATTEMPTS,
                error.message,
            )
            await asyncio.sleep(RETRY_DELAY)
        except (TimeoutError, aiohttp.ClientError) as err:
            if attempt == RETRY_ATTEMPTS - 1:
                _LOGGER.error("Failed to fetch domains after %d attempts: %s", RETRY_ATTEMPTS, err)
                data["subdomains"] = []
                data["error"] = str(err)
                return
            _LOGGER.warning(
                "Failed to fetch domains, retrying (%d/%d): %s",
                attempt + 1,
                RETRY_ATTEMPTS,
                err,
            )
            await asyncio.sleep(RETRY_DELAY)


class IPv64DataUpdateCoordinator(DataUpdateCoordinator):
    """DataUpdateCoordinator to handle IPv64 data updates with caching."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the IPv64 data coordinator."""
        _LOGGER.debug("Initializing IPv64 data updater for entry: %s", entry.entry_id)
        self.config_entry = entry
        self.data = {CONF_DOMAIN: entry.data.get(CONF_DOMAIN, "")}
        self._cache = Store(hass, version=1, key=f"{DOMAIN}_{entry.entry_id}_data")
        interval = entry.options.get(CONF_SCAN_INTERVAL, 23)
        if interval == 0:
            _LOGGER.info("IPv64 data updater disabled (interval=0)")
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(minutes=interval) if interval > 0 else None,
        )

    async def async_update(self, call: ServiceCall) -> None:
        """Update IPv64 data from a service call."""
        _LOGGER.debug("Manual IP address update triggered via service call for entry: %s", self.config_entry.entry_id)
        economy = call.data.get(CONF_API_ECONOMY, False)
        await self._async_update_data(is_economy=economy, force_refresh=True)

    async def _async_update_data(self, is_economy: bool = False, force_refresh: bool = False) -> dict[str, Any]:
        """Update data from IPv64.net, utilizing cache if available."""
        _LOGGER.debug("Updating data from IPv64.net (economy=%s, force_refresh=%s)", is_economy, force_refresh)

        # Ensure self.data is a dictionary
        if not isinstance(self.data, dict):
            _LOGGER.warning("self.data was invalid, reinitializing")
            self.data = {CONF_DOMAIN: self.config_entry.data.get(CONF_DOMAIN, "")}

        # Load cached data if not forced to refresh
        cached_data = await self._cache.async_load() if not force_refresh else None
        if cached_data and not is_economy and not force_refresh:
            cache_time = cached_data.get("cache_time")
            if cache_time and datetime.fromisoformat(cache_time) > datetime.now() - timedelta(hours=1):
                _LOGGER.debug("Utilizing cached data")
                self.data = cached_data
                return self.data

        session = async_get_clientsession(self.hass)
        headers_api = {"Authorization": f"Bearer {self.config_entry.data.get(CONF_API_KEY, '')}"}

        try:
            for attempt in range(RETRY_ATTEMPTS):
                try:
                    account_info = await get_account_info(session, headers_api, self.config_entry.data)
                    if not isinstance(account_info, dict):
                        _LOGGER.error("Received invalid account_info: %s", account_info)
                        raise UpdateFailed("Received invalid account info")
                    self.data.update(account_info)
                    break
                except APIKeyError as err:
                    if attempt == RETRY_ATTEMPTS - 1:
                        _LOGGER.error("Invalid API key after %d attempts: %s", RETRY_ATTEMPTS, err)
                        self.data.update({CONF_DYNDNS_UPDATES: "unavailable", CONF_DAILY_UPDATE_LIMIT: "unavailable"})
                        raise UpdateFailed(f"Invalid API key: {err}") from err
                    _LOGGER.warning("Invalid API key, retrying (%d/%d)", attempt + 1, RETRY_ATTEMPTS)
                    await asyncio.sleep(RETRY_DELAY)
                except (TimeoutError, aiohttp.ClientError) as err:
                    if attempt == RETRY_ATTEMPTS - 1:
                        _LOGGER.error("Failed to fetch account info after %d attempts: %s", RETRY_ATTEMPTS, err)
                        raise UpdateFailed(f"Failed to fetch account info: {err}") from err
                    _LOGGER.warning("Failed to fetch account info, retrying (%d/%d): %s", attempt + 1, RETRY_ATTEMPTS, err)
                    await asyncio.sleep(RETRY_DELAY)

        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error fetching account info: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err

        await get_domain(session, headers_api, self.data)

        ip_is_changed = False
        if self.config_entry.options.get(CONF_API_ECONOMY, False) or is_economy:
            ip_is_changed = await self.check_ip_equal(session)
        else:
            ip_is_changed = True

        if ip_is_changed:
            headers_token = {"Authorization": f"Bearer {self.config_entry.data.get(CONF_TOKEN, '')}"}
            for attempt in range(RETRY_ATTEMPTS):
                try:
                    async with session.get(
                        f"{UPDATE_URL}?domain={self.config_entry.data.get(CONF_DOMAIN, '')}",
                        headers=headers_token,
                        timeout=TIMEOUT,
                    ) as resp:
                        resp.raise_for_status()
                        update_result = await resp.text()
                        self.data.update({"update_result": update_result})
                        _LOGGER.info("IP update successful: %s", update_result)
                        break
                except aiohttp.ClientResponseError as error:
                    self.data.update({"update_result": "fail"})
                    if attempt == RETRY_ATTEMPTS - 1:
                        if error.status == 429:
                            _LOGGER.error(
                                "Update limit reached: %s of %s used",
                                self.data.get(CONF_DYNDNS_UPDATES, "unknown"),
                                self.data.get(CONF_DAILY_UPDATE_LIMIT, "unknown"),
                            )
                        elif error.status == 401:
                            _LOGGER.error("Invalid update token")
                        else:
                            _LOGGER.error(
                                "Update failed after %d attempts: %s | Status: %d",
                                RETRY_ATTEMPTS,
                                error.message,
                                error.status,
                            )
                        raise UpdateFailed(f"Update failed after retries: {error}") from error
                    _LOGGER.warning("Update failed, retrying (%d/%d): %s", attempt + 1, RETRY_ATTEMPTS, error.message)
                    await asyncio.sleep(RETRY_DELAY)
                except (TimeoutError, aiohttp.ClientError) as error:
                    self.data.update({"update_result": "fail"})
                    if attempt == RETRY_ATTEMPTS - 1:
                        _LOGGER.error("Failed to update IP after %d attempts: %s", RETRY_ATTEMPTS, error)
                        raise UpdateFailed(f"Update failed: {error}") from error
                    _LOGGER.warning("Update failed, retrying (%d/%d): %s", attempt + 1, RETRY_ATTEMPTS, error)
                    await asyncio.sleep(RETRY_DELAY)
        else:
            _LOGGER.debug("IP unchanged, no update needed")

        # Calculate remaining updates and send notification if near limit
        updates_used = self.data.get(CONF_DYNDNS_UPDATES, 0)
        updates_limit = self.data.get(CONF_DAILY_UPDATE_LIMIT, 64)
        if updates_used > 0 and updates_limit > 0:
            remaining_updates = updates_limit - int(updates_used)
            self.data.update({CONF_REMAINING_UPDATES: remaining_updates})
            if updates_used >= updates_limit * 0.9:
                async_create(
                    self.hass,
                    f"IPv64: {updates_used} of {updates_limit} daily updates used. Consider enabling economy mode.",
                    title="IPv64 Update Limit Warning",
                    notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_update_limit",
                )

        # Cache data with timestamp
        self.data["cache_time"] = datetime.now().isoformat()
        await self._cache.async_save(self.data)

        return self.data

    async def check_ip_equal(self, session: aiohttp.ClientSession) -> bool:
        """Check if the IP has changed."""
        _LOGGER.debug("Checking IP in economy mode")
        for attempt in range(RETRY_ATTEMPTS):
            try:
                async with session.get(CHECKIP_URL, timeout=TIMEOUT) as request:
                    request.raise_for_status()
                    current_ip = (await request.text()).strip()
                    stored_ip = self.data.get(CONF_IP_ADDRESS, "unknown")
                    ip_changed = current_ip != stored_ip
                    _LOGGER.debug(
                        "IP comparison: stored=%s, current=%s, changed=%s",
                        stored_ip,
                        current_ip,
                        ip_changed,
                    )
                    return ip_changed
            except (aiohttp.ClientResponseError, aiohttp.ClientConnectionError) as error:
                if attempt == RETRY_ATTEMPTS - 1:
                    _LOGGER.error("Failed to check IP after %d attempts: %s", RETRY_ATTEMPTS, error)
                    return True
                _LOGGER.warning("IP check failed, retrying (%d/%d): %s", attempt + 1, RETRY_ATTEMPTS, error)
                await asyncio.sleep(RETRY_DELAY)
            except (TimeoutError, aiohttp.ClientError) as error:
                if attempt == RETRY_ATTEMPTS - 1:
                    _LOGGER.error("Failed to check IP after %d attempts: %s", RETRY_ATTEMPTS, error)
                    return True
                _LOGGER.warning("IP check failed, retrying (%d/%d): %s", attempt + 1, RETRY_ATTEMPTS, error)
                await asyncio.sleep(RETRY_DELAY)
        return True
