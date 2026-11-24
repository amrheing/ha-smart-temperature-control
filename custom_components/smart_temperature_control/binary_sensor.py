"""Eco period, window open and problem per room."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import StcConfigEntry
from .controller import Room
from .entity import RoomEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: StcConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    for room in entry.runtime_data.rooms.values():
        async_add_entities(
            [RoomBinary(room, "eco_period"), RoomBinary(room, "window"), RoomBinary(room, "problem"), RoomBinary(room, "manual")],
            config_subentry_id=room.id,
        )


class RoomBinary(RoomEntity, BinarySensorEntity):
    def __init__(self, room: Room, key: str) -> None:
        super().__init__(room, key)
        self._key = key
        self._attr_device_class = {
            "window": BinarySensorDeviceClass.WINDOW,
            "problem": BinarySensorDeviceClass.PROBLEM,
        }.get(key)

    @property
    def is_on(self) -> bool:
        if self._key == "eco_period":
            return not self.room.schedule.is_comfort(dt_util.now())
        if self._key == "window":
            return self.room.window_open
        if self._key == "manual":
            return self.room.override is not None
        return self.room.problem is not None or self.room.temperature.source != "sensors"
