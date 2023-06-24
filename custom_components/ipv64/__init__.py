"""Integrate IPv64 at https://ipv64.net/"""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DATA_HASS_CONFIG, DATA_SCHEMA, DOMAIN
from .coordinator import IPv64DataUpdateCoordinator

PLATFORMS = [Platform.SENSOR]


_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(DATA_SCHEMA),
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, hass_config: ConfigType) -> bool:
    """Set up the IPv64.net component."""
    _LOGGER.debug("Set up the IPv64.net component")
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][DATA_HASS_CONFIG] = hass_config
    return True


async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Configure based on config entry."""
    _LOGGER.debug("Configure based on config entry %s", entry.entry_id)
    coordinator = IPv64DataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unload a config entry")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def options_update_listener(hass: HomeAssistant, config_entry: config_entries.ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("Configuration options updated, reloading IPv64.net integration")
    await hass.config_entries.async_reload(config_entry.entry_id)
