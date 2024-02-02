"""Const for IPv64."""

from __future__ import annotations

from typing import Final

from homeassistant.const import CONF_DOMAIN, CONF_SCAN_INTERVAL, CONF_TOKEN
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

CONF_API_KEY: Final = "apikey"
CONF_API_ECONOMY: Final = "api_key_economy"
CONF_DAILY_UPDATE_LIMIT: Final = "daily_update_limit"
CONF_DYNDNS_UPDATE_TODAY: Final = "dyndns_updates_today"
CONF_DYNDNS_UPDATES: Final = "dyndns_updates"
CONF_WILDCARD: Final = "wildcard"

DOMAIN: Final = "ipv64"

DEFAULT_INTERVAL: Final = 23

DATA_SCHEMA = {
    vol.Required(CONF_DOMAIN): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT, multiline=False)),
    vol.Required(CONF_TOKEN): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT, multiline=False)),
    vol.Required(CONF_API_KEY): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT, multiline=False)),
    vol.Required(CONF_API_ECONOMY): BooleanSelector(BooleanSelectorConfig()),
    vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_INTERVAL): NumberSelector(
        NumberSelectorConfig(
            mode=NumberSelectorMode.SLIDER,
            min=0,
            max=120,
            unit_of_measurement="minutes",
        )
    ),
}

DATA_HASS_CONFIG: Final = "hass_config"
TRACKER_UPDATE_STR: Final = f"{DOMAIN}_tracker_update"

TIMEOUT: Final = 10
UPDATE_URL: Final = "https://ipv64.net/nic/update"
GET_DOMAIN_URL: Final = "https://ipv64.net/api.php?get_domains"
GET_ACCOUNT_INFO_URL: Final = "https://ipv64.net/api.php?get_account_info"
CHECKIP_URL: Final = "https://checkip.amazonaws.com/"

SERVICE_REFRESH = "refresh"
