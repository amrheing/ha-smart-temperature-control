"""Thermostat profiles: how a room's TRVs are switched off, set and fed.

A profile only describes HOW to talk to one climate entity; the room
controller decides WHAT it should do. New brands are added here.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_HVAC_MODES,
    ATTR_MIN_TEMP,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACMode,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util

from .const import (
    PROFILE_AUTO,
    PROFILE_DANFOSS_ALLY,
    PROFILE_GENERIC,
    PROFILE_SHELLY_TRV,
    SETPOINT_TOLERANCE,
)

# Words that mark a TRV's "external room sensor" number entity.
_EXTERNAL_HINTS = ("external_temperature", "externer_temperatursensor", "external_measured_room_sensor", "external_temperature_input")


@dataclass(frozen=True, slots=True)
class Profile:
    key: str
    #: True: the device has no real "off"; off = lowest setpoint (Danfoss Ally).
    off_by_setpoint: bool
    #: Interval matters: the TRV drops back to its own sensor without fresh values.
    external_required_interval: int | None


PROFILE_DEFS: dict[str, Profile] = {
    PROFILE_DANFOSS_ALLY: Profile(PROFILE_DANFOSS_ALLY, True, 30),
    # Shelly TRV (gen1, hvac off/heat) and Shelly BLU TRV (heat only, external
    # temperature as number entity). Off: hvac off where offered, else setpoint.
    PROFILE_SHELLY_TRV: Profile(PROFILE_SHELLY_TRV, False, None),
    PROFILE_GENERIC: Profile(PROFILE_GENERIC, False, None),
}


def detect_profile(hass: HomeAssistant, entity_id: str) -> str:
    """Guess the profile of a climate entity from its integration and model."""
    ent = er.async_get(hass).async_get(entity_id)
    if ent is None:
        return PROFILE_GENERIC
    if ent.platform == "shelly":
        return PROFILE_SHELLY_TRV
    model = ""
    if ent.device_id and (dev := dr.async_get(hass).async_get(ent.device_id)):
        model = f"{dev.manufacturer or ''} {dev.model or ''}".lower()
    if "danfoss" in model or "etrv" in model or "ally" in model:
        return PROFILE_DANFOSS_ALLY
    return PROFILE_GENERIC


def resolve_profile(hass: HomeAssistant, entity_id: str, configured: str) -> Profile:
    key = detect_profile(hass, entity_id) if configured in (PROFILE_AUTO, None) else configured
    return PROFILE_DEFS.get(key, PROFILE_DEFS[PROFILE_GENERIC])


def suggest_external_input(hass: HomeAssistant, climate_entity_id: str) -> str | None:
    """Find the TRV's 'external temperature' number entity on the same device."""
    reg = er.async_get(hass)
    ent = reg.async_get(climate_entity_id)
    if ent is None or ent.device_id is None:
        return None
    for cand in er.async_entries_for_device(reg, ent.device_id):
        if cand.domain != "number":
            continue
        text = f"{cand.entity_id} {cand.translation_key or ''} {cand.original_name or ''}".lower().replace(" ", "_")
        if any(h in text for h in _EXTERNAL_HINTS):
            return cand.entity_id
    return None


# Marks a TRV's own "open window detection" switch (Danfoss Ally via ZHA:
# window_open_feature, "Interne Fenstererkennung verwenden"). Add more brands here.
_WINDOW_DETECTION_HINTS = ("window_open_feature", "window_detection", "open_window_detection", "fenstererkennung")


def window_detection_switches(hass: HomeAssistant, climate_entity_id: str) -> list[str]:
    """Switch entities on the TRV's device that turn its own window detection on/off."""
    reg = er.async_get(hass)
    ent = reg.async_get(climate_entity_id)
    if ent is None or ent.device_id is None:
        return []
    found = []
    for cand in er.async_entries_for_device(reg, ent.device_id):
        if cand.domain != "switch" or cand.disabled_by is not None:
            continue
        text = f"{cand.entity_id} {cand.unique_id} {cand.translation_key or ''} {cand.original_name or ''}".lower().replace(" ", "_")
        if any(h in text for h in _WINDOW_DETECTION_HINTS):
            found.append(cand.entity_id)
    return found


def off_command(profile: Profile, state: State | None, off_temperature: float) -> tuple[str, dict]:
    """Service + data that switch this thermostat off."""
    modes = (state.attributes.get(ATTR_HVAC_MODES) or []) if state else []
    if not profile.off_by_setpoint and HVACMode.OFF in modes:
        return SERVICE_SET_HVAC_MODE, {ATTR_HVAC_MODE: HVACMode.OFF}
    min_temp = (state.attributes.get(ATTR_MIN_TEMP) if state else None) or off_temperature
    return SERVICE_SET_TEMPERATURE, {ATTR_TEMPERATURE: max(float(min_temp), off_temperature)}


def heat_commands(profile: Profile, state: State | None, target: float) -> list[tuple[str, dict]]:
    """Services that set a heating setpoint (and leave 'off' first if needed)."""
    calls: list[tuple[str, dict]] = []
    if state is not None and state.state == HVACMode.OFF and not profile.off_by_setpoint:
        calls.append((SERVICE_SET_HVAC_MODE, {ATTR_HVAC_MODE: HVACMode.HEAT}))
    calls.append((SERVICE_SET_TEMPERATURE, {ATTR_TEMPERATURE: target}))
    return calls


