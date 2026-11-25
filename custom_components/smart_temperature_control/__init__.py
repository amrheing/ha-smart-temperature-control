"""Smart Temperatur Control: room heating logic as one integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import CoreState, Event, HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CARD_URL, DOMAIN
from .controller import House

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.DATETIME,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
]

type StcConfigEntry = ConfigEntry[House]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    await _async_register_card(hass)
    return True


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the week-schedule Lovelace card (custom:stc-week-card)."""
    if getattr(hass, "http", None) is None:
        return
    try:
        from homeassistant.components.frontend import add_extra_js_url
        from homeassistant.components.http import StaticPathConfig

        path = Path(__file__).parent / "frontend" / "stc-week-card.js"
        await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, str(path), False)])
        # version in the URL so browsers load the new card after an update
        from homeassistant.loader import async_get_integration

        version = (await async_get_integration(hass, DOMAIN)).version
        add_extra_js_url(hass, f"{CARD_URL}?v={version}")
    except Exception as err:  # noqa: BLE001 - the card is optional
        _LOGGER.debug("Week card not registered: %s", err)


async def async_setup_entry(hass: HomeAssistant, entry: StcConfigEntry) -> bool:
    house = House(hass, entry)
    await house.async_load()
    entry.runtime_data = house
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    house.async_start()

    async def _first_refresh(_event: Event | None = None) -> None:
        await house.async_refresh_all()

    if hass.state is CoreState.running:
        await _first_refresh()
    else:
        entry.async_on_unload(
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _first_refresh)
        )
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: StcConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: StcConfigEntry) -> bool:
    entry.runtime_data.async_stop()
    await entry.runtime_data.store.async_save(entry.runtime_data.data)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
