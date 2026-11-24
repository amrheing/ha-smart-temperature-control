"""Comfort and eco temperature per room."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import StcConfigEntry
from .const import MAX_SETPOINT, MIN_SETPOINT
from .controller import Room
from .entity import RoomEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: StcConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    for room in entry.runtime_data.rooms.values():
        async_add_entities([RoomTemperatureNumber(room, "comfort"), RoomTemperatureNumber(room, "eco")], config_subentry_id=room.id)


class RoomTemperatureNumber(RoomEntity, NumberEntity):
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = MIN_SETPOINT
    _attr_native_max_value = MAX_SETPOINT
    _attr_native_step = 0.5
    _attr_mode = NumberMode.BOX

    def __init__(self, room: Room, key: str) -> None:
        super().__init__(room, key)
        self._key = key

    @property
    def native_value(self) -> float:
        return float(self.room.stored[self._key])

    async def async_set_native_value(self, value: float) -> None:
        self.room.update(**{self._key: value})
