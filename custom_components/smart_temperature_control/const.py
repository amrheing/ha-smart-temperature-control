"""Constants for Smart Temperatur Control."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "smart_temperature_control"

SUBENTRY_ROOM: Final = "room"

# Room configuration (subentry data)
CONF_NAME: Final = "name"
CONF_AREA: Final = "area"
CONF_THERMOSTATS: Final = "thermostats"
CONF_EXTERNAL_INPUTS: Final = "external_inputs"
CONF_SENSORS: Final = "sensors"
CONF_WINDOWS: Final = "windows"
CONF_WINDOW_DELAY: Final = "window_delay"
CONF_PROFILE: Final = "profile"

PROFILE_AUTO: Final = "auto"
PROFILE_DANFOSS_ALLY: Final = "danfoss_ally"
PROFILE_SHELLY_TRV: Final = "shelly_trv"
PROFILE_GENERIC: Final = "generic"
PROFILES: Final = [PROFILE_AUTO, PROFILE_DANFOSS_ALLY, PROFILE_SHELLY_TRV, PROFILE_GENERIC]

# House options (main entry options)
CONF_OFF_TEMPERATURE: Final = "off_temperature"
CONF_EXT_INTERVAL: Final = "external_interval"
CONF_VERIFY_DELAY: Final = "verify_delay"
CONF_RETRIES: Final = "retries"
CONF_NOTIFY: Final = "notify_service"
CONF_HEAT_SOURCE: Final = "heat_source"
CONF_HEAT_SOURCE_ENTITY: Final = "heat_source_entity"
CONF_MAP_NORMAL: Final = "map_normal"
CONF_MAP_PARTY: Final = "map_party"
CONF_MAP_VACATION: Final = "map_vacation"
CONF_MAP_SUMMER: Final = "map_summer"
CONF_SENSOR_MIN: Final = "sensor_min"
CONF_SENSOR_MAX: Final = "sensor_max"
CONF_SENSOR_MAX_JUMP: Final = "sensor_max_jump"
CONF_SENSOR_STALE: Final = "sensor_stale"

HEAT_SOURCE_NONE: Final = "none"
HEAT_SOURCE_ENTITY: Final = "entity"

DEFAULT_OFF_TEMPERATURE: Final = 5.0
DEFAULT_EXT_INTERVAL: Final = 10  # minutes; Danfoss needs a value at least every 30 min
DEFAULT_VERIFY_DELAY: Final = 30  # minutes
DEFAULT_RETRIES: Final = 3
DEFAULT_WINDOW_DELAY: Final = 60  # seconds
DEFAULT_COMFORT: Final = 20.0
DEFAULT_ECO: Final = 17.0
DEFAULT_SENSOR_MIN: Final = 0.0
DEFAULT_SENSOR_MAX: Final = 40.0
DEFAULT_SENSOR_MAX_JUMP: Final = 3.0  # Kelvin within JUMP_WINDOW
DEFAULT_SENSOR_STALE: Final = 60  # minutes
JUMP_WINDOW_MINUTES: Final = 5

SETPOINT_TOLERANCE: Final = 0.3
MIN_SETPOINT: Final = 5.0
MAX_SETPOINT: Final = 30.0

# House modes (one input object for rooms AND heat source)
HOUSE_NORMAL: Final = "normal"
HOUSE_PARTY: Final = "party"
HOUSE_VACATION: Final = "vacation"
HOUSE_MODES: Final = [HOUSE_NORMAL, HOUSE_PARTY, HOUSE_VACATION]
# Summer is a separate switch; heat-source mode "summer" wins over everything.
SOURCE_SUMMER: Final = "summer"

# Why a room has its target (sensor attribute "reason")
REASON_SUMMER: Final = "summer"
REASON_OFF: Final = "off"
REASON_VACATION: Final = "vacation"
REASON_WINDOW: Final = "window"
REASON_PARTY: Final = "party"
REASON_MANUAL: Final = "manual"
REASON_PERMANENT_COMFORT: Final = "permanent_comfort"
REASON_ECO: Final = "eco"
REASON_COMFORT: Final = "comfort"
RESTING_REASONS: Final = {REASON_SUMMER, REASON_OFF, REASON_VACATION}

SIGNAL_ROOM_UPDATED: Final = f"{DOMAIN}_room_updated_{{}}"
SIGNAL_HOUSE_UPDATED: Final = f"{DOMAIN}_house_updated_{{}}"

CARD_URL: Final = f"/{DOMAIN}/week-card.js"
