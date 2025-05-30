"""Support for reading status from IPv64.net."""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any

from homeassistant.components.sensor import RestoreSensor, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DOMAIN, CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DAILY_UPDATE_LIMIT,
    CONF_DYNDNS_UPDATES,
    CONF_REMAINING_UPDATES,
    DOMAIN,
    SHORT_NAME,
    TRACKER_UPDATE_STR,
)
from .coordinator import IPv64DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class IPv64BaseEntity(CoordinatorEntity[IPv64DataUpdateCoordinator], RestoreSensor):
    """Base entity class for IPv64."""

    _attr_force_update = False

    def __init__(self, coordinator: IPv64DataUpdateCoordinator, domain: str) -> None:
        """Initialize the IPv64 base entity."""
        super().__init__(coordinator)
        self._attr_attribution = "Data provided by IPv64.net | Free DynDNS2 & Healthcheck Service"
        self._data = DeviceInfo(
            identifiers={(DOMAIN, f"{domain}")},
            manufacturer="IPv64.net",
            model="DynDNS2 & Healthcheck DNS Service",
            name=f"{SHORT_NAME} {domain}",
            via_device=(SHORT_NAME, f"{domain}"),
        )
        self._unsub_dispatchers: list[Callable[[], None]] = []

    async def async_added_to_hass(self) -> None:
        """Run when the entity is added to Home Assistant."""
        await super().async_added_to_hass()
        if state := await self.async_get_last_sensor_data():
            self._attr_native_value = state.native_value
        self._unsub_dispatchers.append(async_dispatcher_connect(self.hass, TRACKER_UPDATE_STR, self.async_update))

    async def async_will_remove_from_hass(self) -> None:
        """Clean up before removing the entity."""
        for unsub in self._unsub_dispatchers[:]:
            unsub()
            self._unsub_dispatchers.remove(unsub)
        _LOGGER.debug("Entity removed from Home Assistant")

    async def async_update(self) -> None:
        """Perform an async update."""
        _LOGGER.debug("Updating entity data via coordinator")


