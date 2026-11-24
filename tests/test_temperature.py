"""Virtual room temperature and plausibility."""

from datetime import timedelta

from homeassistant.core import State
from homeassistant.util import dt as dt_util

from custom_components.smart_temperature_control.temperature import (
    JUMP,
    OK,
    OUT_OF_RANGE,
    UNAVAILABLE,
    Limits,
    PlausibilityFilter,
    room_temperature,
)

LIM = Limits(0, 40, 3, 60)


def _s(entity_id, value, ago=0):
    now = dt_util.utcnow()
    st = State(entity_id, str(value), last_updated=now - timedelta(minutes=ago), last_reported=now - timedelta(minutes=ago))
    return st


def test_average_ignores_bad_values():
    f = PlausibilityFilter()
    now = dt_util.utcnow()
    t = room_temperature(f, [_s("sensor.a", 20.0), _s("sensor.b", 21.0), _s("sensor.c", 85), _s("sensor.d", "unavailable")], [], now, LIM)
    assert t.value == 20.5
    assert t.source == "sensors"
    assert [r.status for r in t.readings] == [OK, OK, OUT_OF_RANGE, UNAVAILABLE]


def test_jump_is_ignored_then_accepted_after_window():
    f = PlausibilityFilter()
    now = dt_util.utcnow()
    assert f.check(_s("sensor.a", 20.0), now, LIM).status == OK
    assert f.check(_s("sensor.a", 27.0), now + timedelta(minutes=1), LIM).status == JUMP
    assert f.check(_s("sensor.a", 27.0), now + timedelta(minutes=6), LIM).status == OK


def test_fallback_to_thermostat():
    f = PlausibilityFilter()
    trv = State("climate.t", "heat", {"current_temperature": 19.5})
    t = room_temperature(f, [_s("sensor.a", "unavailable")], [trv], dt_util.utcnow(), LIM)
    assert (t.value, t.source) == (19.5, "thermostats")
