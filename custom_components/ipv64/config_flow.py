"""Config flow for IPv64."""

from __future__ import annotations

import logging
import re
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries, core
from homeassistant.const import CONF_DOMAIN, CONF_SCAN_INTERVAL, CONF_TOKEN
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .api import request_json
from .const import (
    ALLOWED_DOMAINS,
    CONF_API_ECONOMY,
    CONF_API_KEY,
    CONF_DAILY_UPDATE_LIMIT,
    CONF_DYNDNS_UPDATES,
    DATA_SCHEMA,
    DOMAIN,
    EXCLUDED_KEYS,
    GET_ACCOUNT_INFO_URL,
    GET_DOMAIN_URL,
)

_LOGGER = logging.getLogger(__name__)

# Regex for valid domain names (e.g., subdomain.ipv64.net or prefix.subdomain.home64.de)
DOMAIN_REGEX = r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})+$"


class TokenError(Exception):
    """Exception for invalid token."""


class APIKeyError(Exception):
    """Exception for invalid API key."""


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class DomainNotFound(HomeAssistantError):
    """Error to indicate the domain was not found."""


class InvalidAPIKey(HomeAssistantError):
    """Error to indicate the API key is invalid."""


class InvalidDomain(HomeAssistantError):
    """Error to indicate the domain format is invalid."""


async def get_domains(session: aiohttp.ClientSession, headers_api: dict[str, str]) -> dict[str, Any]:
    """Fetches domain information from the IPv64.net API."""
    return await request_json(
        session,
        "GET",
        GET_DOMAIN_URL,
        headers=headers_api,
        log_context="get_domains",
    )