def reports_off(profile: Profile, state: State | None, off_temperature: float) -> bool:
    if state is None:
        return False
    if state.state == HVACMode.OFF:
        return True
    current = state.attributes.get(ATTR_TEMPERATURE)
    return current is not None and float(current) <= off_temperature + SETPOINT_TOLERANCE


def reports_setpoint(state: State | None, target: float) -> bool:
    if state is None or state.state == HVACMode.OFF:
        return False
    current = state.attributes.get(ATTR_TEMPERATURE)
    return current is not None and abs(float(current) - target) <= SETPOINT_TOLERANCE


async def async_call(hass: HomeAssistant, entity_id: str, service: str, data: dict) -> None:
    await hass.services.async_call(
        CLIMATE_DOMAIN, service, {ATTR_ENTITY_ID: entity_id, **data}, blocking=True
    )


# ----- device health ---------------------------------------------------------
# What the devices view shows per physical thermostat. Each entry: key ->
# (domain, hints in unique_id / translation_key / entity_id, device class).
_HEALTH_ENTITIES: dict[str, tuple[str, tuple[str, ...], str | None]] = {
    "battery": ("sensor", (), "battery"),
    "rssi": ("sensor", ("-rssi", "_rssi"), None),
    "lqi": ("sensor", ("-lqi", "_lqi"), None),
    "heat_demand": ("sensor", ("pi_heating_demand", "valve_position", "pi_waermebedarf"), None),
    "window_detection": ("switch", _WINDOW_DETECTION_HINTS, None),
    "external_priority": ("switch", ("radiator_covered", "priorisieren"), None),
    "mounting_mode": ("binary_sensor", ("mounting_mode_active",), None),
    "software_error": ("sensor", ("sw_error_code",), None),
    "adaptation": ("sensor", ("adaptation_run_status",), None),
    "firmware": ("update", ("firmware",), None),
}

BATTERY_LOW = 20  # % – same rule as the battery list
STALE_AFTER_H = 3  # no report from the TRV for this long = suspicious
RSSI_WEAK = -85
LQI_WEAK = 60


def _num(value: str | None) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def device_health(hass: HomeAssistant, climate_entity_id: str) -> dict:
    """Reachability, battery, radio and function of one physical thermostat."""
    ereg = er.async_get(hass)
    st = hass.states.get(climate_entity_id)
    out: dict = {
        "entity_id": climate_entity_id,
        "name": (st.attributes.get("friendly_name") if st else None) or climate_entity_id,
        "available": st is not None and st.state not in ("unavailable", "unknown"),
        "setpoint": st.attributes.get(ATTR_TEMPERATURE) if st else None,
        "local_temperature": st.attributes.get("current_temperature") if st else None,
        "hvac_action": st.attributes.get("hvac_action") if st else None,
        "last_seen": None,
        "issues": [],
    }
    ent = ereg.async_get(climate_entity_id)
    siblings = er.async_entries_for_device(ereg, ent.device_id, include_disabled_entities=True) if ent and ent.device_id else []
    if ent and ent.device_id and (dev := dr.async_get(hass).async_get(ent.device_id)):
        out["name"] = dev.name_by_user or dev.name or out["name"]
        out["model"] = " ".join(x for x in (dev.manufacturer, dev.model) if x)
    last = st.last_reported if st else None
    for cand in siblings:
        if cand.disabled_by is None and (cst := hass.states.get(cand.entity_id)) and cst.state not in ("unavailable", "unknown"):
            if last is None or cst.last_reported > last:
                last = cst.last_reported
        text = f"{cand.entity_id} {cand.unique_id} {cand.translation_key or ''}".lower()
        for key, (domain, hints, dclass) in _HEALTH_ENTITIES.items():
            if key in out or cand.domain != domain:
                continue
            if dclass and (cand.device_class or cand.original_device_class) != dclass:
                continue
            if hints and not any(h in text for h in hints):
                continue
            if cand.disabled_by is not None:
                out[key] = {"entity_id": cand.entity_id, "disabled": True}
                continue
            cst = hass.states.get(cand.entity_id)
            value = cst.state if cst else None
            if domain == "sensor" and key in ("battery", "rssi", "lqi", "heat_demand"):
                value = _num(value)
            out[key] = {"entity_id": cand.entity_id, "value": value}
    out["last_seen"] = last.isoformat() if last else None

    issues = out["issues"]
    if not out["available"]:
        issues.append("unavailable")
    battery = (out.get("battery") or {}).get("value")
    if isinstance(battery, float) and battery < BATTERY_LOW:
        issues.append("battery_low")
    if last is not None and (dt_util.utcnow() - last).total_seconds() > STALE_AFTER_H * 3600:
        issues.append("stale")
    rssi = (out.get("rssi") or {}).get("value")
    lqi = (out.get("lqi") or {}).get("value")
    if (isinstance(rssi, float) and rssi < RSSI_WEAK) or (isinstance(lqi, float) and lqi < LQI_WEAK):
        issues.append("weak_signal")
    if (out.get("mounting_mode") or {}).get("value") == "on":
        issues.append("mounting_mode")
    if (out.get("firmware") or {}).get("value") == "on":
        issues.append("firmware_update")
    return out
