"""Integrate IPv64 at https://ipv64.net/."""

from __future__ import annotations

import logging

from homeassistant import config_entries
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, SERVICE_REFRESH
from .coordinator import IPv64DataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the IPv64.net component."""
    _LOGGER.debug("Setting up IPv64.net component")
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Configure based on config entry."""
    _LOGGER.debug("Configuring IPv64.net for entry %s", entry.entry_id)
    if not entry.data.get("domain"):
        _LOGGER.error("Invalid config entry: missing domain")
        return False

    coordinator = IPv64DataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    async def update(call: ServiceCall) -> None:
        _LOGGER.debug("Service call to update IP address for entry %s", entry.entry_id)
        await coordinator.async_update(call)

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, update)
    return True


async def options_update_listener(hass: HomeAssistant, config_entry: config_entries.ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("Reloading IPv64.net integration due to options update")
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading IPv64.net config entry %s", entry.entry_id)
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_REFRESH)
    return unload_ok
