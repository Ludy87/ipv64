"""Constants for IPv64."""

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
CONF_DYNDNS_UPDATES: Final = "dyndns_updates"
CONF_REMAINING_UPDATES: Final = "remaining_updates"
CONF_WILDCARD: Final = "wildcard"  # Reserved for future wildcard domain support

DOMAIN: Final = "ipv64"
SHORT_NAME: Final = "IPv64"
DEFAULT_INTERVAL: Final = 23

DATA_SCHEMA: Final = {
    vol.Required(CONF_DOMAIN): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT, multiline=False)),
    vol.Required(CONF_TOKEN): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT, multiline=False)),
    vol.Required(CONF_API_KEY): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT, multiline=False)),
    vol.Required(CONF_API_ECONOMY, default=True): BooleanSelector(BooleanSelectorConfig()),
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
RETRY_ATTEMPTS: Final = 3
RETRY_DELAY: Final = 2
UPDATE_URL: Final = "https://ipv64.net/nic/update"
# UPDATE_URL: Final = "http://192.168.0.220:1080/update.php"  # Local test
# API_URL: Final = "http://192.168.0.220:1080/api.php"  # Local test
API_URL: Final = "https://ipv64.net/api.php"  # Production

CHECKIP_URL: Final = "https://checkip.amazonaws.com/"

GET_DOMAIN_URL: Final = f"{API_URL}?get_domains"
GET_ACCOUNT_INFO_URL: Final = f"{API_URL}?get_account_info"
GET_HEALTHCHECKS: Final = f"{API_URL}?get_healthchecks"
GET_HEALTHCHECK_STATISTICS: Final = f"{API_URL}?get_healthcheck_statistics"
GET_INTEGRATIONS: Final = f"{API_URL}?get_integrations"

SERVICE_REFRESH: Final = "refresh"
SERVICE_ADD_DOMAIN: Final = "add_domain"
SERVICE_DELETE_DOMAIN: Final = "delete_domain"

EXCLUDED_KEYS: Final[list[str]] = [
    "email",
    "account_class",
    "get_account_info",
    "api_key",
]

ALLOWED_DOMAINS: Final[list[str]] = [
    "ipv64.net",
    "ipv64.de",
    "any64.de",
    "eth64.de",
    "home64.de",
    "iot64.de",
    "lan64.de",
    "nas64.de",
    "srv64.de",
    "tcp64.de",
    "udp64.de",
    "vpn64.de",
    "wan64.de",
    "api64.de",
    "dyndns64.de",
    "dynipv6.de",
    "dns64.de",
    "root64.de",
    "route64.de",
]
