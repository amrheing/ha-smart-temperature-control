# Smart Temperatur Control

Home Assistant integration for room-by-room heating: week schedule per room (Komfort/Eco), window detection, manual changes that hold until the next switch point, one house mode (Normal / Party / Urlaub) plus a summer switch, and an optional heat source (e.g. a pellet boiler) that follows the house mode.

Version 0.1 starts in **read mode**: every room computes its setpoint and shows it, but writes nothing to the thermostats until you turn on the room switch "Thermostate steuern".

## Installation

HACS → Custom repositories → `https://github.com/amrheing/ha-smart-temperature-control` (type Integration), install, restart Home Assistant.
Manual: copy `custom_components/smart_temperature_control` into your `config/custom_components/`.

Then *Settings → Devices & services → Add integration → Smart Temperatur Control*. This creates the entry **Heizung Haus**.

## Setup

### House (options of "Heizung Haus")

| Option | Default | Meaning |
|---|---|---|
| Off temperature | 5 °C | Setpoint used when a thermostat has no real "off" |
| External sensor interval | 10 min | How often the room temperature is sent to the thermostats' external input |
| Verify after | 30 min | Check that the thermostat reports the sent setpoint |
| Retries | 3 | Resend attempts before the room shows a problem |
| Sensor min / max | 0 / 40 °C | Readings outside are ignored |
| Max jump | 3 K in 5 min | Bigger jumps are ignored |
| Stale after | 60 min | A sensor without a new value is ignored |
| Notify service | – | e.g. `notify.mobile_app_iphone`, gets problem messages |
| Heat source | none | `entity`: control a select / switch from the house mode |

**Heat source mapping** (step after choosing `entity`): pick a `select`, `input_select`, `switch` or `input_boolean` and the option for each state. Example for the KWB Comfort 4 integration:

| House state | Option |
|---|---|
| Normal | `Heizbetrieb` |
| Party | `Heizbetrieb` |
| Urlaub | `Absenkbetrieb` |
| Sommer | `Sommer` |

Nothing is sent to the heat source until the house switch "Wärmeerzeuger steuern" is on.

### Rooms (add with "+ Raum" on the entry)

Name, area, one or more thermostats (all get the same setpoint), optional temperature sensors (averaged, implausible ones ignored, fallback is the thermostats' own sensor), window contacts with delay, and the thermostat profile. In the second step you can pick number entities that take an external room temperature; matching ones on the same device are suggested.

### Thermostat profiles

| Profile | Off | Notes |
|---|---|---|
| Auto | – | Detected from the device (Danfoss Ally, Shelly), else generic |
| Danfoss Ally | setpoint = off temperature (5 °C) | Ally has no off mode |
| Shelly TRV | `hvac_mode: off` (Gen1) or setpoint = off temperature (BLU TRV) | External temperature via the device's number entity |
| Generic | `hvac_mode: off` if offered, else minimum temperature | |

When a room has window contacts and "Thermostate steuern" is on, the thermostats' own open-window detection is switched off (Danfoss Ally: "Interne Fenstererkennung verwenden"), so only the configured contacts decide.

## Entities

House: `select` Betriebsart (Normal/Party/Urlaub), `switch` Sommerbetrieb and Wärmeerzeuger steuern, `time` Party bis, `datetime` Urlaub ab/bis, `sensor` rooms heating (attributes list eco, manual and problem rooms).

Per room: `climate` (presets plan/comfort/eco; changing the temperature is a manual change), `switch` Heizung / Zeitplan / Thermostate steuern, `number` Komfort / Eco, `sensor` room temperature (virtual) and setpoint (with reason), `binary_sensor` Eco period / window / problem / manually changed, `button` back to plan / save for this period / send now.

### Priority

Sommer → room off → Urlaub → window open → Party → manual change (until next switch point) → schedule off (permanent Komfort) → week schedule.
In Sommer, Urlaub and with the room switched off the thermostats are set off **once** and then left alone (no external sensor feed, no checks) to save batteries.

## Week schedule card

The card is registered automatically. Add it to a dashboard:

```yaml
type: custom:stc-week-card
entity: climate.schlafzimmer_heizung
```

Tap a cell to switch Komfort ↔ Eco. Several taps are collected and saved with one call of `smart_temperature_control.set_schedule` (7 strings of `k`/`e`, 48 slots of 30 min by default).

## Rooms card

```yaml
type: custom:stc-rooms-card
# entities: [climate.schlafzimmer_heizung, climate.buro_heizung]  # optional, default: all rooms
```

One box per room (room temperature, setpoint, reason). Tapping a box opens the room controller directly below it: setpoint ± (holds until the next switch point), Heizung/Zeitplan/Thermostate steuern, week plan, Komfort/Eco, sensors and thermostats. A manual change shows a box with "Für diese Periode speichern" and "Zurück zum Plan".

## Room table and thermostats

```yaml
type: custom:stc-table-card     # all rooms as a table: Ist, Soll, Grund, Heizung, Zeitplan, Steuern, Komfort, Eco
---
type: custom:stc-devices-card   # every physical thermostat
```

The thermostats card shows per TRV: reachable / offline, last report, battery, radio (RSSI/LQI, if those entities are enabled), TRV setpoint vs. room setpoint, the TRV's own temperature, valve demand, its own window detection and external sensor priority, plus hints (battery below 20 %, no report for 3 h, weak signal, mounting mode, firmware update, setpoint differs). The data is the `devices` attribute of each room's climate entity (not recorded in history).

## Pilot

Start with two rooms (Schlafzimmer, Büro) in read mode, compare the "Setpoint" sensor with the existing automations, then turn on "Thermostate steuern" per room and disable the old automations for that room.

## Development

```bash
pip install -r requirements_test.txt
pytest
```

## License

MIT
