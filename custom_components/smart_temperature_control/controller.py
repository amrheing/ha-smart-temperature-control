"""House and room controllers: one place decides every room's setpoint."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, time, timedelta
import logging
from typing import Any

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE, STATE_ON
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_EXT_INTERVAL,
    CONF_EXTERNAL_INPUTS,
    CONF_NAME,
    CONF_NOTIFY,
    CONF_OFF_TEMPERATURE,
    CONF_PROFILE,
    CONF_RETRIES,
    CONF_SENSOR_MAX,
    CONF_SENSOR_MAX_JUMP,
    CONF_SENSOR_MIN,
    CONF_SENSOR_STALE,
    CONF_SENSORS,
    CONF_THERMOSTATS,
    CONF_VERIFY_DELAY,
    CONF_WINDOW_DELAY,
    CONF_WINDOWS,
    DEFAULT_COMFORT,
    DEFAULT_ECO,
    DEFAULT_EXT_INTERVAL,
    DEFAULT_OFF_TEMPERATURE,
    DEFAULT_RETRIES,
    DEFAULT_SENSOR_MAX,
    DEFAULT_SENSOR_MAX_JUMP,
    DEFAULT_SENSOR_MIN,
    DEFAULT_SENSOR_STALE,
    DEFAULT_VERIFY_DELAY,
    DEFAULT_WINDOW_DELAY,
    DOMAIN,
    HOUSE_NORMAL,
    HOUSE_PARTY,
    HOUSE_VACATION,
    MAX_SETPOINT,
    MIN_SETPOINT,
    PROFILE_AUTO,
    REASON_COMFORT,
    REASON_ECO,
    REASON_MANUAL,
    REASON_OFF,
    REASON_PARTY,
    REASON_PERMANENT_COMFORT,
    REASON_SUMMER,
    REASON_VACATION,
    REASON_WINDOW,
    RESTING_REASONS,
    SETPOINT_TOLERANCE,
    SIGNAL_HOUSE_UPDATED,
    SIGNAL_ROOM_UPDATED,
    SOURCE_SUMMER,
)
from .heat_source import HeatSource, build_heat_source
from .schedule import WeekSchedule, default_days, validate_days
from . import thermostat as trv
from .temperature import Limits, PlausibilityFilter, RoomTemperature, room_temperature

_LOGGER = logging.getLogger(__name__)
STORE_VERSION = 1
TICK = timedelta(minutes=1)


@dataclass(slots=True)
class Decision:
    target: float
    reason: str
    until: datetime | None

    @property
    def resting(self) -> bool:
        return self.reason in RESTING_REASONS


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse(value: str | None) -> datetime | None:
    return dt_util.parse_datetime(value) if value else None


class Room:
    """One room: config from its subentry, state in the house store."""

    def __init__(self, house: House, subentry: ConfigSubentry) -> None:
        self.house = house
        self.hass = house.hass
        self.id = subentry.subentry_id
        cfg = subentry.data
        self.name: str = cfg[CONF_NAME]
        self.thermostats: list[str] = list(cfg.get(CONF_THERMOSTATS, []))
        self.external_inputs: list[str] = list(cfg.get(CONF_EXTERNAL_INPUTS, []))
        self.sensors: list[str] = list(cfg.get(CONF_SENSORS, []))
        self.windows: list[str] = list(cfg.get(CONF_WINDOWS, []))
        self.window_delay = timedelta(seconds=cfg.get(CONF_WINDOW_DELAY, DEFAULT_WINDOW_DELAY))
        self.profile_key: str = cfg.get(CONF_PROFILE, PROFILE_AUTO)
        stored = house.data["rooms"].setdefault(self.id, {})
        stored.setdefault("on", True)
        stored.setdefault("schedule_enabled", True)
        stored.setdefault("comfort", DEFAULT_COMFORT)
        stored.setdefault("eco", DEFAULT_ECO)
        stored.setdefault("days", default_days())
        stored.setdefault("override", None)
        stored.setdefault("control", False)  # read-only until switched on
        self.stored = stored
        self.filter = PlausibilityFilter()
        self.temperature = RoomTemperature(None, "none")
        self.decision = Decision(stored["comfort"], REASON_COMFORT, None)
        self.window_open = False
        self.problem: str | None = None
        self._sent: dict[str, float | str] = {}
        self._retries = 0
        self._verify_unsub: Callable[[], None] | None = None
        self.planned: list[str] = []

    # ----- stored settings -------------------------------------------------
    @property
    def schedule(self) -> WeekSchedule:
        return WeekSchedule(self.stored["days"])

    @property
    def control(self) -> bool:
        return bool(self.stored["control"])

    def update(self, **values: Any) -> None:
        if "days" in values:
            values["days"] = validate_days(values["days"])
        for key in ("comfort", "eco"):
            if key in values:
                values[key] = max(MIN_SETPOINT, min(MAX_SETPOINT, float(values[key])))
        self.stored.update(values)
        if "on" in values or "schedule_enabled" in values:
            self.stored["override"] = None
        self.house.save()
        self.house.async_request(self)

    def set_override(self, temperature: float, now: datetime | None = None) -> None:
        now = now or dt_util.now()
        until = self.schedule.next_switch(now) if self.stored["schedule_enabled"] else None
        self.stored["override"] = {
            "temperature": max(MIN_SETPOINT, min(MAX_SETPOINT, round(temperature * 2) / 2)),
            "until": _iso(until or now + timedelta(hours=24)),
        }
        self.house.save()
        self.house.async_request(self)

    def clear_override(self) -> None:
        self.stored["override"] = None
        self.house.save()
        self.house.async_request(self)

    def save_override_as_period_value(self) -> None:
        """'Für diese Periode speichern': manual value becomes comfort or eco."""
        ov = self.stored.get("override")
        if not ov:
            return
        key = "comfort" if self.schedule.is_comfort(dt_util.now()) else "eco"
        self.stored[key] = ov["temperature"]
        self.stored["override"] = None
        self.house.save()
        self.house.async_request(self)

    @property
    def override(self) -> dict | None:
        return self.stored.get("override")

    # ----- decision ---------------------------------------------------------
    def _window_is_open(self, now: datetime) -> bool:
        for entity_id in self.windows:
            st = self.hass.states.get(entity_id)
            if st is not None and st.state == STATE_ON and now - st.last_changed >= self.window_delay:
                return True
        return False

    def compute(self, now: datetime) -> Decision:
        h = self.house
        off = h.off_temperature
        s = self.stored
        sched = self.schedule
        comfort_now = sched.is_comfort(now)
        nxt = sched.next_switch(now)
        self.window_open = self._window_is_open(now)
        ov = s.get("override")
        if ov and (_parse(ov.get("until")) or now) <= now:
            s["override"] = ov = None
            h.save()
        if h.summer:
            return Decision(off, REASON_SUMMER, None)
        if not s["on"]:
            return Decision(off, REASON_OFF, None)
        if h.vacation_active(now):
            return Decision(off, REASON_VACATION, h.vacation_end)
        if self.window_open:
            return Decision(off, REASON_WINDOW, None)
        if h.mode == HOUSE_PARTY:
            return Decision(s["comfort"], REASON_PARTY, h.party_end(now))
        if ov:
            return Decision(ov["temperature"], REASON_MANUAL, _parse(ov["until"]))
        if not s["schedule_enabled"]:
            return Decision(s["comfort"], REASON_PERMANENT_COMFORT, None)
        if comfort_now:
            return Decision(s["comfort"], REASON_COMFORT, nxt)
        return Decision(s["eco"], REASON_ECO, nxt)

    async def async_refresh(self, now: datetime | None = None) -> None:
        now = now or dt_util.now()
        self.temperature = room_temperature(
            self.filter,
            [self.hass.states.get(e) for e in self.sensors],
            [self.hass.states.get(e) for e in self.thermostats],
            now,
            self.house.limits,
        )
        new = self.compute(now)
        changed = (new.target, new.reason) != (self.decision.target, self.decision.reason)
        self.decision = new
        if changed:
            self._cancel_verify()
            self._retries = 0
            self._sent.clear()
        await self.async_disable_trv_window_detection()
        await self._async_apply()
        async_dispatcher_send(self.hass, SIGNAL_ROOM_UPDATED.format(self.id))

    # ----- actuator ---------------------------------------------------------
    def _profile(self, entity_id: str) -> trv.Profile:
        return trv.resolve_profile(self.hass, entity_id, self.profile_key)

    def _commands(self, entity_id: str) -> list[tuple[str, dict]]:
        st = self.hass.states.get(entity_id)
        prof = self._profile(entity_id)
        if self.decision.resting or self.decision.reason == REASON_WINDOW:
            if trv.reports_off(prof, st, self.house.off_temperature):
                return []
            return [trv.off_command(prof, st, self.house.off_temperature)]
        if trv.reports_setpoint(st, self.decision.target):
            return []
        return trv.heat_commands(prof, st, self.decision.target)

    async def _async_apply(self) -> None:
        self.planned = []
        want: float | str = "off" if self.decision.resting else self.decision.target
        for entity_id in self.thermostats:
            if self._sent.get(entity_id) == want:
                continue  # sent already; verification follows
            cmds = self._commands(entity_id)
            if not cmds:
                self._sent[entity_id] = want
                continue
            self.planned.append(entity_id)
            if not self.control:
                continue
            try:
                for service, data in cmds:
                    await trv.async_call(self.hass, entity_id, service, data)
            except Exception as err:  # noqa: BLE001 - radio errors must not stop other TRVs
                _LOGGER.warning("%s: %s not reachable: %s", self.name, entity_id, err)
            self._sent[entity_id] = want
        if self.control and self._sent and self._verify_unsub is None:
            self._verify_unsub = async_call_later(self.hass, self.house.verify_delay, self._async_verify)

    def _cancel_verify(self) -> None:
        if self._verify_unsub:
            self._verify_unsub()
            self._verify_unsub = None

    async def _async_verify(self, _now: datetime) -> None:
        self._verify_unsub = None
        failed = [e for e in self.thermostats if self._commands(e)]
        if not failed:
            if self.problem and self.problem.startswith("setpoint"):
                self.problem = None
                await self.house.async_notify(f"{self.name}: Sollwert jetzt übernommen.")
            async_dispatcher_send(self.hass, SIGNAL_ROOM_UPDATED.format(self.id))
            return
        self._retries += 1
        if self._retries <= self.house.retries:
            for e in failed:
                self._sent.pop(e, None)
            await self._async_apply()
            return
        self.problem = "setpoint_not_applied"
        await self.house.async_notify(
            f"{self.name}: Thermostat übernimmt den Sollwert nicht ({', '.join(failed)})."
        )
        async_dispatcher_send(self.hass, SIGNAL_ROOM_UPDATED.format(self.id))

    async def async_disable_trv_window_detection(self) -> None:
        """With own window contacts, the TRVs' built-in window detection is switched off.

        Otherwise a TRV may close on its own (temperature drop) and fight the
        setpoint we send. Only writes when a switch is still on.
        """
        if not self.control or not self.windows:
            return
        for climate_id in self.thermostats:
            for switch_id in trv.window_detection_switches(self.hass, climate_id):
                st = self.hass.states.get(switch_id)
                if st is None or st.state != STATE_ON:
                    continue
                try:
                    await self.hass.services.async_call(
                        "switch", "turn_off", {ATTR_ENTITY_ID: switch_id}, blocking=True
                    )
                    _LOGGER.info("%s: turned off TRV window detection %s", self.name, switch_id)
                except Exception as err:  # noqa: BLE001
                    _LOGGER.warning("%s: turning off %s failed: %s", self.name, switch_id, err)

    async def async_feed_external(self) -> None:
        """Write the room temperature to each TRV's external sensor input."""
        if not self.control or self.decision.resting or self.temperature.source != "sensors":
            return
        value = round(self.temperature.value, 1)
        for entity_id in self.external_inputs:
            try:
                await self.hass.services.async_call(
                    "number", "set_value", {ATTR_ENTITY_ID: entity_id, "value": value}, blocking=True
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("%s: external input %s failed: %s", self.name, entity_id, err)

    @callback
    def thermostat_changed(self, event: Event[EventStateChangedData]) -> None:
        """A setpoint we did not send is a manual change for this period."""
        new, old = event.data["new_state"], event.data["old_state"]
        if not self.control or new is None or old is None or self.decision.resting:
            return
        if self.decision.reason == REASON_WINDOW:
            return
        new_t, old_t = new.attributes.get(ATTR_TEMPERATURE), old.attributes.get(ATTR_TEMPERATURE)
        if new_t is None or new_t == old_t:
            return
        if abs(float(new_t) - self.decision.target) <= SETPOINT_TOLERANCE:
            return
        if float(new_t) <= self.house.off_temperature + SETPOINT_TOLERANCE:
            return
        self.set_override(float(new_t))

    def attributes(self) -> dict[str, Any]:
        return {
            "room": self.name,
            "thermostats": list(self.thermostats),
            "reason": self.decision.reason,
            "until": _iso(self.decision.until),
            "resting": self.decision.resting,
            "control": self.control,
            "planned_writes": list(self.planned),
            "temperature_source": self.temperature.source,
            "sensors": {r.entity_id: {"value": r.value, "status": r.status} for r in self.temperature.readings},
            "override": self.override,
            "problem": self.problem,
        }


class House:
    """Global state, store, timers and the heat source."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.store: Store[dict] = Store(hass, STORE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self.data: dict[str, Any] = {"house": {}, "rooms": {}}
        self.rooms: dict[str, Room] = {}
        self.heat_source: HeatSource = build_heat_source(hass, dict(entry.options))
        self._unsubs: list[Callable[[], None]] = []
        self._last_source_mode: str | None = None

    # ----- options ----------------------------------------------------------
    @property
    def _opt(self) -> dict:
        return self.entry.options

    @property
    def off_temperature(self) -> float:
        return float(self._opt.get(CONF_OFF_TEMPERATURE, DEFAULT_OFF_TEMPERATURE))

    @property
    def verify_delay(self) -> timedelta:
        return timedelta(minutes=self._opt.get(CONF_VERIFY_DELAY, DEFAULT_VERIFY_DELAY))

    @property
    def retries(self) -> int:
        return int(self._opt.get(CONF_RETRIES, DEFAULT_RETRIES))

    @property
    def limits(self) -> Limits:
        o = self._opt
        return Limits(
            float(o.get(CONF_SENSOR_MIN, DEFAULT_SENSOR_MIN)),
            float(o.get(CONF_SENSOR_MAX, DEFAULT_SENSOR_MAX)),
            float(o.get(CONF_SENSOR_MAX_JUMP, DEFAULT_SENSOR_MAX_JUMP)),
            int(o.get(CONF_SENSOR_STALE, DEFAULT_SENSOR_STALE)),
        )

    # ----- house state ------------------------------------------------------
    @property
    def h(self) -> dict:
        return self.data["house"]

    @property
    def mode(self) -> str:
        return self.h.get("mode", HOUSE_NORMAL)

    @property
    def summer(self) -> bool:
        return bool(self.h.get("summer", False))

    @property
    def control_heat_source(self) -> bool:
        return bool(self.h.get("control_heat_source", False))

    @property
    def party_until(self) -> time:
        return dt_util.parse_time(self.h.get("party_until", "23:30")) or time(23, 30)

    @property
    def vacation_start(self) -> datetime | None:
        return _parse(self.h.get("vacation_start"))

    @property
    def vacation_end(self) -> datetime | None:
        return _parse(self.h.get("vacation_end"))

    def party_end(self, now: datetime) -> datetime:
        end = now.replace(hour=self.party_until.hour, minute=self.party_until.minute, second=0, microsecond=0)
        started = _parse(self.h.get("party_started")) or now
        if end <= started:
            end += timedelta(days=1)
        return end

    def vacation_active(self, now: datetime) -> bool:
        start, end = self.vacation_start, self.vacation_end
        if end is not None and now >= end:
            return False
        if self.mode == HOUSE_VACATION:
            return start is None or now >= start
        return start is not None and end is not None and start <= now < end

    def source_mode(self, now: datetime) -> str:
        if self.summer:
            return SOURCE_SUMMER
        if self.vacation_active(now):
            return HOUSE_VACATION
        if self.mode == HOUSE_PARTY:
            return HOUSE_PARTY
        return HOUSE_NORMAL

    def set_house(self, **values: Any) -> None:
        if values.get("mode") == HOUSE_PARTY and self.mode != HOUSE_PARTY:
            values["party_started"] = _iso(dt_util.now())
        for key in ("vacation_start", "vacation_end"):
            if key in values and isinstance(values[key], datetime):
                values[key] = _iso(values[key])
        if "party_until" in values and isinstance(values["party_until"], time):
            values["party_until"] = values["party_until"].strftime("%H:%M")
        self.h.update(values)
        self.save()
        self.hass.async_create_task(self.async_refresh_all())

    # ----- lifecycle ----------------------------------------------------------
    async def async_load(self) -> None:
        stored = await self.store.async_load()
        if stored:
            self.data = stored
        self.data.setdefault("house", {})
        self.data.setdefault("rooms", {})
        for sub in self.entry.subentries.values():
            self.rooms[sub.subentry_id] = Room(self, sub)
        # forget rooms that were deleted
        for rid in list(self.data["rooms"]):
            if rid not in self.rooms:
                self.data["rooms"].pop(rid)

    @callback
    def async_start(self) -> None:
        for room in self.rooms.values():
            watched = room.sensors + room.windows
            if watched:
                self._unsubs.append(
                    async_track_state_change_event(self.hass, watched, self._room_listener(room))
                )
            if room.thermostats:
                self._unsubs.append(
                    async_track_state_change_event(self.hass, room.thermostats, room.thermostat_changed)
                )
        self._unsubs.append(async_track_time_interval(self.hass, self._tick, TICK))
        ext = timedelta(minutes=self._opt.get(CONF_EXT_INTERVAL, DEFAULT_EXT_INTERVAL))
        self._unsubs.append(async_track_time_interval(self.hass, self._feed, ext))

    def _room_listener(self, room: Room) -> Callable[[Event[EventStateChangedData]], None]:
        @callback
        def _changed(_event: Event[EventStateChangedData]) -> None:
            self.async_request(room)

        return _changed

    @callback
    def async_request(self, room: Room) -> None:
        self.hass.async_create_task(room.async_refresh())

    async def _tick(self, now: datetime) -> None:
        await self.async_refresh_all()

    async def _feed(self, _now: datetime) -> None:
        for room in self.rooms.values():
            await room.async_feed_external()

    async def async_refresh_all(self) -> None:
        now = dt_util.now()
        if self.mode == HOUSE_PARTY and now >= self.party_end(now):
            self.h["mode"] = HOUSE_NORMAL
            self.save()
        end = self.vacation_end
        if end is not None and now >= end:
            self.h.update(mode=HOUSE_NORMAL, vacation_start=None, vacation_end=None)
            self.save()
        for room in self.rooms.values():
            await room.async_refresh(now)
        mode = self.source_mode(now)
        if self.control_heat_source and mode != self._last_source_mode:
            try:
                await self.heat_source.async_set_mode(mode)
                self._last_source_mode = mode
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Heat source: setting %s failed: %s", mode, err)
        async_dispatcher_send(self.hass, SIGNAL_HOUSE_UPDATED.format(self.entry.entry_id))

    @callback
    def async_stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        for room in self.rooms.values():
            room._cancel_verify()

    def save(self) -> None:
        self.store.async_delay_save(lambda: self.data, 2)

    async def async_notify(self, message: str) -> None:
        service = self._opt.get(CONF_NOTIFY)
        if not service:
            return
        domain, _, name = service.partition(".")
        if not name:
            domain, name = "notify", domain
        try:
            await self.hass.services.async_call(
                domain, name, {"title": "Heizung", "message": message}, blocking=False
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Notify %s failed: %s", service, err)


__all__ = ["CLIMATE_DOMAIN", "Decision", "House", "Room"]
