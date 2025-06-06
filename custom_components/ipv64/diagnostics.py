"""Diagnostics support for IPv64."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, CONF_TOKEN, DOMAIN

TO_REDACT = {
    CONF_API_KEY,
    CONF_TOKEN,
    "record_key",
    "record_id",
    "domain_update_hash",
    "domain",
    "title",
    "ip_address",
    "unique_id",
}
_LOGGER = logging.getLogger(__name__)


def _redact_metadata(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact metadata sections."""
    result: dict[str, Any] = {}
    for key, value in data.items():
        new_key = "**REDACTED**_metadata" if key.endswith("_metadata") and key != f'{data.get("domain")}_metadata' else key
        new_key = "**REDACTED_REG_DOMAIN**_metadata" if key == f'{data.get("domain")}_metadata' else new_key
        if isinstance(value, dict):
            result[new_key] = _redact_metadata(value)
        elif isinstance(value, list):
            result[new_key] = [_redact_metadata(item) if isinstance(item, dict) else item for item in value]
        else:
            result[new_key] = value
    return result


async def async_get_config_entry_diagnostics(hass: HomeAssistant, config_entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.debug(coordinator.data["domain"])
    data = _redact_metadata(coordinator.data)

    return {
        "entry": async_redact_data(config_entry.as_dict(), TO_REDACT),
        "data": async_redact_data(data, TO_REDACT),
    }


# """Diagnostics platform for IPv64."""

# from __future__ import annotations

# from homeassistant.components.diagnostics import async_redact_data
# from homeassistant.core import HomeAssistant

# from .coordinator import IPv64DataUpdateCoordinator

# TO_REDACT = {"token", "apikey", "domain", "update_hash", "unique_id", "title", "ip_address"}


# async def async_get_config_entry_diagnostics(
#     hass: HomeAssistant,
#     config_entry: IPv64DataUpdateCoordinator,
# ) -> dict[str, any]:
#     """Return diagnostics for a config entry."""
#     return {
#         "data": async_redact_data(config_entry.runtime_data.data, TO_REDACT),
#     }
