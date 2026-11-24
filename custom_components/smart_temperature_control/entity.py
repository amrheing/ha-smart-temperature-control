"""Base entities: one device for the house, one per room."""

from __future__ import annotations

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, SIGNAL_HOUSE_UPDATED, SIGNAL_ROOM_UPDATED
from .controller import House, Room


class HouseEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, house: House, key: str) -> None:
        self.house = house
        self._attr_translation_key = key
        self._attr_unique_id = f"{house.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, house.entry.entry_id)},
            name="Heizung Haus",
            manufacturer="Smart Temperatur Control",
            model="Haus",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_HOUSE_UPDATED.format(self.house.entry.entry_id), self.async_write_ha_state
            )
        )


class RoomEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, room: Room, key: str | None) -> None:
        self.room = room
        self._attr_translation_key = key
        self._attr_unique_id = f"{room.id}_{key or 'climate'}"
        area_id = room.house.entry.subentries[room.id].data.get("area")
        area_entry = ar.async_get(room.hass).async_get_area(area_id) if area_id else None
        area = area_entry.name if area_entry else None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, room.id)},
            name=f"Heizung {room.name}",
            manufacturer="Smart Temperatur Control",
            model="Raum",
            suggested_area=area or room.name,
            via_device=(DOMAIN, room.house.entry.entry_id),
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_ROOM_UPDATED.format(self.room.id), self.async_write_ha_state)
        )


def rooms_by_subentry(house: House) -> dict[str, Room]:
    return house.rooms
