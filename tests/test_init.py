"""Room controller end to end with fake thermostats."""

from __future__ import annotations

from datetime import datetime, timedelta

from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.smart_temperature_control.const import (
    CONF_HEAT_SOURCE,
    CONF_HEAT_SOURCE_ENTITY,
    CONF_MAP_NORMAL,
    CONF_MAP_SUMMER,
    CONF_MAP_VACATION,
    DOMAIN,
    HEAT_SOURCE_ENTITY,
)
from custom_components.smart_temperature_control.config_flow import DEFAULT_OPTIONS

ROOM = {
    "name": "Schlafzimmer",
    "thermostats": ["climate.sz_1", "climate.sz_2"],
    "external_inputs": ["number.sz_1_external"],
    "sensors": ["sensor.sz_multi", "sensor.sz_ep1"],
    "windows": ["binary_sensor.sz_window"],
    "window_delay": 60,
    "profile": "danfoss_ally",
}


def _trv(hass, entity_id, setpoint, current=19.0):
    hass.states.async_set(
        entity_id,
        "heat",
        {"temperature": setpoint, "current_temperature": current, "hvac_modes": ["heat"], "min_temp": 5},
    )


@pytest.fixture
async def setup(hass: HomeAssistant, freezer: FrozenDateTimeFactory):
    tz = dt_util.get_default_time_zone()
    freezer.move_to(datetime(2026, 11, 24, 18, 30, tzinfo=tz))  # Tuesday
    _trv(hass, "climate.sz_1", 17)
    _trv(hass, "climate.sz_2", 17)
    hass.states.async_set("sensor.sz_multi", "19.2", {"unit_of_measurement": "°C"})
    hass.states.async_set("sensor.sz_ep1", "19.6", {"unit_of_measurement": "°C"})
    hass.states.async_set("binary_sensor.sz_window", "off")
    hass.states.async_set("number.sz_1_external", "19")
    hass.states.async_set("select.kwb_program", "Heizbetrieb", {"options": ["Heizbetrieb", "Absenkbetrieb", "Sommer"]})
    options = {
        **DEFAULT_OPTIONS,
        CONF_HEAT_SOURCE: HEAT_SOURCE_ENTITY,
        CONF_HEAT_SOURCE_ENTITY: "select.kwb_program",
        CONF_MAP_NORMAL: "Heizbetrieb",
        CONF_MAP_VACATION: "Absenkbetrieb",
        CONF_MAP_SUMMER: "Sommer",
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Heizung Haus",
        unique_id=DOMAIN,
        options=options,
        subentries_data=[ConfigSubentryData(data=ROOM, subentry_type="room", title="Schlafzimmer", unique_id=None)],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # mock after setup: our platforms load the real climate/number/select components
    calls = {
        "temp": async_mock_service(hass, "climate", "set_temperature"),
        "mode": async_mock_service(hass, "climate", "set_hvac_mode"),
        "number": async_mock_service(hass, "number", "set_value"),
        "select": async_mock_service(hass, "select", "select_option"),
    }
    return entry, calls, freezer


def _room(entry):
    return next(iter(entry.runtime_data.rooms.values()))


async def test_read_mode_computes_but_does_not_write(hass, setup):
    entry, calls, _ = setup
    room = _room(entry)
    assert room.decision.target == 20.0
    assert room.decision.reason == "comfort"
    assert room.temperature.value == 19.4
    assert room.planned == ["climate.sz_1", "climate.sz_2"]
    assert calls["temp"] == []
    st = hass.states.get("climate.heizung")
    assert st is not None
    assert st.attributes["temperature"] == 20.0
    assert st.attributes["current_temperature"] == 19.4
    assert st.attributes["reason"] == "comfort"


async def test_control_writes_both_trvs_same_setpoint(hass, setup):
    entry, calls, _ = setup
    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.heizung_control_thermostats"}, blocking=True)
    await hass.async_block_till_done()
    sent = sorted((c.data["entity_id"], c.data["temperature"]) for c in calls["temp"])
    assert sent == [("climate.sz_1", 20.0), ("climate.sz_2", 20.0)]


async def test_window_and_heating_off_rest(hass, setup):
    entry, calls, freezer = setup
    room = _room(entry)
    room.update(control=True)
    await hass.async_block_till_done()
    _trv(hass, "climate.sz_1", 20)
    _trv(hass, "climate.sz_2", 20)
    calls["temp"].clear()
    hass.states.async_set("binary_sensor.sz_window", "on")
    freezer.tick(timedelta(seconds=90))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert room.decision.reason == "window"
    assert {c.data["temperature"] for c in calls["temp"]} == {5.0}

    # heating off: off once, then the thermostats are left alone
    hass.states.async_set("binary_sensor.sz_window", "off")
    room.update(on=False)
    await hass.async_block_till_done()
    _trv(hass, "climate.sz_1", 5)
    _trv(hass, "climate.sz_2", 5)
    calls["temp"].clear()
    calls["number"].clear()
    for _ in range(3):
        freezer.tick(timedelta(minutes=11))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
    assert room.decision.resting
    assert calls["temp"] == []
    assert calls["number"] == []  # no external sensor feed while resting


async def test_external_feed(hass, setup):
    entry, calls, freezer = setup
    _room(entry).update(control=True)
    freezer.tick(timedelta(minutes=11))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert calls["number"][-1].data == {"entity_id": "number.sz_1_external", "value": 19.4}


async def test_manual_change_holds_until_next_switch_and_can_be_saved(hass, setup):
    entry, calls, _ = setup
    room = _room(entry)
    room.update(control=True)
    await hass.async_block_till_done()
    _trv(hass, "climate.sz_1", 20)
    await hass.async_block_till_done()
    _trv(hass, "climate.sz_1", 22)  # someone turned the knob
    await hass.async_block_till_done()
    assert room.decision.reason == "manual"
    assert room.decision.target == 22.0
    assert room.decision.until.hour == 22  # next schedule switch
    assert hass.states.get("binary_sensor.heizung_manually_changed").state == "on"
    await hass.services.async_call("button", "press", {"entity_id": "button.heizung_save_for_this_period"}, blocking=True)
    await hass.async_block_till_done()
    assert room.stored["comfort"] == 22.0
    assert room.override is None


async def test_house_mode_drives_rooms_and_heat_source(hass, setup):
    entry, calls, _ = setup
    house = entry.runtime_data
    room = _room(entry)
    house.set_house(control_heat_source=True)
    await hass.async_block_till_done()
    # select.select_option is mocked in this fixture, so drive the house directly
    house.set_house(mode="vacation")
    await hass.async_block_till_done()
    assert room.decision.reason == "vacation"
    assert any(c.data.get("option") == "Absenkbetrieb" for c in calls["select"])
    house.set_house(summer=True)
    await hass.async_block_till_done()
    assert room.decision.reason == "summer"
    assert calls["select"][-1].data["option"] == "Sommer"


async def test_schedule_service(hass, setup):
    entry, _, _ = setup
    days = ["e" * 48] * 7
    await hass.services.async_call(DOMAIN, "set_schedule", {"entity_id": "climate.heizung", "days": days}, blocking=True)
    await hass.async_block_till_done()
    room = _room(entry)
    assert room.decision.reason == "eco"
    assert room.decision.target == 17.0


async def test_trv_window_detection_switched_off_with_own_contacts(hass, setup):
    from homeassistant.helpers import device_registry as dr, entity_registry as er

    entry, calls, _ = setup
    zha = MockConfigEntry(domain="zha")
    zha.add_to_hass(hass)
    dev = dr.async_get(hass).async_get_or_create(config_entry_id=zha.entry_id, identifiers={("zha", "sz1")})
    reg = er.async_get(hass)
    hass.states.async_remove("climate.sz_1")  # registry avoids ids that have a state
    reg.async_get_or_create("climate", "zha", "sz1-1-513", device_id=dev.id, suggested_object_id="sz_1")
    _trv(hass, "climate.sz_1", 17)
    reg.async_get_or_create("switch", "zha", "sz1-1-513-window_open_feature", device_id=dev.id, suggested_object_id="sz_1_window")
    reg.async_get_or_create("switch", "zha", "sz1-1-513-external_open_window_detected", device_id=dev.id, suggested_object_id="sz_1_ext_window")
    hass.states.async_set("switch.sz_1_window", "on")
    hass.states.async_set("switch.sz_1_ext_window", "off")
    off = async_mock_service(hass, "switch", "turn_off")
    room = _room(entry)
    await room.async_refresh()
    assert off == []  # read mode: nothing written
    room.stored["control"] = True
    await room.async_refresh()
    assert [c.data["entity_id"] for c in off] == ["switch.sz_1_window"]
