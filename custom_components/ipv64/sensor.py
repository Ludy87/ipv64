"""Support for reading status from IPv64.net."""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import cast

from homeassistant.components.sensor import RestoreSensor, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DOMAIN, CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DYNDNS_UPDATES, DOMAIN, SHORT_NAME, TRACKER_UPDATE_STR
from .coordinator import IPv64DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class IPv64BaseEntity(CoordinatorEntity[IPv64DataUpdateCoordinator], RestoreSensor):
    """Base entity class for IPv64."""

    _attr_force_update = False

    def __init__(self, coordinator: IPv64DataUpdateCoordinator) -> None:
        """Initialize the IPv64 base entity."""
        super().__init__(coordinator)
        self._attr_attribution = "Data provided by IPv64.net | Free DynDNS2 & Healthcheck Service"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.data[CONF_DOMAIN]}")},
            manufacturer="IPv64.net",
            model="Free DynDNS2 & Healthcheck Service",
            name=f"{SHORT_NAME} {self.coordinator.data[CONF_DOMAIN]}",
            via_device=(SHORT_NAME, f"{self.coordinator.data[CONF_DOMAIN]}"),
        )
        self._unsub_dispatchers: list[Callable[[], None]] = []

    async def async_added_to_hass(self) -> None:
        """Run when the entity is added to Home Assistant."""
        await super().async_added_to_hass()
        if state := await self.async_get_last_sensor_data():
            self._attr_native_value = cast(float, state.native_value)
        self._unsub_dispatchers.append(async_dispatcher_connect(self.hass, TRACKER_UPDATE_STR, self.update))

    async def async_will_remove_from_hass(self) -> None:
        """Clean up before removing the entity."""
        for unsub in self._unsub_dispatchers[:]:
            unsub()
            self._unsub_dispatchers.remove(unsub)
        _LOGGER.debug("When entity is remove on hass")
        self._unsub_dispatchers = []

    async def update(self):
        """Perform an update."""
        _LOGGER.debug("update data in Coordinator")


class IPv64Sensor(IPv64BaseEntity, SensorEntity):
    """Sensor entity class for IPv64."""

    def __init__(
        self,
        coordinator: IPv64DataUpdateCoordinator,
    ) -> None:
        """Initialize the IPv64 sensor."""
        super().__init__(coordinator)

        self._attr_name: str = f"{SHORT_NAME}"
        self._attr_unique_id = f"{DOMAIN}"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("update_result", "fail")

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return the extra state attributes of the sensor."""
        data = super().extra_state_attributes or {}
        if self.coordinator.data:
            attr_data = {
                CONF_DOMAIN: self.coordinator.data[CONF_DOMAIN],
                "account": self.coordinator.data["account"],
                "account_status": self.coordinator.data["account_status"],
                "reg_date": self.coordinator.data["reg_date"],
                "update_result": self.coordinator.data.get("update_result", "fail"),
                "info": self.coordinator.data["info"],
                "status": self.coordinator.data["status"],
            }
            return dict(data, **attr_data)
        return dict(data, **{})


class IPv64SettingSesnor(IPv64BaseEntity, SensorEntity):
    """."""

    def __init__(
        self,
        coordinator: IPv64DataUpdateCoordinator,
        name,
        key,
        attr_key: str = None,
    ) -> None:
        """Initialize the IPv64 sensor."""
        super().__init__(coordinator)

        self._attr_name: str = f"{name} {SHORT_NAME}"
        self._attr_unique_id = f"{DOMAIN}_{name}"
        self._key = key
        self._attr_key = attr_key

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        return self.coordinator.data[self._key]

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return the extra state attributes of the sensor."""
        data = super().extra_state_attributes or {}
        if self._attr_key and self.coordinator.data[self._attr_key]:
            data = {self._attr_key: self.coordinator.data[self._attr_key]}
        return dict(data, **{})


class IPv64DomainSensor(IPv64BaseEntity, SensorEntity):
    """Sensor entity class for IPv64 Domain."""

    _attr_icon = "mdi:ip"

    def __init__(
        self,
        coordinator: IPv64DataUpdateCoordinator,
        subdomain,
    ) -> None:
        """Initialize the IPv64 sensor."""
        super().__init__(coordinator)

        self._subdomain = subdomain

        self._attr_name: str = f"{subdomain[CONF_DOMAIN]}"
        self._attr_unique_id = f"subdomain_{subdomain[CONF_DOMAIN]}"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        return self._subdomain[CONF_IP_ADDRESS]

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return the extra state attributes of the sensor."""
        data = super().extra_state_attributes or {}
        if self.coordinator.data:
            if "subdomains" in self.coordinator.data:
                del self.coordinator.data["subdomains"]
            return dict(data, **self._subdomain)
        return dict(data, **{})


class IPv64DomainUpdateSensor(IPv64BaseEntity, SensorEntity):
    """Sensor entity class for IPv64 Domain."""

    def __init__(
        self,
        coordinator: IPv64DataUpdateCoordinator,
        subdomain,
    ) -> None:
        """Initialize the IPv64 sensor."""
        super().__init__(coordinator)

        self._subdomain = subdomain

        self._attr_name: str = f"{subdomain[CONF_DOMAIN]} Update"
        self._attr_unique_id = f"{subdomain[CONF_DOMAIN]}_update"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("update_result", "fail")

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return the extra state attributes of the sensor."""
        data = {CONF_IP_ADDRESS: self._subdomain[CONF_IP_ADDRESS]}
        return dict(data, **{})


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IPv64 sensors from the config entry."""
    coordinator: IPv64DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities: list = []

    if coordinator.data["owndomains"]:
        entities.append(IPv64SettingSesnor(coordinator, "Owner Domains", "owndomains", "owndomain_limit"))

    if coordinator.data["healthchecks_updates"]:
        entities.append(
            IPv64SettingSesnor(coordinator, "Healthcheck counter today", "healthchecks_updates", "healthcheck_update_limit")
        )
    if coordinator.data["sms_count"] or coordinator.data["sms_count"] == 0:
        entities.append(IPv64SettingSesnor(coordinator, "SMS counter today", "sms_count", "sms_limit"))
    if coordinator.data["api_updates"] or coordinator.data["api_updates"] == 0:
        entities.append(IPv64SettingSesnor(coordinator, "API counter today", "api_updates", "api_limit"))

    if coordinator.data["healthchecks"] or coordinator.data["healthchecks"] == 0:
        entities.append(IPv64SettingSesnor(coordinator, "Healthchecks", "healthchecks", "healthcheck_limit"))

    if coordinator.data["dyndns_subdomains"] or coordinator.data["dyndns_subdomains"] == 0:
        entities.append(IPv64SettingSesnor(coordinator, "DynDNS Domains", "dyndns_subdomains", "dyndns_domain_limit"))

    if coordinator.data[CONF_DYNDNS_UPDATES] or coordinator.data[CONF_DYNDNS_UPDATES] == 0:
        entities.append(IPv64SettingSesnor(coordinator, "Dyndns counter today", CONF_DYNDNS_UPDATES, "daily_update_limit"))
    if "subdomains" in coordinator.data and coordinator.data["subdomains"]:
        for subdomain in coordinator.data["subdomains"]:
            if coordinator.data[CONF_DOMAIN] == subdomain[CONF_DOMAIN]:
                entities.append(IPv64DomainSensor(coordinator, subdomain))
                entities.append(IPv64DomainUpdateSensor(coordinator, subdomain))

    if coordinator.data[CONF_DOMAIN]:
        entities.append(IPv64Sensor(coordinator))
    async_add_entities(entities)
