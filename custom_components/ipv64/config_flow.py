"""Config flow for IPv64."""
from __future__ import annotations

import logging

import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant import config_entries, core
from homeassistant.const import CONF_DOMAIN, CONF_SCAN_INTERVAL, CONF_TOKEN
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_API_ECONOMY,
    CONF_API_KEY,
    CONF_DAILY_UPDATE_LIMIT,
    CONF_DYNDNS_UPDATES,
    DATA_SCHEMA,
    DOMAIN,
    GET_ACCOUNT_INFO_URL,
    GET_DOMAIN_URL,
    TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class TokenError(Exception):
    """Exception Token."""


class APIKeyError(Exception):
    """Exception API Key."""


async def check_domain_login(hass: core.HomeAssistant, data: dict[str, str]):
    """Check the domain login information."""
    result = {}

    session: aiohttp.ClientSession = async_get_clientsession(hass)

    headers_api = {"Authorization": f"Bearer {data[CONF_API_KEY]}"}

    result.update(await get_domains(session, headers_api))
    result.update(await get_account_info(data, result, session, headers_api))

    _LOGGER.debug(result)
    return result


async def get_domains(session: aiohttp.ClientSession, headers_api: dict):
    """Fetches domain information from the IPv64.net API."""  # noqa: D401
    async with async_timeout.timeout(TIMEOUT):
        try:
            resp = await session.get(GET_DOMAIN_URL, headers=headers_api, raise_for_status=True)
            result = dict(await resp.json())
        except aiohttp.ClientResponseError as error:
            _LOGGER.error(
                "Your 'API Key' is incorrect. Error: %s | Status: %i",
                error.message,
                error.status,
            )
            raise TokenError() from error
    return result


async def get_account_info(
    data: dict[str, str],
    result: dict,
    session: aiohttp.ClientSession,
    headers_api: dict,
) -> dict:
    """Fetches account information from the IPv64.net API and updates the result."""  # noqa: D401
    async with async_timeout.timeout(TIMEOUT):
        try:
            resp_account_info = await session.get(GET_ACCOUNT_INFO_URL, headers=headers_api, raise_for_status=True)
            account_result = await resp_account_info.json()
            if account_result["update_hash"] != data[CONF_TOKEN]:
                raise APIKeyError()
            result.update(
                {
                    CONF_DAILY_UPDATE_LIMIT: account_result["account_class"]["dyndns_update_limit"],
                    CONF_DYNDNS_UPDATES: account_result[CONF_DYNDNS_UPDATES],
                }
            )
        except aiohttp.ClientResponseError as error:
            _LOGGER.error(
                "Your 'API Key' is incorrect. Error: %s | Status: %i",
                error.message,
                error.status,
            )
            raise APIKeyError() from error
    return result


async def validate_input(hass: core.HomeAssistant, data: dict[str, str]) -> dict[str, str]:
    """Validate the user input for domain login."""
    result = await check_domain_login(hass, data)
    return {"title": f"{DOMAIN} {data[CONF_DOMAIN]}", "data": result}


class IPv64ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for IPv64."""

    VERSION = 1

    @staticmethod
    @core.callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return IPv64OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial user step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            unique_id = f"{user_input[CONF_DOMAIN]}"
            await self.async_set_unique_id(unique_id)

            self._abort_if_unique_id_configured()

            info = None

            try:
                info = await validate_input(self.hass, user_input)
            except TokenError:
                errors["base"] = "unauthorized"
            except APIKeyError:
                errors["base"] = "invalid_api_key"

            if info and user_input[CONF_DOMAIN] not in info["data"]["subdomains"]:
                errors["base"] = "domain_not_found"
            elif not errors:
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

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(DATA_SCHEMA),
            errors=errors,
            last_step=False,
        )


class IPv64OptionsFlowHandler(config_entries.OptionsFlowWithConfigEntry):
    """Handle the options flow for IPv64."""

    async def async_step_init(self, user_input: dict[str, any] | None = None) -> FlowResult:
        """Handle the options flow initialization step."""
        options = self.options
        data_schema = vol.Schema(
            {
                vol.Required(CONF_API_ECONOMY, default=options.get(CONF_API_ECONOMY, False)): BooleanSelector(
                    BooleanSelectorConfig()
                ),
                vol.Required(CONF_SCAN_INTERVAL, default=options.get(CONF_SCAN_INTERVAL, 23)): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.SLIDER,
                        min=0,
                        max=120,
                        unit_of_measurement="minutes",
                    )
                ),
            }
        )
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(step_id="init", data_schema=data_schema, last_step=True)
