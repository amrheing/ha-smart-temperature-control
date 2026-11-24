"""Heat-source interface: how the house mode reaches the boiler / heat pump.

The integration only talks to a heat source through `HeatSource`. Built in:
- `NoHeatSource`: rooms only.
- `EntityHeatSource`: maps each house mode to an option of an existing
  `select` (e.g. the KWB Comfort 4 program select, Viessmann, Vaillant ...)
  or to on/off of a `switch` / `input_boolean`. No code needed.
Other integrations can provide their own class with the same methods.
"""

from __future__ import annotations

import logging

from homeassistant.const import ATTR_ENTITY_ID, ATTR_OPTION, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant

from .const import (
    CONF_HEAT_SOURCE,
    CONF_HEAT_SOURCE_ENTITY,
    CONF_MAP_NORMAL,
    CONF_MAP_PARTY,
    CONF_MAP_SUMMER,
    CONF_MAP_VACATION,
    HEAT_SOURCE_ENTITY,
    HOUSE_NORMAL,
    HOUSE_PARTY,
    HOUSE_VACATION,
    SOURCE_SUMMER,
)

_LOGGER = logging.getLogger(__name__)


class HeatSource:
    """Interface. `mode` is one of normal, party, vacation, summer."""

    name = "none"

    def supported_modes(self) -> set[str]:
        return set()

    async def async_set_mode(self, mode: str) -> bool:
        """Return True when a command was sent."""
        return False

    def status(self) -> dict:
        return {}


class NoHeatSource(HeatSource):
    pass


class EntityHeatSource(HeatSource):
    name = "entity"

    def __init__(self, hass: HomeAssistant, entity_id: str, mapping: dict[str, str]) -> None:
        self.hass = hass
        self.entity_id = entity_id
        self.mapping = {k: v for k, v in mapping.items() if v}

    def supported_modes(self) -> set[str]:
        return set(self.mapping)

    async def async_set_mode(self, mode: str) -> bool:
        wanted = self.mapping.get(mode) or self.mapping.get(HOUSE_NORMAL)
        if not wanted:
            return False
        state = self.hass.states.get(self.entity_id)
        domain = self.entity_id.split(".")[0]
        if domain in ("select", "input_select"):
            if state is not None and state.state == wanted:
                return False
            await self.hass.services.async_call(
                domain, "select_option", {ATTR_ENTITY_ID: self.entity_id, ATTR_OPTION: wanted}, blocking=True
            )
            return True
        if domain in ("switch", "input_boolean"):
            on = wanted.lower() in ("on", "an", "true", "1")
            if state is not None and state.state == ("on" if on else "off"):
                return False
            await self.hass.services.async_call(
                domain, SERVICE_TURN_ON if on else SERVICE_TURN_OFF, {ATTR_ENTITY_ID: self.entity_id}, blocking=True
            )
            return True
        _LOGGER.warning("Heat source %s: unsupported domain %s", self.entity_id, domain)
        return False

    def status(self) -> dict:
        state = self.hass.states.get(self.entity_id)
        return {"entity_id": self.entity_id, "state": state.state if state else None}


def build_heat_source(hass: HomeAssistant, options: dict) -> HeatSource:
    if options.get(CONF_HEAT_SOURCE) == HEAT_SOURCE_ENTITY and options.get(CONF_HEAT_SOURCE_ENTITY):
        return EntityHeatSource(
            hass,
            options[CONF_HEAT_SOURCE_ENTITY],
            {
                HOUSE_NORMAL: options.get(CONF_MAP_NORMAL, ""),
                HOUSE_PARTY: options.get(CONF_MAP_PARTY, ""),
                HOUSE_VACATION: options.get(CONF_MAP_VACATION, ""),
                SOURCE_SUMMER: options.get(CONF_MAP_SUMMER, ""),
            },
        )
    return NoHeatSource()
