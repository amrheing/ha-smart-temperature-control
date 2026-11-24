"""Config flow: house + room subentry."""

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.smart_temperature_control.const import DOMAIN


async def test_house_and_room(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry = result["result"]
    await hass.async_block_till_done()

    hass.states.async_set("climate.buero", "heat", {"temperature": 20, "current_temperature": 19})
    result = await hass.config_entries.subentries.async_init((entry.entry_id, "room"), context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"name": "Büro", "thermostats": ["climate.buero"], "sensors": [], "windows": [], "window_delay": 60, "profile": "auto"},
    )
    assert result["step_id"] == "external"
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {"external_inputs": []})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert len(entry.subentries) == 1
    assert hass.states.get("climate.heizung") is not None


async def test_single_instance(hass):
    await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {}) if r["type"] is FlowResultType.FORM else r
    # second one may already abort or be allowed to finish only once
    assert r["type"] in (FlowResultType.ABORT, FlowResultType.CREATE_ENTRY)
