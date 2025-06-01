"""Integrate IPv64 at https://ipv64.net/."""

from __future__ import annotations

import logging

from homeassistant import config_entries
from homeassistant.components.persistent_notification import async_create
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, SERVICE_REFRESH
from .coordinator import IPv64DataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the IPv64.net component."""
    _LOGGER.debug("Initializing IPv64.net component")
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Configure based on config entry."""
    _LOGGER.debug("Configuring IPv64.net for entry %s with domain %s", entry.entry_id, entry.data.get("domain"))
    if not entry.data.get("domain"):
        _LOGGER.error("Invalid config entry: missing domain for entry %s", entry.entry_id)
        async_create(
            hass,
            f"IPv64.net: Ungültiger Konfigurationseintrag für ID {entry.entry_id}. Domain fehlt.",
            title="IPv64.net Konfigurationsfehler",
            notification_id=f"{DOMAIN}_{entry.entry_id}_config_error",
        )
        return False

    coordinator = IPv64DataUpdateCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Failed to refresh config entry %s: %s", entry.entry_id, err)
        async_create(
            hass,
            f"IPv64.net: Fehler beim Laden der Konfiguration für {entry.data.get('domain')}: {err}",
            title="IPv64.net Initialisierungsfehler",
            notification_id=f"{DOMAIN}_{entry.entry_id}_init_error",
        )
        return False

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    async def update(call: ServiceCall) -> None:
        """Handle service call to update IP address."""
        _LOGGER.debug("Service call to update IP address for entry %s", entry.entry_id)
        await coordinator.async_update(call)

    # Register service with unique name to avoid conflicts
    service_name = f"{SERVICE_REFRESH}_{entry.entry_id}"
    if not hass.services.has_service(DOMAIN, service_name):
        hass.services.async_register(DOMAIN, service_name, update)
    else:
        _LOGGER.warning("Service %s already registered for entry %s", service_name, entry.entry_id)

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
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, f"{SERVICE_REFRESH}_{entry.entry_id}")
    return unload_ok
