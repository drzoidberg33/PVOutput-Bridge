"""Constants for the PVOutput Bridge integration."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "pvoutput_bridge"

CONF_API_KEY: Final = "api_key"
CONF_SYSTEM_ID: Final = "system_id"
CONF_POWER_GENERATION: Final = "power_generation"
CONF_ENERGY_GENERATION: Final = "energy_generation"
CONF_POWER_CONSUMPTION: Final = "power_consumption"
CONF_ENERGY_CONSUMPTION: Final = "energy_consumption"
CONF_TEMPERATURE: Final = "temperature"
CONF_VOLTAGE: Final = "voltage"
CONF_INTERVAL_MINUTES: Final = "interval_minutes"
CONF_CUMULATIVE: Final = "cumulative"
CONF_NET: Final = "net"

DEFAULT_INTERVAL_MINUTES: Final = 5
DEFAULT_CUMULATIVE: Final = False
DEFAULT_NET: Final = False

ALLOWED_INTERVALS: Final = (5, 10, 15)

PVOUTPUT_BASE_URL: Final = "https://pvoutput.org/service/r2"
