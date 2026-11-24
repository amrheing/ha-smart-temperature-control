"""Switches: room heating / schedule / control, house summer / heat source."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import StcConfigEntry
from .controller import House, Room
from .entity import HouseEntity, RoomEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: StcConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    house = entry.runtime_data
    async_add_entities([HouseSwitch(house, "summer"), HouseSwitch(house, "control_heat_source")])
    for room in house.rooms.values():
        async_add_entities(
            [RoomSwitch(room, "on"), RoomSwitch(room, "schedule_enabled"), RoomSwitch(room, "control")],
            config_subentry_id=room.id,
        )


class RoomSwitch(RoomEntity, SwitchEntity):
    def __init__(self, room: Room, key: str) -> None:
        super().__init__(room, key)
        self._key = key
        if key == "control":
            self._attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool:
        return bool(self.room.stored[self._key])

    async def async_turn_on(self, **kwargs: Any) -> None:
        extra = {"schedule_enabled": True} if self._key == "on" else {}
        self.room.update(**{self._key: True}, **extra)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.room.update(**{self._key: False})


class HouseSwitch(HouseEntity, SwitchEntity):
    def __init__(self, house: House, key: str) -> None:
        super().__init__(house, key)
        self._key = key
        if key == "control_heat_source":
            self._attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool:
        return bool(self.house.h.get(self._key, False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.house.set_house(**{self._key: True})
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.house.set_house(**{self._key: False})
        self.async_write_ha_state()
