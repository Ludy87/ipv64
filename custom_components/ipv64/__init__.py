"""Integrate IPv64 at https://ipv64.net/."""

from __future__ import annotations

import logging

from homeassistant import config_entries
from homeassistant.components.persistent_notification import async_create
from homeassistant.const import CONF_DOMAIN, Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    CONF_API_ECONOMY,
    CONF_API_KEY,
    DOMAIN,
    SERVICE_ADD_DOMAIN,
    SERVICE_DELETE_DOMAIN,
    SERVICE_REFRESH,
)
from .coordinator import IPv64DataUpdateCoordinator, add_domain, delete_domain

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the IPv64.net component."""
    _LOGGER.debug("Initializing IPv64.net component")
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: config_entries.ConfigEntry) -> bool:
    """Migrate old config entries to new format."""
    _LOGGER.debug("Migrating config entry %s", config_entry.entry_id)
    if config_entry.version == 1:
        new_options = {**config_entry.options}
        if CONF_API_ECONOMY not in new_options:
            new_options[CONF_API_ECONOMY] = True
            hass.config_entries.async_update_entry(config_entry, options=new_options)
            _LOGGER.info("Migrated config entry %s to set CONF_API_ECONOMY=True", config_entry.entry_id)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Configure based on config entry."""
    _LOGGER.debug("Configuring IPv64.net for entry %s with domain %s", entry.entry_id, entry.data.get("domain"))
    if not entry.data.get("domain"):
        _LOGGER.error("Invalid config entry: missing domain for entry %s", entry.entry_id)
        async_create(
            hass,
            f"IPv64.net: Invalid config entry for ID {entry.entry_id}. Domain is missing.",
            title="IPv64.net Configuration Error",
            notification_id=f"{DOMAIN}_{entry.entry_id}_config_error",
        )
        return False

    if not await async_migrate_entry(hass, entry):
        return False

    coordinator = IPv64DataUpdateCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Failed to refresh config entry %s: %s", entry.entry_id, err)
        async_create(
            hass,
            f"IPv64.net: Error while loading configuration for {entry.data.get('domain')}: {err}",
            title="IPv64.net Initialization Error",
            notification_id=f"{DOMAIN}_{entry.entry_id}_init_error",
        )
        return False

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    async def refresh(call: ServiceCall) -> None:
        """Handle service call to update IP address."""
        if len(hass.data[DOMAIN]) != 1:
            _LOGGER.error("Expected exactly one config entry, found %d", len(hass.data[DOMAIN]))
            async_create(
                hass,
                f"IPv64.net: Invalid number of config entries: {len(hass.data[DOMAIN])}. Only one instance is allowed.",
                title="IPv64.net Service Error",
                notification_id=f"{DOMAIN}_service_error",
            )
            return
        entry_id = next(iter(hass.data[DOMAIN]))
        _LOGGER.debug("Service call to refresh IP address for entry %s", entry_id)
        coordinator: IPv64DataUpdateCoordinator = hass.data[DOMAIN][entry_id]
        await coordinator.async_update(call)

    async def handle_add_domain(call: ServiceCall) -> None:
        """Handle service call to add a domain."""
        if len(hass.data[DOMAIN]) != 1:
            _LOGGER.error("Expected exactly one config entry, found %d", len(hass.data[DOMAIN]))
            async_create(
                hass,
                f"IPv64.net: Invalid number of config entries: {len(hass.data[DOMAIN])}. Only one instance is allowed.",
                title="IPv64.net Service Error",
                notification_id=f"{DOMAIN}_service_error",
            )
            return
        entry_id = next(iter(hass.data[DOMAIN]))
        domain = call.data.get(CONF_DOMAIN)
        if not domain:
            _LOGGER.error("No domain provided for add_domain service")
            async_create(
                hass,
                "IPv64.net: No domain specified for add_domain service.",
                title="IPv64.net Service Error",
                notification_id=f"{DOMAIN}_{entry_id}_add_domain_error",
            )
            return
        _LOGGER.debug("Service call to add domain %s for entry %s", domain, entry_id)
        coordinator: IPv64DataUpdateCoordinator = hass.data[DOMAIN][entry_id]
        try:
            await add_domain(hass, coordinator, domain, coordinator.config_entry.data.get(CONF_API_KEY))
            async_create(
                hass,
                f"IPv64.net: Domain {domain} successfully created.",
                title="IPv64.net Domain Created",
                notification_id=f"{DOMAIN}_{entry_id}_add_domain_success",
            )
            # Reload integration to recreate sensors with new subdomains
            await hass.config_entries.async_reload(entry_id)
        except Exception as err:
            _LOGGER.error("Failed to add domain %s: %s", domain, err)
            async_create(
                hass,
                f"IPv64.net: Error while creating domain {domain}: {err}",
                title="IPv64.net Domain Error",
                notification_id=f"{DOMAIN}_{entry_id}_add_domain_error",
            )

    async def handle_delete_domain(call: ServiceCall) -> None:
        """Handle service call to delete a domain."""
        if len(hass.data[DOMAIN]) != 1:
            _LOGGER.error("Expected exactly one config entry, found %d", len(hass.data[DOMAIN]))
            async_create(
                hass,
                f"IPv64.net: Invalid number of config entries: {len(hass.data[DOMAIN])}. Only one instance is allowed.",
                title="IPv64.net Service Error",
                notification_id=f"{DOMAIN}_service_error",
            )
            return
        entry_id = next(iter(hass.data[DOMAIN]))
        domain = call.data.get(CONF_DOMAIN)
        if not domain:
            _LOGGER.error("No domain provided for delete_domain service")
            async_create(
                hass,
                "IPv64.net: No domain specified for delete_domain service.",
                title="IPv64.net Service Error",
                notification_id=f"{DOMAIN}_{entry_id}_delete_domain_error",
            )
            return
        _LOGGER.debug("Service call to delete domain %s for entry %s", domain, entry_id)
        coordinator: IPv64DataUpdateCoordinator = hass.data[DOMAIN][entry_id]
        try:
            await delete_domain(hass, coordinator, domain, coordinator.config_entry.data.get(CONF_API_KEY))
            async_create(
                hass,
                f"IPv64.net: Domain {domain} successfully deleted.",
                title="IPv64.net Domain Deleted",
                notification_id=f"{DOMAIN}_{entry_id}_delete_domain_success",
            )
            # Reload integration to recreate sensors with updated subdomains
            await hass.config_entries.async_reload(entry_id)
        except Exception as err:
            _LOGGER.error("Failed to delete domain %s: %s", domain, err)
            async_create(
                hass,
                f"IPv64.net: Error while deleting domain {domain}: {err}",
                title="IPv64.net Domain Error",
                notification_id=f"{DOMAIN}_{entry_id}_delete_domain_error",
            )

    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH):
        hass.services.async_register(DOMAIN, SERVICE_REFRESH, refresh)
    else:
        _LOGGER.debug("Service %s already registered", SERVICE_REFRESH)

    if not hass.services.has_service(DOMAIN, SERVICE_ADD_DOMAIN):
        hass.services.async_register(DOMAIN, SERVICE_ADD_DOMAIN, handle_add_domain)
    else:
        _LOGGER.debug("Service %s already registered", SERVICE_ADD_DOMAIN)

    if not hass.services.has_service(DOMAIN, SERVICE_DELETE_DOMAIN):
        hass.services.async_register(DOMAIN, SERVICE_DELETE_DOMAIN, handle_delete_domain)
    else:
        _LOGGER.debug("Service %s already registered", SERVICE_DELETE_DOMAIN)

    return True


async def options_update_listener(hass: HomeAssistant, config_entry: config_entries.ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("Reloading IPv64.net integration for entry %s due to options update", config_entry.entry_id)
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading IPv64.net config entry %s", entry.entry_id)
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        hass.services.async_remove(DOMAIN, SERVICE_REFRESH)
        hass.services.async_remove(DOMAIN, SERVICE_ADD_DOMAIN)
        hass.services.async_remove(DOMAIN, SERVICE_DELETE_DOMAIN)
    return unload_ok
