"""The PVOutput Bridge integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import PVOutputBridgeConfigEntry, PVOutputBridgeCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

SERVICE_UPLOAD_NOW = "upload_now"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"

UPLOAD_NOW_SCHEMA = vol.Schema({vol.Required(ATTR_CONFIG_ENTRY_ID): str})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register integration-level services."""

    async def _async_upload_now(call: ServiceCall) -> None:
        entry_id: str = call.data[ATTR_CONFIG_ENTRY_ID]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            raise ServiceValidationError(
                f"Config entry {entry_id} is not a PVOutput Bridge entry",
                translation_domain=DOMAIN,
                translation_key="unknown_config_entry",
            )
        if entry.state is not ConfigEntryState.LOADED:
            raise ServiceValidationError(
                f"Config entry {entry_id} is not loaded",
                translation_domain=DOMAIN,
                translation_key="config_entry_not_loaded",
            )
        coordinator: PVOutputBridgeCoordinator = entry.runtime_data
        await coordinator.async_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPLOAD_NOW,
        _async_upload_now,
        schema=UPLOAD_NOW_SCHEMA,
    )
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: PVOutputBridgeConfigEntry
) -> bool:
    """Set up PVOutput Bridge from a config entry."""
    coordinator = PVOutputBridgeCoordinator(hass, entry)
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: PVOutputBridgeConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant, entry: PVOutputBridgeConfigEntry
) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
