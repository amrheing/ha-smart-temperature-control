"""Config flow: one entry 'Haus', one subentry per room, options for the house."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_AREA,
    CONF_EXT_INTERVAL,
    CONF_EXTERNAL_INPUTS,
    CONF_HEAT_SOURCE,
    CONF_HEAT_SOURCE_ENTITY,
    CONF_MAP_NORMAL,
    CONF_MAP_PARTY,
    CONF_MAP_SUMMER,
    CONF_MAP_VACATION,
    CONF_NAME,
    CONF_NOTIFY,
    CONF_OFF_TEMPERATURE,
    CONF_PROFILE,
    CONF_RETRIES,
    CONF_SENSOR_MAX,
    CONF_SENSOR_MAX_JUMP,
    CONF_SENSOR_MIN,
    CONF_SENSOR_STALE,
    CONF_SENSORS,
    CONF_THERMOSTATS,
    CONF_VERIFY_DELAY,
    CONF_WINDOW_DELAY,
    CONF_WINDOWS,
    DEFAULT_EXT_INTERVAL,
    DEFAULT_OFF_TEMPERATURE,
    DEFAULT_RETRIES,
    DEFAULT_SENSOR_MAX,
    DEFAULT_SENSOR_MAX_JUMP,
    DEFAULT_SENSOR_MIN,
    DEFAULT_SENSOR_STALE,
    DEFAULT_VERIFY_DELAY,
    DEFAULT_WINDOW_DELAY,
    DOMAIN,
    HEAT_SOURCE_ENTITY,
    HEAT_SOURCE_NONE,
    PROFILE_AUTO,
    PROFILES,
    SUBENTRY_ROOM,
)
from .thermostat import suggest_external_input

DEFAULT_OPTIONS = {
    CONF_OFF_TEMPERATURE: DEFAULT_OFF_TEMPERATURE,
    CONF_EXT_INTERVAL: DEFAULT_EXT_INTERVAL,
    CONF_VERIFY_DELAY: DEFAULT_VERIFY_DELAY,
    CONF_RETRIES: DEFAULT_RETRIES,
    CONF_SENSOR_MIN: DEFAULT_SENSOR_MIN,
    CONF_SENSOR_MAX: DEFAULT_SENSOR_MAX,
    CONF_SENSOR_MAX_JUMP: DEFAULT_SENSOR_MAX_JUMP,
    CONF_SENSOR_STALE: DEFAULT_SENSOR_STALE,
    CONF_HEAT_SOURCE: HEAT_SOURCE_NONE,
}


def _num(minimum: float, maximum: float, step: float, unit: str | None = None) -> selector.NumberSelector:
    config = selector.NumberSelectorConfig(min=minimum, max=maximum, step=step, mode=selector.NumberSelectorMode.BOX)
    if unit is not None:
        # HA rejects unit_of_measurement=None, which made the options form fail with 400.
        config["unit_of_measurement"] = unit
    return selector.NumberSelector(config)


class StcConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Heizung Haus", data={}, options=dict(DEFAULT_OPTIONS))
        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return StcOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry: ConfigEntry) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_ROOM: RoomSubentryFlow}


class StcOptionsFlow(OptionsFlow):
    """House settings: off temperature, timing, plausibility, heat source."""

    def __init__(self) -> None:
        self._opts: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        opts = {**DEFAULT_OPTIONS, **self.config_entry.options}
        if user_input is not None:
            self._opts = {**opts, **user_input}
            if user_input.get(CONF_HEAT_SOURCE) == HEAT_SOURCE_ENTITY:
                return await self.async_step_heat_source()
            return self.async_create_entry(data=self._opts)
        schema = vol.Schema(
            {
                vol.Required(CONF_OFF_TEMPERATURE, default=opts[CONF_OFF_TEMPERATURE]): _num(4, 10, 0.5, "°C"),
                vol.Required(CONF_EXT_INTERVAL, default=opts[CONF_EXT_INTERVAL]): _num(1, 29, 1, "min"),
                vol.Required(CONF_VERIFY_DELAY, default=opts[CONF_VERIFY_DELAY]): _num(5, 120, 1, "min"),
                vol.Required(CONF_RETRIES, default=opts[CONF_RETRIES]): _num(0, 10, 1),
                vol.Required(CONF_SENSOR_MIN, default=opts[CONF_SENSOR_MIN]): _num(-20, 20, 0.5, "°C"),
                vol.Required(CONF_SENSOR_MAX, default=opts[CONF_SENSOR_MAX]): _num(20, 60, 0.5, "°C"),
                vol.Required(CONF_SENSOR_MAX_JUMP, default=opts[CONF_SENSOR_MAX_JUMP]): _num(0.5, 20, 0.5, "K"),
                vol.Required(CONF_SENSOR_STALE, default=opts[CONF_SENSOR_STALE]): _num(5, 600, 5, "min"),
                vol.Optional(CONF_NOTIFY, description={"suggested_value": opts.get(CONF_NOTIFY)}): selector.TextSelector(),
                vol.Required(CONF_HEAT_SOURCE, default=opts[CONF_HEAT_SOURCE]): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=[HEAT_SOURCE_NONE, HEAT_SOURCE_ENTITY], translation_key="heat_source")
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_heat_source(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data={**self._opts, **user_input})
        o = self._opts
        schema = vol.Schema(
            {
                vol.Required(CONF_HEAT_SOURCE_ENTITY, description={"suggested_value": o.get(CONF_HEAT_SOURCE_ENTITY)}): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["select", "input_select", "switch", "input_boolean"])
                ),
                vol.Optional(CONF_MAP_NORMAL, description={"suggested_value": o.get(CONF_MAP_NORMAL)}): selector.TextSelector(),
                vol.Optional(CONF_MAP_PARTY, description={"suggested_value": o.get(CONF_MAP_PARTY)}): selector.TextSelector(),
                vol.Optional(CONF_MAP_VACATION, description={"suggested_value": o.get(CONF_MAP_VACATION)}): selector.TextSelector(),
                vol.Optional(CONF_MAP_SUMMER, description={"suggested_value": o.get(CONF_MAP_SUMMER)}): selector.TextSelector(),
            }
        )
        return self.async_show_form(step_id="heat_source", data_schema=schema)


def _room_schema(d: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=d.get(CONF_NAME, vol.UNDEFINED)): selector.TextSelector(),
            vol.Optional(CONF_AREA, description={"suggested_value": d.get(CONF_AREA)}): selector.AreaSelector(),
            vol.Required(CONF_THERMOSTATS, default=d.get(CONF_THERMOSTATS, [])): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="climate", multiple=True)
            ),
            vol.Optional(CONF_SENSORS, default=d.get(CONF_SENSORS, [])): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature", multiple=True)
            ),
            vol.Optional(CONF_WINDOWS, default=d.get(CONF_WINDOWS, [])): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
            ),
            vol.Required(CONF_WINDOW_DELAY, default=d.get(CONF_WINDOW_DELAY, DEFAULT_WINDOW_DELAY)): _num(0, 900, 5, "s"),
            vol.Required(CONF_PROFILE, default=d.get(CONF_PROFILE, PROFILE_AUTO)): selector.SelectSelector(
                selector.SelectSelectorConfig(options=PROFILES, translation_key="profile")
            ),
        }
    )


class RoomSubentryFlow(ConfigSubentryFlow):
    """Add or change a room."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get(CONF_THERMOSTATS):
                errors[CONF_THERMOSTATS] = "no_thermostat"
            else:
                self._data = user_input
                return await self.async_step_external()
        return self.async_show_form(step_id="user", data_schema=_room_schema(user_input or {}), errors=errors)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        current = dict(self._get_reconfigure_subentry().data)
        if user_input is not None:
            self._data = {**current, **user_input}
            return await self.async_step_external()
        return self.async_show_form(step_id="reconfigure", data_schema=_room_schema(current))

    async def async_step_external(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        if user_input is not None:
            data = {**self._data, CONF_EXTERNAL_INPUTS: user_input.get(CONF_EXTERNAL_INPUTS, [])}
            if self.source == "reconfigure":
                return self.async_update_and_abort(
                    self._get_entry(), self._get_reconfigure_subentry(), title=data[CONF_NAME], data=data
                )
            return self.async_create_entry(title=data[CONF_NAME], data=data)
        suggested = self._data.get(CONF_EXTERNAL_INPUTS) or [
            e for t in self._data[CONF_THERMOSTATS] if (e := suggest_external_input(self.hass, t))
        ]
        schema = vol.Schema(
            {
                vol.Optional(CONF_EXTERNAL_INPUTS, default=suggested): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="number", multiple=True)
                )
            }
        )
        return self.async_show_form(step_id="external", data_schema=schema)
