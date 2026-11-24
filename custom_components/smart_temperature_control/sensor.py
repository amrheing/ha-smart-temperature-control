"""Room temperature (virtual sensor) and room setpoint with its reason."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import StcConfigEntry
from .const import REASON_ECO
from .entity import HouseEntity, RoomEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: StcConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    house = entry.runtime_data
    async_add_entities([HouseOverview(house, "overview")])
    for room in house.rooms.values():
        async_add_entities([RoomTemperatureSensor(room, "temperature"), RoomTargetSensor(room, "target")], config_subentry_id=room.id)


class RoomTemperatureSensor(RoomEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1

    @property
    def native_value(self) -> float | None:
        return self.room.temperature.value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "source": self.room.temperature.source,
            "sensors": {r.entity_id: {"value": r.value, "status": r.status} for r in self.room.temperature.readings},
        }


class RoomTargetSensor(RoomEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1

    @property
    def native_value(self) -> float:
        return self.room.decision.target

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.room.attributes()


class HouseOverview(HouseEntity, SensorEntity):
    """Number of rooms heating; attributes list eco/problem/manual rooms."""

    @property
    def native_value(self) -> int:
        return sum(1 for r in self.house.rooms.values() if not r.decision.resting)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        rooms = self.house.rooms.values()
        return {
            "eco": [r.name for r in rooms if r.decision.reason == REASON_ECO],
            "manual": [r.name for r in rooms if r.override],
            "problems": {r.name: r.problem for r in rooms if r.problem},
            "heat_source_mode": self.house.source_mode(dt_util.now()),
            "heat_source": self.house.heat_source.status(),
        }
