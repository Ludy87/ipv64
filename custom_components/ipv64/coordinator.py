"""Coordinator for IPv64."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

import aiohttp

from homeassistant.components.persistent_notification import async_create, async_dismiss
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DOMAIN, CONF_IP_ADDRESS, CONF_SCAN_INTERVAL, CONF_TOKEN, CONF_TTL, CONF_TYPE
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .config_flow import APIKeyError, get_account_info
from .const import (
    ALLOWED_DOMAINS,
    API_URL,
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
    config_domain = data.get(CONF_DOMAIN, "")
    # Validate domain against allowed domains
    if not any(config_domain.endswith(allowed_domain) for allowed_domain in ALLOWED_DOMAINS):
        _LOGGER.error("Domain %s is not one of the allowed domains: %s", config_domain, ALLOWED_DOMAINS)
        data["subdomains"] = []
        data["error"] = f"Domain {config_domain} not allowed"
        return

    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with session.get(GET_DOMAIN_URL, headers=headers, timeout=TIMEOUT) as resp:
                resp.raise_for_status()
                result = await resp.json()
                subdomains = result.get("subdomains", {})
                if not subdomains:
                    _LOGGER.warning("No subdomains found for account")
                    data["subdomains"] = []
                    data["error"] = "No subdomains available"
                    return

                sub_domains_list = []
                domain_found = False
                for subdomain, values in subdomains.items():
                    _LOGGER.debug("Checking subdomain %s against config domain %s", subdomain, config_domain)
                    records = values.get("records", [])
                    for record in records:
                        domain_name = subdomain if not record.get("praefix", "") else f"{record['praefix']}.{subdomain}"
                        if domain_name == config_domain:
                            domain_found = True
                            data[CONF_IP_ADDRESS] = record["content"]  # Set IP address for config domain
                        sub_domains_list.append(
                            {
                                CONF_DOMAIN: domain_name,
                                CONF_IP_ADDRESS: record["content"],
                                CONF_TYPE: record["type"],
                                CONF_TTL: str(record["ttl"]),
                                "failover_policy": str(record["failover_policy"]),
                                "deactivated": bool(record["deactivated"]),
                                "last_update": record["last_update"],
                            }
                        )
                    data.update(
                        {
                            f"{subdomain}_metadata": {
                                "updates": values.get("updates"),
                                "wildcard": values.get("wildcard"),
                                "domain_update_hash": values.get("domain_update_hash"),
                                "ipv6prefix": values.get("ipv6prefix"),
                                "dualstack": values.get("dualstack"),
                                "deactivated": values.get("deactivated"),
                            }
                        }
                    )
                if not domain_found:
                    _LOGGER.error("Configured domain %s not found in subdomains", config_domain)
                    data["subdomains"] = []
                    data["error"] = f"Domain {config_domain} not found"
                    return
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


async def add_domain(hass: HomeAssistant, coordinator: DataUpdateCoordinator, domain: str, api_key: str) -> None:
    """Add a new domain via the IPv64.net API."""
    if not any(domain.endswith(allowed_domain) for allowed_domain in ALLOWED_DOMAINS):
        _LOGGER.error("Domain %s is not one of the allowed domains: %s", domain, ALLOWED_DOMAINS)
        raise ValueError(f"Domain {domain} not allowed")

    session = async_get_clientsession(hass)
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {"add_domain": domain}

    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with session.post(API_URL, headers=headers, data=data, timeout=TIMEOUT) as resp:
                resp.raise_for_status()
                result = await resp.json()
                _LOGGER.debug("Received result: %s", result)  # log API response
                if result.get("info") != "success":
                    _LOGGER.error("Failed to add domain %s: %s", domain, result.get("add_domain"))
                    raise UpdateFailed(f"Failed to add domain: {result.get('add_domain')}")
                _LOGGER.info("Successfully added domain %s", domain)
                await coordinator.async_request_refresh()
                return
        except aiohttp.ClientResponseError as error:
            if attempt == RETRY_ATTEMPTS - 1:
                _LOGGER.error(
                    "Failed to add domain %s after %d attempts: %s | Status: %d",
                    domain,
                    RETRY_ATTEMPTS,
                    error.message,
                    error.status,
                )
                if error.status == 401:
                    raise APIKeyError("Invalid API key") from error
                if error.status == 429:
                    raise UpdateFailed("Rate limit exceeded: Maximum 3 requests per 10 seconds") from error
                raise UpdateFailed(f"Failed to add domain: {error.message}") from error
            _LOGGER.warning(
                "Failed to add domain, retrying (%d/%d): %s",
                attempt + 1,
                RETRY_ATTEMPTS,
                error.message,
            )
            await asyncio.sleep(RETRY_DELAY)
        except (TimeoutError, aiohttp.ClientError) as err:
            if attempt == RETRY_ATTEMPTS - 1:
                _LOGGER.error("Failed to add domain %s after %d attempts: %s", domain, RETRY_ATTEMPTS, err)
                raise UpdateFailed(f"Network error: {err}") from err
            _LOGGER.warning(
                "Failed to add domain, retrying (%d/%d): %s",
                attempt + 1,
                RETRY_ATTEMPTS,
                err,
            )
            await asyncio.sleep(RETRY_DELAY)


async def delete_domain(hass: HomeAssistant, coordinator: DataUpdateCoordinator, domain: str, api_key: str) -> None:
    """Delete a domain via the IPv64.net API."""
    if not any(domain.endswith(allowed_domain) for allowed_domain in ALLOWED_DOMAINS):
        _LOGGER.error("Domain %s is not one of the allowed domains: %s", domain, ALLOWED_DOMAINS)
        raise ValueError(f"Domain {domain} not allowed")

    session = async_get_clientsession(hass)
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {"del_domain": domain}

    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with session.delete(API_URL, headers=headers, data=data, timeout=TIMEOUT) as resp:
                resp.raise_for_status()
                result = await resp.json()
                _LOGGER.debug("Received result: %s", result)  # log API response
                if result.get("info") != "success":
                    _LOGGER.error("Failed to delete domain %s: %s", domain, result.get("info"))
                    raise UpdateFailed(f"Failed to delete domain: {result.get('info')}")
                _LOGGER.info("Successfully deleted domain %s", domain)
                await coordinator.async_request_refresh()
                return
        except aiohttp.ClientResponseError as error:
            if attempt == RETRY_ATTEMPTS - 1:
                _LOGGER.error(
                    "Failed to delete domain %s after %d attempts: %s | Status: %d",
                    domain,
                    RETRY_ATTEMPTS,
                    error.message,
                    error.status,
                )
                if error.status == 401:
                    raise APIKeyError("Invalid API key") from error
                if error.status == 429:
                    raise UpdateFailed("Rate limit exceeded: Maximum 3 requests per 10 seconds") from error
                raise UpdateFailed(f"Failed to delete domain: {error.message}") from error
            _LOGGER.warning(
                "Failed to delete domain, retrying (%d/%d): %s",
                attempt + 1,
                RETRY_ATTEMPTS,
                error.message,
            )
            await asyncio.sleep(RETRY_DELAY)
        except (TimeoutError, aiohttp.ClientError) as err:
            if attempt == RETRY_ATTEMPTS - 1:
                _LOGGER.error("Failed to delete domain %s after %d attempts: %s", domain, RETRY_ATTEMPTS, err)
                raise UpdateFailed(f"Network error: {err}") from err
            _LOGGER.warning(
                "Failed to delete domain, retrying (%d/%d): %s",
                attempt + 1,
                RETRY_ATTEMPTS,
                err,
            )
            await asyncio.sleep(RETRY_DELAY)


type IPv64ConfigEntry = ConfigEntry[IPv64DataUpdateCoordinator]


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
        if not isinstance(economy, bool):
            _LOGGER.warning("Invalid economy parameter: %s, defaulting to False", economy)
            economy = False
        await self._async_update_data(is_economy=economy, force_refresh=True)

    async def _async_update_data(self, is_economy: bool = False, force_refresh: bool = False) -> dict[str, Any]:
        """Update data from IPv64.net, utilizing cache if available."""
        _LOGGER.debug("Updating data from IPv64.net (economy=%s, force_refresh=%s)", is_economy, force_refresh)

        if not isinstance(self.data, dict):
            _LOGGER.debug("self.data was invalid, reinitializing")
            self.data = {CONF_DOMAIN: self.config_entry.data.get(CONF_DOMAIN, "")}

        session = async_get_clientsession(self.hass)
        headers_api = {"Authorization": f"Bearer {self.config_entry.data.get(CONF_API_KEY, '')}"}

        try:
            for attempt in range(RETRY_ATTEMPTS):
                try:
                    account_info = await get_account_info(session, headers_api, self.config_entry.data)
                    if not isinstance(account_info, dict):
                        _LOGGER.error("Received invalid account_info: %s", account_info)
                        raise UpdateFailed("Received invalid account info")
                    _LOGGER.debug("Received account info: %s", account_info)
                    self.data.update(account_info)
                    async_dismiss(
                        self.hass,
                        notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_api_error",
                    )
                    async_dismiss(
                        self.hass,
                        notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_network_error",
                    )
                    break
                except APIKeyError as err:
                    if attempt == RETRY_ATTEMPTS - 1:
                        _LOGGER.error("Invalid API key after %d attempts: %s", RETRY_ATTEMPTS, err)
                        self.data.update({CONF_DYNDNS_UPDATES: "unavailable", CONF_DAILY_UPDATE_LIMIT: "unavailable"})
                        async_create(
                            self.hass,
                            f"IPv64.net: Invalid API key for {self.config_entry.data.get(CONF_DOMAIN)} after {RETRY_ATTEMPTS} attempts.",
                            title="IPv64.net API Error",
                            notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_api_error",
                        )
                        raise UpdateFailed(f"Invalid API key: {err}") from err
                    _LOGGER.warning("Invalid API key, retrying (%d/%d)", attempt + 1, RETRY_ATTEMPTS)
                    await asyncio.sleep(RETRY_DELAY)
                except (TimeoutError, aiohttp.ClientError) as err:
                    if attempt == RETRY_ATTEMPTS - 1:
                        _LOGGER.error("Failed to fetch account info after %d attempts: %s", RETRY_ATTEMPTS, err)
                        async_create(
                            self.hass,
                            f"IPv64.net: Network error while fetching account information for {self.config_entry.data.get(CONF_DOMAIN)}: {err}",
                            title="IPv64.net Network Error",
                            notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_network_error",
                        )
                        raise UpdateFailed(f"Failed to fetch account info: {err}") from err
                    _LOGGER.warning("Failed to fetch account info, retrying (%d/%d): %s", attempt + 1, RETRY_ATTEMPTS, err)
                    await asyncio.sleep(RETRY_DELAY)
            async_dismiss(
                self.hass,
                notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_unexpected_error",
            )

        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error fetching account info: %s", err)
            async_create(
                self.hass,
                f"IPv64.net: Unexpected error while fetching account information for {self.config_entry.data.get(CONF_DOMAIN)}: {err}",
                title="IPv64.net Error",
                notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_unexpected_error",
            )
            raise UpdateFailed(f"Unexpected error: {err}") from err

        await get_domain(session, headers_api, self.data)

        ip_is_changed = False
        if self.config_entry.options.get(CONF_API_ECONOMY, True) or is_economy:
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
                        update_result = await resp.json()
                        self.data.update({"update_result": update_result.get("status", "unknown")})
                        _LOGGER.info("IP update successful for %s: %s", self.config_entry.data.get(CONF_DOMAIN), update_result)
                        break
                    async_dismiss(
                        self.hass,
                        notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_limit_error",
                    )
                    async_dismiss(
                        self.hass,
                        notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_auth_error",
                    )
                    async_dismiss(
                        self.hass,
                        notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_network_update_error",
                    )
                except aiohttp.ClientResponseError as error:
                    self.data.update({"update_result": "fail"})
                    if attempt == RETRY_ATTEMPTS - 1:
                        if error.status == 429:
                            _LOGGER.error(
                                "Update limit reached for %s: %s of %s used",
                                self.config_entry.data.get(CONF_DOMAIN),
                                self.data.get(CONF_DYNDNS_UPDATES, "unknown"),
                                self.data.get(CONF_DAILY_UPDATE_LIMIT, "unknown"),
                            )
                            async_create(
                                self.hass,
                                f"IPv64.net: Update limit reached for {self.config_entry.data.get(CONF_DOMAIN)}. Remaining updates: {self.data.get(CONF_REMAINING_UPDATES, 'unknown')}.",
                                title="IPv64.net Update Limit",
                                notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_limit_error",
                            )
                        elif error.status == 401:
                            _LOGGER.error("Invalid update token for %s", self.config_entry.data.get(CONF_DOMAIN))
                            async_create(
                                self.hass,
                                f"IPv64.net: Invalid update token for {self.config_entry.data.get(CONF_DOMAIN)}.",
                                title="IPv64.net Authentication Error",
                                notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_auth_error",
                            )
                        else:
                            _LOGGER.error(
                                "Update failed for %s after %d attempts: %s | Status: %d",
                                self.config_entry.data.get(CONF_DOMAIN),
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
                        _LOGGER.error(
                            "Failed to update IP for %s after %d attempts: %s",
                            self.config_entry.data.get(CONF_DOMAIN),
                            RETRY_ATTEMPTS,
                            error,
                        )
                        async_create(
                            self.hass,
                            f"IPv64.net: Network error while updating IP for {self.config_entry.data.get(CONF_DOMAIN)}: {error}",
                            title="IPv64.net Network Error",
                            notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_network_update_error",
                        )
                        raise UpdateFailed(f"Update failed: {error}") from error
                    _LOGGER.warning("Update failed, retrying (%d/%d): %s", attempt + 1, RETRY_ATTEMPTS, error)
                    await asyncio.sleep(RETRY_DELAY)
        else:
            _LOGGER.debug("IP unchanged for %s, no update needed", self.config_entry.data.get(CONF_DOMAIN))

        updates_used = self.data.get(CONF_DYNDNS_UPDATES, 0)
        updates_limit = self.data.get(CONF_DAILY_UPDATE_LIMIT, 64)
        if updates_used > 0 and updates_limit > 0:
            remaining_updates = updates_limit - int(updates_used)
            self.data.update({CONF_REMAINING_UPDATES: remaining_updates})
            if updates_used >= updates_limit * 0.9:
                async_create(
                    self.hass,
                    f"IPv64.net: {updates_used} of {updates_limit} daily updates for {self.config_entry.data.get(CONF_DOMAIN)} consumed. Enable economy mode to save updates.",
                    title="IPv64.net Update Limit Warning",
                    notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_update_limit",
                )
            else:
                async_dismiss(
                    self.hass,
                    notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_update_limit",
                )

        self.data["cache_time"] = datetime.now().isoformat()
        await self._cache.async_save(self.data)

        return self.data

    async def check_ip_equal(self, session: aiohttp.ClientSession) -> bool:
        """Check if the IP has changed."""
        _LOGGER.debug("Checking IP in economy mode for %s", self.config_entry.data.get(CONF_DOMAIN))
        config_domain = self.config_entry.data.get(CONF_DOMAIN)
        stored_ip = self.data.get(CONF_IP_ADDRESS, "unknown")
        if stored_ip == "unknown":
            _LOGGER.warning("No stored IP found for domain %s, fetching from subdomains", config_domain)
            for subdomain in self.data.get("subdomains", []):
                if subdomain.get("domain") == config_domain:
                    stored_ip = subdomain.get("ip_address", "unknown")
                    self.data[CONF_IP_ADDRESS] = stored_ip  # Update self.data
                    break
            if stored_ip == "unknown":
                _LOGGER.error("No IP address found for domain %s in subdomains", config_domain)
                return True  # Trigger update if no stored IP

        for attempt in range(RETRY_ATTEMPTS):
            try:
                async with session.get(CHECKIP_URL, timeout=TIMEOUT) as request:
                    request.raise_for_status()
                    current_ip = (await request.text()).strip()
                    _LOGGER.debug("Current IP for %s: %s", config_domain, current_ip)
                    _LOGGER.debug("Stored IP for %s: %s", config_domain, stored_ip)
                    ip_changed = current_ip != stored_ip
                    _LOGGER.debug(
                        "IP comparison for %s: stored=%s, current=%s, changed=%s",
                        config_domain,
                        stored_ip,
                        current_ip,
                        ip_changed,
                    )
                    if ip_changed:
                        self.data[CONF_IP_ADDRESS] = current_ip  # Update stored IP
                    async_dismiss(
                        self.hass,
                        notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_ip_check_error",
                    )
                    async_dismiss(
                        self.hass,
                        notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_ip_check_network_error",
                    )
                    return ip_changed
            except (aiohttp.ClientResponseError, aiohttp.ClientConnectionError) as error:
                if attempt == RETRY_ATTEMPTS - 1:
                    _LOGGER.error(
                        "Failed to check IP for %s after %d attempts: %s",
                        config_domain,
                        RETRY_ATTEMPTS,
                        error,
                    )
                    async_create(
                        self.hass,
                        f"IPv64.net: Error while checking IP address for {config_domain}: {error}",
                        title="IPv64.net IP Check Error",
                        notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_ip_check_error",
                    )
                    return False
                _LOGGER.warning("IP check failed, retrying (%d/%d): %s", attempt + 1, RETRY_ATTEMPTS, error)
                await asyncio.sleep(RETRY_DELAY)
            except (TimeoutError, aiohttp.ClientError) as error:
                if attempt == RETRY_ATTEMPTS - 1:
                    _LOGGER.error(
                        "Failed to check IP for %s after %d attempts: %s",
                        config_domain,
                        RETRY_ATTEMPTS,
                        error,
                    )
                    async_create(
                        self.hass,
                        f"IPv64.net: Network error while checking IP address for {config_domain}: {error}",
                        title="IPv64.net IP Check Error",
                        notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_ip_check_network_error",
                    )
                    return False
                _LOGGER.warning("IP check failed, retrying (%d/%d): %s", attempt + 1, RETRY_ATTEMPTS, error)
                await asyncio.sleep(RETRY_DELAY)
        return False
