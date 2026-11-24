"""Room buttons: back to plan, save manual value for this period, resend."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import StcConfigEntry
from .controller import Room
from .entity import RoomEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: StcConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    for room in entry.runtime_data.rooms.values():
        async_add_entities(
            [RoomButton(room, "back_to_plan"), RoomButton(room, "save_for_period"), RoomButton(room, "resend")],
            config_subentry_id=room.id,
        )


class RoomButton(RoomEntity, ButtonEntity):
    def __init__(self, room: Room, key: str) -> None:
        super().__init__(room, key)
        self._key = key

    async def async_press(self) -> None:
        if self._key == "back_to_plan":
            self.room.clear_override()
        elif self._key == "save_for_period":
            self.room.save_override_as_period_value()
        else:
            self.room._sent.clear()  # noqa: SLF001 - "Jetzt setzen"
            await self.room.async_refresh()
