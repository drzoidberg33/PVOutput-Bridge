"""Diagnostic sensors for the PVOutput Bridge integration."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SYSTEM_ID, DOMAIN
from .coordinator import PVOutputBridgeConfigEntry, PVOutputBridgeCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PVOutputBridgeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the diagnostic sensors."""
    coordinator = entry.runtime_data
    system_id = entry.data[CONF_SYSTEM_ID]
    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="PVOutput.org",
        model="PVOutput System",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=f"https://pvoutput.org/list.jsp?sid={system_id}",
    )
    async_add_entities(
        [
            LastUploadSensor(coordinator, entry, device_info),
            LastStatusSensor(coordinator, entry, device_info),
            RateLimitRemainingSensor(coordinator, entry, device_info),
        ]
    )


class PVOutputBridgeSensorBase(
    CoordinatorEntity[PVOutputBridgeCoordinator], SensorEntity
):
    """Base class for PVOutput Bridge diagnostic sensors."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: PVOutputBridgeCoordinator,
        entry: PVOutputBridgeConfigEntry,
        device_info: DeviceInfo,
        *,
        key: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = device_info

    @property
    def available(self) -> bool:
        # Diagnostic sensors must stay visible even when uploads fail —
        # that's precisely when the user needs to see them.
        return True


class LastUploadSensor(PVOutputBridgeSensorBase):
    """Timestamp of the most recent successful upload."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: PVOutputBridgeCoordinator,
        entry: PVOutputBridgeConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator, entry, device_info, key="last_upload")

    @property
    def native_value(self) -> datetime | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.timestamp


class LastStatusSensor(PVOutputBridgeSensorBase):
    """Outcome of the most recent upload attempt."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["ok", "error"]

    def __init__(
        self,
        coordinator: PVOutputBridgeCoordinator,
        entry: PVOutputBridgeConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator, entry, device_info, key="last_status")

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None and self.coordinator.last_exception is None:
            return None
        return "ok" if self.coordinator.last_update_success else "error"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        exc = self.coordinator.last_exception
        return {"error_message": str(exc) if exc else None}


class RateLimitRemainingSensor(PVOutputBridgeSensorBase):
    """Number of PVOutput API requests remaining in the current window."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: PVOutputBridgeCoordinator,
        entry: PVOutputBridgeConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(
            coordinator, entry, device_info, key="rate_limit_remaining"
        )

    @property
    def native_value(self) -> int | None:
        return self.coordinator.client.rate_limit.remaining

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        rate_limit = self.coordinator.client.rate_limit
        return {
            "limit": rate_limit.limit,
            "reset": rate_limit.reset,
        }
