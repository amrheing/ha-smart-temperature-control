"""House mode: Normal / Party / Urlaub — drives rooms and heat source."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import StcConfigEntry
from .const import HOUSE_MODES
from .entity import HouseEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: StcConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([HouseModeSelect(entry.runtime_data, "house_mode")])


class HouseModeSelect(HouseEntity, SelectEntity):
    _attr_options = HOUSE_MODES

    @property
    def current_option(self) -> str:
        return self.house.mode

    async def async_select_option(self, option: str) -> None:
        self.house.set_house(mode=option)
        self.async_write_ha_state()
