"""Week schedule."""

from datetime import datetime

import pytest

from custom_components.smart_temperature_control.schedule import WeekSchedule, default_days, validate_days


def test_default_and_next_switch():
    s = WeekSchedule(default_days("06:00", "22:00"))
    tue_1830 = datetime(2026, 11, 24, 18, 30)  # Tuesday
    assert s.is_comfort(tue_1830)
    assert s.next_switch(tue_1830) == datetime(2026, 11, 24, 22, 0)
    late = datetime(2026, 11, 24, 23, 10)
    assert not s.is_comfort(late)
    assert s.next_switch(late) == datetime(2026, 11, 25, 6, 0)


def test_constant_schedule_has_no_switch():
    s = WeekSchedule(["e" * 24] * 7)
    assert s.next_switch(datetime(2026, 11, 24, 12, 0)) is None


def test_validate():
    with pytest.raises(ValueError):
        validate_days(["k" * 48] * 6)
    with pytest.raises(ValueError):
        validate_days(["x" * 48] * 7)
    assert validate_days(["k" * 96] * 7)[0] == "k" * 96