async def get_account_info(
    session: aiohttp.ClientSession,
    headers_api: dict[str, str],
    data: dict[str, Any],
    result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fetches account information from the IPv64.net API."""
    if result is None:
        result = {}
    account_result = await request_json(
        session,
        "GET",
        GET_ACCOUNT_INFO_URL,
        headers=headers_api,
        log_context="get_account_info",
    )
    result.update(
        {
            "account_status": account_result["account_status"],
            "reg_date": account_result["reg_date"],
            "dyndns_updates": account_result.get(CONF_DYNDNS_UPDATES, 0),
            "dyndns_subdomains": account_result.get("dyndns_subdomains", 0),
            "owndomains": account_result.get("owndomains", 0),
            "healthchecks": account_result.get("healthchecks", 0),
            "healthchecks_updates": account_result.get("healthchecks_updates", 0),
            "api_updates": account_result.get("api_updates", 0),
            "sms_count": account_result.get("sms_count", 0),
            "account": account_result["account_class"]["class_name"],
            "dyndns_domain_limit": account_result["account_class"].get("dyndns_domain_limit", 0),
            CONF_DAILY_UPDATE_LIMIT: account_result["account_class"].get("dyndns_update_limit", 0),
            "owndomain_limit": account_result["account_class"].get("owndomain_limit", 0),
            "healthcheck_limit": account_result["account_class"].get("healthcheck_limit", 0),
            "healthcheck_update_limit": account_result["account_class"].get("healthcheck_update_limit", 0),
            "dyndns_ttl": account_result["account_class"].get("dyndns_ttl", 0),
            "api_limit": account_result["account_class"].get("api_limit", 0),
            "sms_limit": account_result["account_class"].get("sms_limit", 0),
            "info": account_result.get("info", "unknown"),
            "status": account_result.get("status", "unknown"),
        }
    )
    for k, v in account_result.items():
        if k not in EXCLUDED_KEYS:
            result.setdefault(k, v)
    return result


async def check_domain_login(hass: core.HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Check the domain login information."""
    result = {}
    session: aiohttp.ClientSession = async_get_clientsession(hass)
    headers_api = {"Authorization": f"Bearer {data[CONF_API_KEY]}"}

    # Validate domain against allowed domains
    input_domain = data[CONF_DOMAIN]
    if not any(input_domain.endswith(allowed_domain) for allowed_domain in ALLOWED_DOMAINS):
        _LOGGER.error("Domain %s is not one of the allowed domains: %s", input_domain, ALLOWED_DOMAINS)
        raise InvalidDomain(f"Domain {input_domain} is not allowed. Allowed domains: {', '.join(ALLOWED_DOMAINS)}")

    try:
        result.update(await get_account_info(session, headers_api, data))
        domains = await get_domains(session, headers_api)
        subdomains = domains.get("subdomains", {})
        found = False
        for subdomain, subdomain_data in subdomains.items():
            _LOGGER.debug("Checking subdomain %s against input domain %s", subdomain, input_domain)
            # Check if input_domain is the main subdomain or a prefixed subdomain
            for record in subdomain_data.get("records", []):
                prefixed_domain = f"{record['praefix']}.{subdomain}" if record.get("praefix") else subdomain
                _LOGGER.debug("Comparing input domain %s with %s", input_domain, prefixed_domain)
                if input_domain == prefixed_domain:
                    found = True
                    break
            if found:
                break
        if not found:
            _LOGGER.error("Domain %s not found in account subdomains", input_domain)
            raise TokenError(f"Domain {input_domain} not found")
        result.update(domains)
    except aiohttp.ClientResponseError as error:
        _LOGGER.error("API request failed: %s | Status: %d", error.message, error.status)
        if error.status == 401:
            raise APIKeyError("Invalid API key") from error
        if error.status == 429:
            raise CannotConnect("Rate limit exceeded: Maximum 3 requests per 10 seconds") from error
        raise APIKeyError(f"API error: {error.message}") from error
    except (TimeoutError, aiohttp.ClientError) as error:
        _LOGGER.error("Network error during API request: %s", error)
        raise CannotConnect(f"Network error: {error}") from error
    return result


async def validate_input(hass: core.HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input for domain login."""
    # Validate domain format
    if not re.match(DOMAIN_REGEX, data[CONF_DOMAIN]):
        _LOGGER.error("Invalid domain format: %s", data[CONF_DOMAIN])
        raise InvalidDomain("Invalid domain format")
    result = await check_domain_login(hass, data)
    return {"title": f"{DOMAIN} {data[CONF_DOMAIN]}", "data": result}


class IPv64ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for IPv64."""

    VERSION = 1

    @staticmethod
    @core.callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return IPv64OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial user step."""
        # Only one configuration entry is allowed to prevent conflicting updates
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                _LOGGER.debug("Received user input: %s", user_input)
                info = await validate_input(self.hass, user_input)
                unique_id = f"{user_input[CONF_DOMAIN]}_{self.hass.data.get(DOMAIN, {}).get('entry_count', 0)}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info["title"],
                    data={
                        CONF_DOMAIN: user_input[CONF_DOMAIN],
                        CONF_API_KEY: user_input[CONF_API_KEY],
                        CONF_TOKEN: user_input[CONF_TOKEN],
                    },
                    options={
                        CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                        CONF_API_ECONOMY: user_input[CONF_API_ECONOMY],
                    },
                )
            except InvalidDomain:
                errors["base"] = "invalid_domain"
            except TokenError:
                errors["base"] = "domain_not_found"
            except APIKeyError:
                errors["base"] = "invalid_api_key"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during validation")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(DATA_SCHEMA),
            errors=errors,
            last_step=False,
            description_placeholders={
                "description": "Enter your IPv64.net credentials to manage your domains. API key and update token can be found in your IPv64.net account."
            },
        )


class IPv64OptionsFlowHandler(config_entries.OptionsFlowWithConfigEntry):
    """Handle the options flow for IPv64."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the options flow initialization step."""
        options = self.options
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_API_ECONOMY,
                    default=options.get(CONF_API_ECONOMY, True),
                ): BooleanSelector(BooleanSelectorConfig()),
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=options.get(CONF_SCAN_INTERVAL, 23),
                ): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.SLIDER,
                        min=0,
                        max=120,
                        step=1,
                        unit_of_measurement="minutes",
                    )
                ),
            }
        )
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            last_step=True,
            description_placeholders={"description": "Configure the update interval and economy mode for IPv64.net."},
        )
