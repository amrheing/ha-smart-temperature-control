"""Weekly comfort/eco schedule: 7 days x N slots, 'k' = comfort, 'e' = eco."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

COMFORT = "k"
ECO = "e"
VALID_SLOTS = (24, 48, 96)
DEFAULT_SLOTS = 48


def default_days(start: str = "06:00", end: str = "22:00", slots: int = DEFAULT_SLOTS) -> list[str]:
    """Comfort from start to end on every day."""
    per = 1440 // slots
    s = _minutes(start) // per
    e = _minutes(end) // per
    row = "".join(COMFORT if s <= i < e else ECO for i in range(slots))
    return [row] * 7


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")[:2]
    return int(h) * 60 + int(m)


def validate_days(days: list[str]) -> list[str]:
    """Raise ValueError unless days is 7 equal-length strings of k/e."""
    if not isinstance(days, list) or len(days) != 7:
        raise ValueError("schedule needs exactly 7 days (Monday first)")
    length = len(days[0]) if days else 0
    if length not in VALID_SLOTS:
        raise ValueError(f"each day needs {', '.join(map(str, VALID_SLOTS))} slots")
    for day in days:
        if not isinstance(day, str) or len(day) != length or set(day) - {COMFORT, ECO}:
            raise ValueError("days must be strings of 'k' (comfort) and 'e' (eco) of equal length")
    return list(days)


@dataclass
class WeekSchedule:
    days: list[str]

    @property
    def slots(self) -> int:
        return len(self.days[0])

    @property
    def slot_minutes(self) -> int:
        return 1440 // self.slots

    def _index(self, when: datetime) -> tuple[int, int]:
        return when.weekday(), (when.hour * 60 + when.minute) // self.slot_minutes

    def is_comfort(self, when: datetime) -> bool:
        day, slot = self._index(when)
        return self.days[day][slot] == COMFORT

    def next_switch(self, when: datetime) -> datetime | None:
        """Start of the next slot whose value differs from now; None if constant."""
        day, slot = self._index(when)
        current = self.days[day][slot]
        start = when.replace(second=0, microsecond=0) - timedelta(
            minutes=(when.hour * 60 + when.minute) % self.slot_minutes
        )
        for step in range(1, 7 * self.slots + 1):
            d = (day + (slot + step) // self.slots) % 7
            s = (slot + step) % self.slots
            if self.days[d][s] != current:
                return start + timedelta(minutes=step * self.slot_minutes)
        return None
