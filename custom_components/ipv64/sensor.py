"""Support for reading status from IPv64.net."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import RestoreSensor, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DOMAIN, CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry, DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DAILY_UPDATE_LIMIT, CONF_DYNDNS_UPDATES, CONF_REMAINING_UPDATES, DOMAIN, SHORT_NAME
from .coordinator import IPv64DataUpdateCoordinator
from .models import IPv64RuntimeData

_LOGGER = logging.getLogger(__name__)


class IPv64BaseEntity(CoordinatorEntity[IPv64DataUpdateCoordinator], RestoreSensor):
    """Base entity class for IPv64."""

    _attr_available = False
    _attr_force_update = True  # Ensure updates are always sent to Home Assistant
    device_entry: DeviceEntry

    def __init__(self, coordinator: IPv64DataUpdateCoordinator, domain: str) -> None:
        """Initialize the IPv64 base entity."""
        super().__init__(coordinator)
        self._attr_attribution = "Data provided by IPv64.net | Free DynDNS2 & Healthcheck Service"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, domain)},
            manufacturer="IPv64.net",
            model="DynDNS2 & Healthcheck DNS Service",
            name=f"{SHORT_NAME} {domain}",
        )

    async def async_added_to_hass(self) -> None:
        """Run when the entity is added to Home Assistant."""
        await super().async_added_to_hass()
        if state := await self.async_get_last_sensor_data():
            self._attr_native_value = state.native_value
        # Removed TRACKER_UPDATE_STR dispatcher as it's unused
        self._attr_available = True  # Set available after initialization

    async def async_will_remove_from_hass(self) -> None:
        """Clean up before removing the entity."""
        await super().async_will_remove_from_hass()
        _LOGGER.debug("Entity %s removed from Home Assistant", self.entity_id)


class IPv64DynDNSStatusSensor(IPv64BaseEntity, SensorEntity):
    """Sensor for IPv64 DynDNS status."""

    def __init__(self, coordinator: IPv64DataUpdateCoordinator) -> None:
        """Initialize the IPv64 DynDNS sensor."""
        super().__init__(coordinator, coordinator.data[CONF_DOMAIN])
        self._attr_name = f"{SHORT_NAME} {coordinator.data[CONF_DOMAIN]} Status"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.data[CONF_DOMAIN]}_status"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        return (
            self.coordinator.data.get("status", "unknown").split(" ", 1)[1]
            if self.coordinator.data.get("status")
            else "unknown"
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the extra state attributes of the sensor."""
        data = super().extra_state_attributes or {}
        if not self.coordinator.data:
            return data
        return {
            **data,
            CONF_DOMAIN: self.coordinator.data[CONF_DOMAIN],
            "account_status": self.coordinator.data["account_status"],
            "reg_date": self.coordinator.data["reg_date"],
            "dyndns_updates": self.coordinator.data.get(CONF_DYNDNS_UPDATES, 0),
            "dyndns_subdomains": self.coordinator.data.get("dyndns_subdomains", 0),
            "owndomains": self.coordinator.data.get("owndomains", 0),
            "healthchecks": self.coordinator.data.get("healthchecks", 0),
            "healthchecks_updates": self.coordinator.data.get("healthchecks_updates", 0),
            "api_updates": self.coordinator.data.get("api_updates", 0),
            "sms_count": self.coordinator.data.get("sms_count", 0),
            "account": self.coordinator.data.get("account", "unknown"),
            "dyndns_domain_limit": self.coordinator.data.get("dyndns_domain_limit", 0),
            CONF_DAILY_UPDATE_LIMIT: self.coordinator.data.get(CONF_DAILY_UPDATE_LIMIT, 0),
            "owndomain_limit": self.coordinator.data.get("owndomain_limit", 0),
            "healthcheck_limit": self.coordinator.data.get("healthcheck_limit", 0),
            "healthcheck_update_limit": self.coordinator.data.get("healthcheck_update_limit", 0),
            "dyndns_ttl": self.coordinator.data.get("dyndns_ttl", 0),
            "api_limit": self.coordinator.data.get("api_limit", 0),
            "sms_limit": self.coordinator.data.get("sms_limit", 0),
            "info": self.coordinator.data.get("info", "unknown"),
            "status": self.coordinator.data.get("status", "unknown"),
        }


