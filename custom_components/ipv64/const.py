"""Const for IPv64."""

from __future__ import annotations

from typing import Final

import voluptuous as vol

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

CONF_API_KEY: Final = "apikey"
CONF_API_ECONOMY: Final = "api_key_economy"
CONF_DAILY_UPDATE_LIMIT: Final = "daily_update_limit"
CONF_DYNDNS_UPDATE_TODAY: Final = "dyndns_updates_today"
CONF_DYNDNS_UPDATES: Final = "dyndns_updates"
CONF_WILDCARD: Final = "wildcard"

DOMAIN: Final = "ipv64"

SHORT_NAME: Final = "IPv64"

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
API_URL: Final = "https://ipv64.net/api.php"  # "http://192.168.0.220:1080/api.php"
CHECKIP_URL: Final = "https://checkip.amazonaws.com/"

GET_DOMAIN_URL: Final = f"{API_URL}?get_domains"
GET_ACCOUNT_INFO_URL: Final = f"{API_URL}?get_account_info"
GET_HEALTHCHECKS: Final = f"{API_URL}?get_healthchecks"
GET_HEALTHCHECK_STATISTICS: Final = f"{API_URL}?get_healthcheck_statistics"
GET_INTEGRATIONS: Final = f"{API_URL}?get_integrations"

SERVICE_REFRESH = "refresh"

EXCLUDED_KEYS: Final = [
    "email",
    "account_class",
    "get_account_info",
    "dyndns_updates",
    "update_hash",
    "api_key",
    "sms_count",
    "api_updates",
]
