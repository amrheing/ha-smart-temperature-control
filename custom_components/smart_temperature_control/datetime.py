"""Vacation start / end."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import StcConfigEntry
from .controller import House
from .entity import HouseEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: StcConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    house = entry.runtime_data
    async_add_entities([VacationDateTime(house, "vacation_start"), VacationDateTime(house, "vacation_end")])


class VacationDateTime(HouseEntity, DateTimeEntity):
    def __init__(self, house: House, key: str) -> None:
        super().__init__(house, key)
        self._key = key

    @property
    def native_value(self) -> datetime | None:
        return getattr(self.house, self._key)

    async def async_set_value(self, value: datetime) -> None:
        self.house.set_house(**{self._key: value})
        self.async_write_ha_state()
