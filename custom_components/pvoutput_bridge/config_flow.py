"""Config flow for the PVOutput Bridge integration."""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PVOutputAuthError, PVOutputClient, PVOutputError
from .const import (
    ALLOWED_INTERVALS,
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

API_KEY_SELECTOR = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
)

CREDENTIALS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): API_KEY_SELECTOR,
        vol.Required(CONF_SYSTEM_ID): str,
    }
)

REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): API_KEY_SELECTOR})


def _sensor_selector(device_class: str) -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor", device_class=device_class)
    )


def _entity_options_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    """Build the schema for entity selection + upload options."""

    def _suggested(key: str) -> dict[str, Any]:
        if key in defaults and defaults[key] is not None:
            return {"description": {"suggested_value": defaults[key]}}
        return {}

    return vol.Schema(
        {
            vol.Required(
                CONF_POWER_GENERATION, **_suggested(CONF_POWER_GENERATION)
            ): _sensor_selector("power"),
            vol.Optional(
                CONF_ENERGY_GENERATION, **_suggested(CONF_ENERGY_GENERATION)
            ): _sensor_selector("energy"),
            vol.Optional(
                CONF_POWER_CONSUMPTION, **_suggested(CONF_POWER_CONSUMPTION)
            ): _sensor_selector("power"),
            vol.Optional(
                CONF_ENERGY_CONSUMPTION, **_suggested(CONF_ENERGY_CONSUMPTION)
            ): _sensor_selector("energy"),
            vol.Optional(
                CONF_TEMPERATURE, **_suggested(CONF_TEMPERATURE)
            ): _sensor_selector("temperature"),
            vol.Optional(
                CONF_VOLTAGE, **_suggested(CONF_VOLTAGE)
            ): _sensor_selector("voltage"),
            vol.Required(
                CONF_INTERVAL_MINUTES,
                default=defaults.get(CONF_INTERVAL_MINUTES, DEFAULT_INTERVAL_MINUTES),
            ): vol.In(ALLOWED_INTERVALS),
            vol.Required(
                CONF_CUMULATIVE,
                default=defaults.get(CONF_CUMULATIVE, DEFAULT_CUMULATIVE),
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_NET,
                default=defaults.get(CONF_NET, DEFAULT_NET),
            ): selector.BooleanSelector(),
        }
    )


class PVOutputBridgeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for PVOutput Bridge."""

    VERSION = 1

    def __init__(self) -> None:
        self._credentials: dict[str, str] = {}
        self._system_name: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Prompt for and validate PVOutput credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            system_id = user_input[CONF_SYSTEM_ID]
            await self.async_set_unique_id(system_id)
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = PVOutputClient(
                session, user_input[CONF_API_KEY], system_id
            )
            try:
                system_name = await client.async_validate_credentials()
            except PVOutputAuthError:
                errors["base"] = "invalid_auth"
            except PVOutputError:
                _LOGGER.exception("PVOutput credential check failed")
                errors["base"] = "cannot_connect"
            else:
                self._credentials = dict(user_input)
                self._system_name = system_name or f"System {system_id}"
                return await self.async_step_entities()

        return self.async_show_form(
            step_id="user",
            data_schema=CREDENTIALS_SCHEMA,
            errors=errors,
        )

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick source entities and configure upload options."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._system_name,
                data=self._credentials,
                options=user_input,
            )

        return self.async_show_form(
            step_id="entities",
            data_schema=_entity_options_schema({}),
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle a reauthentication triggered by an auth failure."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Prompt the user for a fresh API key and validate it."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        system_id = entry.data[CONF_SYSTEM_ID]

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = PVOutputClient(session, user_input[CONF_API_KEY], system_id)
            try:
                await client.async_validate_credentials()
            except PVOutputAuthError:
                errors["base"] = "invalid_auth"
            except PVOutputError:
                _LOGGER.exception("PVOutput credential check failed during reauth")
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data={**entry.data, CONF_API_KEY: user_input[CONF_API_KEY]},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            description_placeholders={"system_id": system_id},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return PVOutputBridgeOptionsFlow()


class PVOutputBridgeOptionsFlow(OptionsFlow):
    """Options flow for PVOutput Bridge."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit entity selections and upload options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_entity_options_schema(self.config_entry.options),
        )