class IPv64LastUpdateSensor(IPv64BaseEntity, SensorEntity):
    """Sensor for the last update time of IPv64."""

    _attr_icon = "mdi:clock"

    def __init__(self, coordinator: IPv64DataUpdateCoordinator) -> None:
        """Initialize the IPv64 last update sensor."""
        super().__init__(coordinator, coordinator.data[CONF_DOMAIN])
        self._attr_name = f"{SHORT_NAME} {coordinator.data[CONF_DOMAIN]} Last Update"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.data[CONF_DOMAIN]}_last_update"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        last_update = "unknown"
        for subdomain in self.coordinator.data.get("subdomains", []):
            if subdomain.get(CONF_DOMAIN) == self.coordinator.data[CONF_DOMAIN]:
                last_update = subdomain.get("last_update", "unknown")
        return last_update

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the extra state attributes of the sensor."""
        data = super().extra_state_attributes or {}
        for subdomain in self.coordinator.data.get("subdomains", []):
            if subdomain.get(CONF_DOMAIN) == self.coordinator.data[CONF_DOMAIN]:
                last_update = subdomain.get("last_update", "unknown")
                if last_update != "unknown":
                    return {**data, "last_update": last_update}
        return {**data}


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
        self._attr_name = f"{SHORT_NAME} {coordinator.data[CONF_DOMAIN]} {name}"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.data[CONF_DOMAIN]}_{key}"
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

    def __init__(self, coordinator: IPv64DataUpdateCoordinator, domain: str) -> None:
        """Initialize the IPv64 domain sensor."""
        super().__init__(coordinator, domain)
        self._domain = domain
        self._attr_name = f"{SHORT_NAME} {domain} IP"
        self._attr_unique_id = f"{DOMAIN}_{domain}_ip"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        for subdomain in self.coordinator.data.get("subdomains", []):
            if subdomain.get(CONF_DOMAIN) == self._domain:
                return subdomain.get(CONF_IP_ADDRESS, "unknown")
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the extra state attributes of the sensor."""
        data = super().extra_state_attributes or {}
        if not self.coordinator.data:
            return data
        for subdomain in self.coordinator.data.get("subdomains", []):
            if subdomain.get(CONF_DOMAIN) == self._domain:
                subdomain_data = {k: v for k, v in subdomain.items() if k != "subdomains"}
                main_domain = self._domain.split(".", 1)[1] if "." in self._domain else self._domain
                metadata = self.coordinator.data.get(f"{main_domain}_metadata", {})
                if metadata.get("wildcard"):
                    subdomain_data["wildcard"] = metadata["wildcard"]
                return {**data, **subdomain_data}
        return data


class IPv64RemainingUpdatesSensor(IPv64BaseEntity, SensorEntity):
    """Sensor for remaining IPv64 DynDNS updates."""

    _attr_icon = "mdi:counter"

    def __init__(self, coordinator: IPv64DataUpdateCoordinator) -> None:
        """Initialize the remaining updates sensor."""
        super().__init__(coordinator, coordinator.data[CONF_DOMAIN])
        self._attr_name = f"{SHORT_NAME} {coordinator.data[CONF_DOMAIN]} Remaining Updates"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.data[CONF_DOMAIN]}_remaining_updates"

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
    runtime_data: IPv64RuntimeData = hass.data[DOMAIN][config_entry.entry_id]
    coordinator: IPv64DataUpdateCoordinator = runtime_data.coordinator
    entities: list[SensorEntity] = []

    if not coordinator.data.get("subdomains"):
        _LOGGER.warning("No subdomains available for %s, skipping domain sensors", config_entry.entry_id)
    else:
        entities.extend(
            [IPv64DomainSensor(coordinator, subdomain[CONF_DOMAIN]) for subdomain in coordinator.data["subdomains"]]
        )
        entities.append(IPv64LastUpdateSensor(coordinator))

    if coordinator.data.get(CONF_DYNDNS_UPDATES) is not None:
        entities.append(IPv64SettingSensor(coordinator, "DynDNS Counter Today", CONF_DYNDNS_UPDATES, "daily_update_limit"))

    if coordinator.data.get(CONF_REMAINING_UPDATES) is not None:
        entities.append(IPv64RemainingUpdatesSensor(coordinator))

    if coordinator.data.get(CONF_DOMAIN):
        entities.append(IPv64DynDNSStatusSensor(coordinator))

    async_add_entities(entities)