class IPv64DynDNSStatusSensor(IPv64BaseEntity, SensorEntity):
    """Sensor for IPv64 DynDNS status."""

    def __init__(self, coordinator: IPv64DataUpdateCoordinator) -> None:
        """Initialize the IPv64 DynDNS sensor."""
        super().__init__(coordinator, coordinator.data[CONF_DOMAIN])
        self._attr_name = f"{SHORT_NAME} DynDNS Status"
        self._attr_unique_id = f"{DOMAIN}_dyndns_status"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("update_result", "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the extra state attributes of the sensor."""
        data = super().extra_state_attributes or {}
        if not self.coordinator.data:
            return data
        return {
            **data,
            CONF_DOMAIN: self.coordinator.data[CONF_DOMAIN],
            "account": self.coordinator.data.get("account", "unknown"),
            "account_status": self.coordinator.data.get("account_status", "unknown"),
            "reg_date": self.coordinator.data.get("reg_date"),
            "update_result": self.coordinator.data.get("update_result", "fail"),
            "info": self.coordinator.data.get("info", "unknown"),
            "status": self.coordinator.data.get("status", "unknown"),
            "last_update": self.coordinator.data.get("last_update"),
        }


class IPv64SettingSensor(IPv64BaseEntity, SensorEntity):
    """Sensor for IPv64 settings and counters."""

    def __init__(
        self,
        coordinator: IPv64DataUpdateCoordinator,
        name: str,
        key: str,
        attr_key: str | None = None,
    ) -> None:
        """Initialize the IPv64 setting sensor."""
        super().__init__(coordinator, coordinator.data[CONF_DOMAIN])
        self._attr_name = f"{SHORT_NAME} {name}"
        self._attr_unique_id = f"{DOMAIN}_{key}_"
        self._key = key
        self._attr_key = attr_key

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        return self.coordinator.data.get(self._key, "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the extra state attributes of the sensor."""
        data = super().extra_state_attributes or {}
        if self._attr_key and self.coordinator.data.get(self._attr_key):
            return {**data, self._attr_key: self.coordinator.data[self._attr_key]}
        return data


class IPv64DomainSensor(IPv64BaseEntity, SensorEntity):
    """Sensor for IPv64 domain IP address."""

    _attr_icon = "mdi:ip"

    def __init__(self, coordinator: IPv64DataUpdateCoordinator, subdomain: dict[str, Any]) -> None:
        """Initialize the IPv64 domain sensor."""
        super().__init__(coordinator, subdomain[CONF_DOMAIN])
        self._subdomain = subdomain
        self._attr_name = f"{SHORT_NAME} {subdomain[CONF_DOMAIN]} IP"
        self._attr_unique_id = f"{DOMAIN}_subdomain_{subdomain[CONF_DOMAIN]}"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        return self._subdomain.get(CONF_IP_ADDRESS, "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the extra state attributes of the sensor."""
        data = super().extra_state_attributes or {}
        if self.coordinator.data:
            subdomain_data = {k: v for k, v in self._subdomain.items() if k != "subdomains"}
            return {**data, **subdomain_data}
        return data


class IPv64DomainUpdateSensor(IPv64BaseEntity, SensorEntity):
    """Sensor for IPv64 domain update status."""

    def __init__(self, coordinator: IPv64DataUpdateCoordinator, subdomain: dict[str, Any]) -> None:
        """Initialize the IPv64 domain update sensor."""
        super().__init__(coordinator, subdomain[CONF_DOMAIN])
        self._subdomain = subdomain
        self._attr_name = f"{SHORT_NAME} {subdomain[CONF_DOMAIN]} Update"
        self._attr_unique_id = f"{DOMAIN}_{subdomain[CONF_DOMAIN]}_update"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("update_result", "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the extra state attributes of the sensor."""
        data = super().extra_state_attributes or {}
        return {**data, CONF_IP_ADDRESS: self._subdomain.get(CONF_IP_ADDRESS, "unknown")}


class IPv64RemainingUpdatesSensor(IPv64BaseEntity, SensorEntity):
    """Sensor for remaining IPv64 DynDNS updates."""

    _attr_icon = "mdi:counter"

    def __init__(self, coordinator: IPv64DataUpdateCoordinator) -> None:
        """Initialize the remaining updates sensor."""
        super().__init__(coordinator, coordinator.data[CONF_DOMAIN])
        self._attr_name = f"{SHORT_NAME} Remaining Updates"
        self._attr_unique_id = f"{DOMAIN}_remaining_updates"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        return self.coordinator.data.get(CONF_REMAINING_UPDATES, "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the extra state attributes of the sensor."""
        data = super().extra_state_attributes or {}
        return {
            **data,
            CONF_DYNDNS_UPDATES: self.coordinator.data.get(CONF_DYNDNS_UPDATES, "unknown"),
            CONF_DAILY_UPDATE_LIMIT: self.coordinator.data.get(CONF_DAILY_UPDATE_LIMIT, "unknown"),
        }


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IPv64 sensors from the config entry."""
    coordinator: IPv64DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[SensorEntity] = []

    if coordinator.data.get("owndomains"):
        entities.append(IPv64SettingSensor(coordinator, "Owner Domains", "owndomains", "owndomain_limit"))

    if coordinator.data.get("healthchecks_updates"):
        entities.append(
            IPv64SettingSensor(coordinator, "Healthcheck Counter Today", "healthchecks_updates", "healthcheck_update_limit")
        )

    if coordinator.data.get("sms_count") is not None:
        entities.append(IPv64SettingSensor(coordinator, "SMS Counter", "sms_count", "sms_limit"))

    if coordinator.data.get("api_updates") is not None:
        entities.append(IPv64SettingSensor(coordinator, "API Counter Today", "api_updates", "api_limit"))

    if coordinator.data.get("healthchecks") is not None:
        entities.append(IPv64SettingSensor(coordinator, "Healthchecks", "healthchecks", "healthcheck_limit"))

    if coordinator.data.get("dyndns_subdomains") is not None:
        entities.append(IPv64SettingSensor(coordinator, "DynDNS Domains", "dyndns_subdomains", "dyndns_domain_limit"))

    if coordinator.data.get(CONF_DYNDNS_UPDATES) is not None:
        entities.append(IPv64SettingSensor(coordinator, "DynDNS Counter Today", CONF_DYNDNS_UPDATES, "daily_update_limit"))

    if coordinator.data.get(CONF_REMAINING_UPDATES) is not None:
        entities.append(IPv64RemainingUpdatesSensor(coordinator))

    if coordinator.data.get("subdomains"):
        for subdomain in coordinator.data["subdomains"]:
            if coordinator.data[CONF_DOMAIN] == subdomain[CONF_DOMAIN]:
                entities.append(IPv64DomainSensor(coordinator, subdomain))
                entities.append(IPv64DomainUpdateSensor(coordinator, subdomain))

    if coordinator.data.get(CONF_DOMAIN):
        entities.append(IPv64DynDNSStatusSensor(coordinator))

    async_add_entities(entities)
