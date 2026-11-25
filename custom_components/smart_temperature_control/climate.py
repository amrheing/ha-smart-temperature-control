"""The room regulator: one climate entity per room."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import StcConfigEntry
from .const import DOMAIN, MAX_SETPOINT, MIN_SETPOINT, REASON_ECO
from .controller import Room
from .entity import RoomEntity

PRESET_PLAN = "plan"
PRESET_COMFORT = "comfort"
PRESET_ECO = "eco"


async def async_setup_entry(
    hass: HomeAssistant, entry: StcConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    house = entry.runtime_data
    for room in house.rooms.values():
        async_add_entities([RoomClimate(room)], config_subentry_id=room.id)

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        "set_schedule",
        {vol.Required("days"): vol.All(cv.ensure_list, [cv.string])},
        "async_set_schedule",
    )


class RoomClimate(RoomEntity, ClimateEntity):
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_preset_modes = [PRESET_PLAN, PRESET_COMFORT, PRESET_ECO]
    _attr_min_temp = MIN_SETPOINT
    _attr_max_temp = MAX_SETPOINT
    _attr_target_temperature_step = 0.5
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, room: Room) -> None:
        super().__init__(room, None)
        self._attr_translation_key = "room"

    # changes every minute (last_seen) and is only for the dashboard
    _unrecorded_attributes = frozenset({"devices"})

    @property
    def hvac_mode(self) -> HVACMode:
        return HVACMode.HEAT if self.room.stored["on"] else HVACMode.OFF

    @property
    def current_temperature(self) -> float | None:
        return self.room.temperature.value

    @property
    def target_temperature(self) -> float | None:
        return self.room.decision.target

    @property
    def preset_mode(self) -> str:
        if self.room.override:
            return PRESET_ECO if self.room.override["temperature"] == self.room.stored["eco"] else PRESET_COMFORT
        return PRESET_PLAN

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        s = self.room.stored
        return {
            **self.room.attributes(),
            "comfort": s["comfort"],
            "eco": s["eco"],
            "schedule_enabled": s["schedule_enabled"],
            "eco_now": self.room.decision.reason == REASON_ECO,
            "days": s["days"],
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            self.room.set_override(float(temp))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        on = hvac_mode != HVACMode.OFF
        self.room.update(on=on, **({"schedule_enabled": True} if on else {}))

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == PRESET_PLAN:
            self.room.clear_override()
        elif preset_mode == PRESET_COMFORT:
            self.room.set_override(self.room.stored["comfort"])
        elif preset_mode == PRESET_ECO:
            self.room.set_override(self.room.stored["eco"])

    async def async_set_schedule(self, days: list[str]) -> None:
        try:
            self.room.update(days=days)
        except ValueError as err:
            raise ServiceValidationError(str(err), translation_domain=DOMAIN, translation_key="invalid_schedule") from err
