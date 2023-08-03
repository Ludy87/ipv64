"""Support for reading status from IPv64.net."""
from __future__ import annotations

from collections.abc import Callable
import logging
from typing import cast

from homeassistant.components.sensor import RestoreSensor, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DOMAIN, CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, TRACKER_UPDATE_STR
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
            name=f"{DOMAIN} {self.coordinator.data[CONF_DOMAIN]}",
            via_device=(DOMAIN, f"{self.coordinator.data[CONF_DOMAIN]}"),
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

    _attr_icon = "mdi:ip"

    def __init__(
        self,
        coordinator: IPv64DataUpdateCoordinator,
    ) -> None:
        """Initialize the IPv64 sensor."""
        super().__init__(coordinator)

        self._attr_name: str = f"{DOMAIN} {coordinator.data[CONF_DOMAIN]}"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.data[CONF_DOMAIN]}"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        if CONF_IP_ADDRESS in self.coordinator.data:
            return self.coordinator.data[CONF_IP_ADDRESS]

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return the extra state attributes of the sensor."""
        data = super().extra_state_attributes or {}
        if self.coordinator.data:
            if "subdomains" in self.coordinator.data:
                del self.coordinator.data["subdomains"]
            return dict(data, **self.coordinator.data)
        return dict(data, **{})


class IPv64SubSensor(IPv64BaseEntity, SensorEntity):
    """Sensor entity class for IPv64."""

    _attr_icon = "mdi:ip"

    def __init__(
        self,
        subdomain,
        coordinator: IPv64DataUpdateCoordinator,
    ) -> None:
        """Initialize the IPv64 sensor."""
        super().__init__(coordinator)

        self._subdomain = subdomain

        self._attr_name: str = f"subdomain {subdomain[CONF_DOMAIN]}"
        self._attr_unique_id = f"subdomain_{subdomain[CONF_DOMAIN]}"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        return self._subdomain[CONF_IP_ADDRESS]

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return the extra state attributes of the sensor."""
        data = super().extra_state_attributes or {}
        self._subdomain["update"] = "Update for this domain is not triggered"
        return dict(data, **self._subdomain)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IPv64 sensors from the config entry."""
    coordinator: IPv64DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities: list = []

    if coordinator.data[CONF_DOMAIN]:
        entities.append(IPv64Sensor(coordinator))
    if "subdomains" in coordinator.data and coordinator.data["subdomains"]:
        for subdomain in coordinator.data["subdomains"]:
            entities.append(IPv64SubSensor(subdomain, coordinator))
    async_add_entities(entities)
