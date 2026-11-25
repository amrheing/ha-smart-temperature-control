"""Options flow of the house entry opens and saves."""

import voluptuous_serialize
from homeassistant.helpers import config_validation as cv
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smart_temperature_control.const import DOMAIN


async def test_options_flow_opens_and_saves(hass, enable_custom_integrations):
    entry = MockConfigEntry(domain=DOMAIN, title="Heizung Haus", data={}, options={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"
    voluptuous_serialize.convert(result["data_schema"], custom_serializer=cv.custom_serializer)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"off_temperature": 5, "external_interval": 10, "verify_delay": 30, "retries": 3, "sensor_min": 0,
         "sensor_max": 40, "sensor_max_jump": 3, "sensor_stale": 60, "heat_source": "none"},
    )
    assert result["type"] == "create_entry"
    assert entry.options["retries"] == 3
