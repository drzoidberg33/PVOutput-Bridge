"""Diagnostics support for the PVOutput Bridge integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, CONF_API_KEY
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ENERGY_CONSUMPTION,
    CONF_ENERGY_GENERATION,
    CONF_POWER_CONSUMPTION,
    CONF_POWER_GENERATION,
    CONF_SYSTEM_ID,
    CONF_TEMPERATURE,
    CONF_VOLTAGE,
)
from .coordinator import PVOutputBridgeConfigEntry

TO_REDACT = {CONF_API_KEY, CONF_SYSTEM_ID}

SOURCE_ENTITY_KEYS = (
    CONF_POWER_GENERATION,
    CONF_ENERGY_GENERATION,
    CONF_POWER_CONSUMPTION,
    CONF_ENERGY_CONSUMPTION,
    CONF_TEMPERATURE,
    CONF_VOLTAGE,
)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: PVOutputBridgeConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    last_upload: dict[str, Any] | None = None
    if coordinator.data is not None:
        last_upload = {
            "timestamp": coordinator.data.timestamp.isoformat(),
            "payload": coordinator.data.payload.to_params(),
        }

    source_entities: dict[str, Any] = {}
    for key in SOURCE_ENTITY_KEYS:
        entity_id = entry.options.get(key)
        if not entity_id:
            source_entities[key] = None
            continue
        state = hass.states.get(entity_id)
        source_entities[key] = {
            "entity_id": entity_id,
            "exists": state is not None,
            "state": state.state if state is not None else None,
            "unit": (
                state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
                if state is not None
                else None
            ),
        }

    rate_limit = coordinator.client.rate_limit
    update_interval = coordinator.update_interval

    return {
        "entry": async_redact_data(
            {
                "data": dict(entry.data),
                "options": dict(entry.options),
                "title": entry.title,
                "unique_id": entry.unique_id,
            },
            TO_REDACT,
        ),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": (
                str(coordinator.last_exception)
                if coordinator.last_exception
                else None
            ),
            "update_interval_seconds": (
                update_interval.total_seconds() if update_interval else None
            ),
        },
        "last_upload": last_upload,
        "rate_limit": {
            "remaining": rate_limit.remaining,
            "limit": rate_limit.limit,
            "reset": rate_limit.reset.isoformat() if rate_limit.reset else None,
        },
        "source_entities": source_entities,
    }
