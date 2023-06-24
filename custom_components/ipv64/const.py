"""Const for IPv64"""
from __future__ import annotations
from typing import Final

import voluptuous as vol

from homeassistant.const import CONF_DOMAIN, CONF_SCAN_INTERVAL, CONF_TOKEN
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

CONF_API_KEY = "apikey"

DOMAIN = "ipv64"

DEFAULT_INTERVAL = 23

DATA_SCHEMA = {
    vol.Required(CONF_DOMAIN): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT, multiline=False)),
    vol.Required(CONF_TOKEN): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT, multiline=False)),
    vol.Required(CONF_API_KEY): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT, multiline=False)),
    vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_INTERVAL): NumberSelector(
        NumberSelectorConfig(mode=NumberSelectorMode.SLIDER, min=1, max=120, unit_of_measurement="minutes")
    ),
}

DATA_HASS_CONFIG = "hass_config"
TRACKER_UPDATE_STR: Final = f"{DOMAIN}_tracker_update"

TIMEOUT = 10
UPDATE_URL = "https://ipv64.net/nic/update"
