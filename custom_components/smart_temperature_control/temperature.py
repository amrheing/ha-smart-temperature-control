"""Virtual room temperature: plausible room sensors, else the thermostats."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from homeassistant.components.climate import ATTR_CURRENT_TEMPERATURE
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import State

from .const import JUMP_WINDOW_MINUTES

OK = "ok"
UNAVAILABLE = "unavailable"
OUT_OF_RANGE = "out_of_range"
JUMP = "jump"
STALE = "stale"


@dataclass(slots=True)
class Limits:
    minimum: float
    maximum: float
    max_jump: float
    stale_minutes: int


@dataclass(slots=True)
class SensorReading:
    entity_id: str
    value: float | None
    status: str


@dataclass(slots=True)
class RoomTemperature:
    value: float | None
    source: str  # "sensors" | "thermostats" | "none"
    readings: list[SensorReading] = field(default_factory=list)


class PlausibilityFilter:
    """Remembers the last accepted value per sensor to spot jumps."""

    def __init__(self) -> None:
        self._last: dict[str, tuple[float, datetime]] = {}

    def check(self, state: State | None, now: datetime, limits: Limits) -> SensorReading:
        entity_id = state.entity_id if state else "?"
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN, ""):
            return SensorReading(entity_id, None, UNAVAILABLE)
        try:
            value = float(state.state)
        except ValueError:
            return SensorReading(entity_id, None, UNAVAILABLE)
        if not limits.minimum <= value <= limits.maximum:
            return SensorReading(entity_id, value, OUT_OF_RANGE)
        seen = getattr(state, "last_reported", None) or state.last_updated
        if now - seen > timedelta(minutes=limits.stale_minutes):
            return SensorReading(entity_id, value, STALE)
        prev = self._last.get(entity_id)
        if (
            prev is not None
            and now - prev[1] <= timedelta(minutes=JUMP_WINDOW_MINUTES)
            and abs(value - prev[0]) > limits.max_jump
        ):
            # Not accepted; the old reference stays. A value that holds for
            # longer than the jump window is accepted then (real change).
            return SensorReading(entity_id, value, JUMP)
        self._last[entity_id] = (value, now)
        return SensorReading(entity_id, value, OK)


def room_temperature(
    flt: PlausibilityFilter,
    sensor_states: list[State | None],
    thermostat_states: list[State | None],
    now: datetime,
    limits: Limits,
) -> RoomTemperature:
    readings = [flt.check(s, now, limits) for s in sensor_states]
    good = [r.value for r in readings if r.status == OK and r.value is not None]
    if good:
        return RoomTemperature(round(sum(good) / len(good), 2), "sensors", readings)
    trv = []
    for st in thermostat_states:
        if st is None:
            continue
        val = st.attributes.get(ATTR_CURRENT_TEMPERATURE)
        if isinstance(val, (int, float)) and limits.minimum <= val <= limits.maximum:
            trv.append(float(val))
    if trv:
        return RoomTemperature(round(sum(trv) / len(trv), 2), "thermostats", readings)
    return RoomTemperature(None, "none", readings)
