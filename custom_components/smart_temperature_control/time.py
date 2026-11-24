"""Party end time."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import StcConfigEntry
from .entity import HouseEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: StcConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([PartyUntil(entry.runtime_data, "party_until")])


class PartyUntil(HouseEntity, TimeEntity):
    @property
    def native_value(self) -> time:
        return self.house.party_until

    async def async_set_value(self, value: time) -> None:
        self.house.set_house(party_until=value)
        self.async_write_ha_state()
