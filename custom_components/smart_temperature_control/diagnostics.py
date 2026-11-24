"""Diagnostics download."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import StcConfigEntry


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: StcConfigEntry) -> dict[str, Any]:
    house = entry.runtime_data
    return {
        "options": dict(entry.options),
        "house": house.h,
        "rooms": {
            r.name: {
                "config": dict(entry.subentries[r.id].data),
                "stored": r.stored,
                "decision": {"target": r.decision.target, "reason": r.decision.reason},
                **r.attributes(),
            }
            for r in house.rooms.values()
        },
    }
