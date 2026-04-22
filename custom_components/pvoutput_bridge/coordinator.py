"""DataUpdateCoordinator that pushes PV status data to pvoutput.org."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_API_KEY,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import (
    BaseUnitConverter,
    ElectricPotentialConverter,
    EnergyConverter,
    PowerConverter,
    TemperatureConverter,
)

from .api import (
    PVOutputApiError,
    PVOutputAuthError,
    PVOutputClient,
    PVOutputRateLimitError,
    StatusPayload,
)
from .const import (
    CONF_CUMULATIVE,
    CONF_ENERGY_CONSUMPTION,
    CONF_ENERGY_GENERATION,
    CONF_INTERVAL_MINUTES,
    CONF_NET,
    CONF_POWER_CONSUMPTION,
    CONF_POWER_GENERATION,
    CONF_SYSTEM_ID,
    CONF_TEMPERATURE,
    CONF_VOLTAGE,
    DEFAULT_CUMULATIVE,
    DEFAULT_INTERVAL_MINUTES,
    DEFAULT_NET,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

RATE_LIMIT_ISSUE_ID_PREFIX = "rate_limit_exceeded_"


@dataclass(slots=True)
class UploadResult:
    """Outcome of a successful upload, stored as coordinator.data."""

    timestamp: datetime
    payload: StatusPayload


type PVOutputBridgeConfigEntry = ConfigEntry[PVOutputBridgeCoordinator]


class PVOutputBridgeCoordinator(DataUpdateCoordinator[UploadResult]):
    """Periodically read source entities and push status to PVOutput."""

    config_entry: PVOutputBridgeConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: PVOutputBridgeConfigEntry
    ) -> None:
        interval_minutes = int(
            entry.options.get(CONF_INTERVAL_MINUTES, DEFAULT_INTERVAL_MINUTES)
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=interval_minutes),
            config_entry=entry,
        )
        self.client = PVOutputClient(
            async_get_clientsession(hass),
            entry.data[CONF_API_KEY],
            entry.data[CONF_SYSTEM_ID],
        )
        self._interval_minutes = interval_minutes

    async def _async_update_data(self) -> UploadResult:
        payload = self._build_payload()
        if payload is None:
            raise UpdateFailed(
                "Power generation entity is unavailable; skipping upload"
            )

        try:
            await self.client.async_add_status(payload)
        except PVOutputAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except PVOutputRateLimitError as err:
            self._create_rate_limit_issue()
            raise UpdateFailed(f"PVOutput rate limit exceeded: {err}") from err
        except PVOutputApiError as err:
            raise UpdateFailed(f"PVOutput API error: {err}") from err

        self._clear_rate_limit_issue()
        return UploadResult(timestamp=payload.timestamp, payload=payload)

    def _rate_limit_issue_id(self) -> str:
        return f"{RATE_LIMIT_ISSUE_ID_PREFIX}{self.config_entry.entry_id}"

    def _create_rate_limit_issue(self) -> None:
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            self._rate_limit_issue_id(),
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="rate_limit_exceeded",
            translation_placeholders={"entry_title": self.config_entry.title},
        )

    def _clear_rate_limit_issue(self) -> None:
        ir.async_delete_issue(self.hass, DOMAIN, self._rate_limit_issue_id())

    def _build_payload(self) -> StatusPayload | None:
        options = self.config_entry.options

        power_gen_w = self._read_converted(
            options.get(CONF_POWER_GENERATION),
            PowerConverter,
            UnitOfPower.WATT,
        )
        if power_gen_w is None:
            return None

        return StatusPayload(
            timestamp=dt_util.now(),
            power_generation_w=power_gen_w,
            energy_generation_wh=self._read_converted(
                options.get(CONF_ENERGY_GENERATION),
                EnergyConverter,
                UnitOfEnergy.WATT_HOUR,
            ),
            power_consumption_w=self._read_converted(
                options.get(CONF_POWER_CONSUMPTION),
                PowerConverter,
                UnitOfPower.WATT,
            ),
            energy_consumption_wh=self._read_converted(
                options.get(CONF_ENERGY_CONSUMPTION),
                EnergyConverter,
                UnitOfEnergy.WATT_HOUR,
            ),
            temperature_c=self._read_converted(
                options.get(CONF_TEMPERATURE),
                TemperatureConverter,
                UnitOfTemperature.CELSIUS,
            ),
            voltage_v=self._read_converted(
                options.get(CONF_VOLTAGE),
                ElectricPotentialConverter,
                UnitOfElectricPotential.VOLT,
            ),
            cumulative=options.get(CONF_CUMULATIVE, DEFAULT_CUMULATIVE),
            net=options.get(CONF_NET, DEFAULT_NET),
        )

    def _read_converted(
        self,
        entity_id: str | None,
        converter: type[BaseUnitConverter],
        target_unit: str,
    ) -> float | None:
        """Read an entity's numeric state and convert to the PVOutput target unit."""
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        try:
            value = float(state.state)
        except (TypeError, ValueError):
            _LOGGER.warning(
                "Entity %s has non-numeric state %r; skipping", entity_id, state.state
            )
            return None
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        if unit is None:
            _LOGGER.warning(
                "Entity %s has no unit_of_measurement; assuming %s",
                entity_id,
                target_unit,
            )
            return value
        try:
            return converter.convert(value, unit, target_unit)
        except HomeAssistantError:
            _LOGGER.warning(
                "Cannot convert %s from %s to %s", entity_id, unit, target_unit
            )
            return None
