# evcc on top of the integration

> **Experimental.** The three battery scripts have been run in Home Assistant's
> test harness, and their settings are the ones [scenes.md](scenes.md) and evcc's own
> Sungrow template use. Nobody has yet watched evcc drive a Sungrow through this
> integration. Start with the meters, then the wallbox, then the battery.

[evcc](https://evcc.io) charges a car from solar surplus, to a target state of
charge, by a plan. This page connects it to your Sungrow **through Home
Assistant**, so evcc opens no Modbus connection of its own: an inverter accepts
very few, and two programs writing to one inverter overrule each other. Do not
also add evcc's own *Sungrow* templates for the same devices.

evcc is open source. Its Home Assistant charger needs no sponsor token.

## Connect evcc to Home Assistant

In evcc, **Configuration → Add additional meter → Home Assistant**. Pick your
instance, or enter its address. Authorise it: Home Assistant opens for you to log
in, and evcc keeps the token. If evcc runs as a Home Assistant app, pick
`http://supervisor/core`; it is already authorised. Do this once before using the
YAML below; the same fields can also be filled in evcc's user interface.

`<device>` is your inverter's name as Home Assistant writes it in ids, such as
`sh10rt`, and `<wallbox>` the wallbox's. Check each id in **Developer tools →
States**: Home Assistant answers a command to an id that does not exist, or to an
unavailable entity, as if it had worked.

With the YAML package's ids taken over, they have no device in front and some
differ ([entity_names.md](entity_names.md) has both): *Total PV input power* is
`sensor.total_dc_power`, and *Battery max discharging power* is
`number.battery_max_discharge_power`.

## The meters

```yaml
meters:
  - name: grid
    type: template
    template: homeassistant
    usage: grid
    uri: http://homeassistant.local:8123
    power: sensor.<device>_meter_active_power          # + is import
    energy: sensor.<device>_total_imported_energy
    returnEnergy: sensor.<device>_total_exported_energy
  - name: pv
    type: template
    template: homeassistant
    usage: pv
    uri: http://homeassistant.local:8123
    power: sensor.<device>_total_pv_input_power
    energy: sensor.<device>_total_pv_generation
  - name: battery
    type: template
    template: homeassistant
    usage: battery
    uri: http://homeassistant.local:8123
    power: sensor.<device>_battery_power                # + is discharging
    soc: sensor.<device>_battery_level
    minSocEntity: number.<device>_battery_min_soc
    maxSocEntity: number.<device>_battery_max_soc
    # add these three once the scripts below exist
    # modeNormal: script.evcc_battery_normal
    # modeHold: script.evcc_battery_hold
    # modeCharge: script.evcc_battery_charge

site:
  title: Home
  meters:
    grid: grid
    pv: [pv]
    battery: [battery]
```

Leave evcc's `interval` at 30 s or more.

## The wallbox

This is for a wallbox the **inverter manages**, whose inverter has *Wallbox
charge*, *Wallbox charge mode* and *Wallbox user-defined current*. A standalone
wallbox is read-only here: see [A wallbox no inverter manages](#a-wallbox-no-inverter-manages).

Before the first charge, once:

1. **Wallbox charge mode: user defined** (`select.<device>_wallbox_charge_mode`). The
   inverter takes a current only in this mode. Choosing it can start a charge.
2. **Start charging on plug-in: off**, in Sungrow's app. With it on, every plug-in starts
   a charge whatever evcc decided.
3. Leave the mode alone after that. Changing it can end a session, and evcc never does.

Make a status evcc understands. The wallbox's own status can read *idle* with a car
plugged in, so this uses the plug instead:

```yaml
template:
  - sensor:
      - name: evcc wallbox status
        unique_id: evcc_wallbox_status
        availability: "{{ has_value('binary_sensor.<wallbox>_car_connected') }}"
        state: >-
          {% if is_state('binary_sensor.<wallbox>_charging', 'on') %}C
          {% elif is_state('binary_sensor.<wallbox>_car_connected', 'on') %}B
          {% else %}A{% endif %}
```

```yaml
chargers:
  - name: wallbox
    type: template
    template: homeassistant
    uri: http://homeassistant.local:8123
    status: sensor.evcc_wallbox_status
    enabled: switch.<device>_wallbox_charge
    enable: switch.<device>_wallbox_charge
    setMaxCurrent: number.<device>_wallbox_user_defined_current   # 6 A and up
    timeout: 30s
    power: sensor.<wallbox>_charging_power
    energy: sensor.<wallbox>_total_charged_energy
    currentL1: sensor.<wallbox>_phase_a_charging_current
    currentL2: sensor.<wallbox>_phase_b_charging_current
    currentL3: sensor.<wallbox>_phase_c_charging_current
    voltageL1: sensor.<wallbox>_phase_a_voltage
    voltageL2: sensor.<wallbox>_phase_b_voltage
    voltageL3: sensor.<wallbox>_phase_c_voltage

loadpoints:
  - title: Wallbox
    charger: wallbox
    vehicle: car
```

In the charging point's settings, choose three phases, and 6 A as the minimum: 4.14 kW
is the least a charge takes. Do not add `phaseswitch`; the inverter chooses the phases.

In the current evcc, the mode that charges from surplus is called `smart`.

### A wallbox no inverter manages

A wallbox that is not set up as an inverter's EV charger in iSolarCloud is driven at the
wallbox itself, and Home Assistant only reads it. Use **evcc's own Sungrow charger**
(AC011E-01, AC22E-01) for it instead of the charger above. It sets the current, starts and
stops, and switches between one and three phases, pausing the charge for the switch; set the
charging point's phases to automatic for evcc to choose them:

```yaml
chargers:
  - name: wallbox
    type: template
    template: sungrow
    modbus: rs485
    device: /dev/ttyUSB0
    baudrate: 9600
    comset: 8N1
    id: 248
```

evcc cannot speak TLS, so it does not reach the wallbox at the LAN port the integration
uses (516); wire it to the wallbox's RS485, or to a Modbus TCP gateway on it
(`host: <gateway>` and `port: 502` in place of `device`). The serial settings above are evcc's defaults: check
them against your wallbox's. Home Assistant's wallbox entry can stay and keep reading it.
Leave that entry's capability test off while evcc drives the wallbox, or stop evcc for the
test: both write the same registers.

This setup is reported working by an owner and not watched here.

## The car and the forecast

Let Home Assistant hold the car's account and the solar forecast. One program
asking the maker's cloud or a forecast service is enough, and more meets its limits.

```yaml
vehicles:
  - name: car
    type: template
    template: homeassistant
    uri: http://homeassistant.local:8123
    soc: sensor.<car>_state_of_charge
    capacity: 60            # kWh
    autodetectdisabled: true

tariffs:
  solar:
    - type: template
      template: homeassistant
      uri: http://homeassistant.local:8123
```

The forecast is the one chosen in Home Assistant's
[Energy dashboard](energy_dashboard.md). Without a state of charge, evcc plans the
current session in kWh.

## The battery

evcc can keep the battery from discharging into the car (*hold*) and charge it
from the grid (*charge*). Each mode is a Home Assistant script. evcc starts a script
and does not learn how it ended, and it does not repeat a mode it believes is set. So
these check what the inverter reads, try three times, and leave a notification when the
mode did not take.

Put your own values in: the four entity ids, `charge_power`, and **5000, twice: your own
maximum discharge power**. *Normal* and *charge* write that limit and *hold* lowers it
to 10 W, the lowest the inverter takes, so whatever limit you set by hand is replaced.

```yaml
script:
  sungrow_battery_mode:
    alias: Sungrow battery mode (called by the three below)
    mode: restart
    variables:
      ems_entity: select.<device>_ems_mode
      command_entity: select.<device>_battery_forced_charge_discharge
      power_entity: number.<device>_battery_forced_charge_discharge_power
      discharge_entity: number.<device>_battery_max_discharging_power
      charge_power: 2000        # W, how hard "charge" charges from the grid
    sequence:
      - repeat:
          while: >-
            {{ repeat.index <= 3 and not (
               is_state(ems_entity, ems) and is_state(command_entity, command)
               and states(discharge_entity) | float(-1) == discharge | float
               and (command != 'charge' or states(power_entity) | float(-1) == charge_power)) }}
          sequence:
            - if: "{{ command == 'charge' }}"
              then:
                - action: number.set_value
                  continue_on_error: true
                  target: {entity_id: "{{ power_entity }}"}
                  data: {value: "{{ charge_power }}"}
            - action: number.set_value
              continue_on_error: true
              target: {entity_id: "{{ discharge_entity }}"}
              data: {value: "{{ discharge }}"}
            - action: select.select_option
              continue_on_error: true
              target: {entity_id: "{{ command_entity }}"}
              data: {option: "{{ command }}"}
            - action: select.select_option
              continue_on_error: true
              target: {entity_id: "{{ ems_entity }}"}
              data: {option: "{{ ems }}"}
            - wait_template: >-
                {{ is_state(ems_entity, ems) and is_state(command_entity, command)
                   and states(discharge_entity) | float(-1) == discharge | float
                   and (command != 'charge' or states(power_entity) | float(-1) == charge_power) }}
              timeout: "00:00:20"
      - if: >-
          {{ is_state(ems_entity, ems) and is_state(command_entity, command)
             and states(discharge_entity) | float(-1) == discharge | float
             and (command != 'charge' or states(power_entity) | float(-1) == charge_power) }}
        then:
          - action: persistent_notification.dismiss
            data: {notification_id: sungrow_battery_mode}
        else:
          - action: persistent_notification.create
            data:
              notification_id: sungrow_battery_mode
              title: Battery mode not set
              message: >-
                evcc asked for {{ ems }} / {{ command }} / {{ discharge }} W.
                The inverter reads {{ states(ems_entity) }} /
                {{ states(command_entity) }} / {{ states(discharge_entity) }} W.

  evcc_battery_normal:
    alias: evcc battery normal
    mode: restart
    sequence:
      - action: script.sungrow_battery_mode
        data: {ems: self_consumption, command: stop, discharge: 5000}

  evcc_battery_hold:
    alias: evcc battery hold
    mode: restart
    sequence:
      - action: script.sungrow_battery_mode
        data: {ems: self_consumption, command: stop, discharge: 10}

  evcc_battery_charge:
    alias: evcc battery charge
    mode: restart
    sequence:
      - action: script.sungrow_battery_mode
        data: {ems: forced, command: charge, discharge: 5000}
```

In *hold*, the battery can still charge from the sun. *Charge* takes from the grid at
`charge_power`. evcc overwrites what you, a scene or another automation set, so use one of
them to steer the battery. A [capability test](capability_tests.md) running at the time refuses these writes;
the notification says so.

`evcc meter verifybatterymodes` steps through the modes and watches the battery. Run
it with somebody watching, in daylight and with the battery neither full nor empty.

### If evcc stops

**A battery mode stays set when evcc stops.** This returns it to normal after five
minutes without an answer from evcc, and after a Home Assistant restart if evcc has
not come back. It does not notice an evcc that answers but is stuck.

```yaml
binary_sensor:
  - platform: rest
    name: evcc alive
    unique_id: evcc_alive
    resource: http://<evcc>:7070/api/state
    value_template: "{{ 'loadpoints' in value }}"
    scan_interval: 30

automation:
  - id: evcc_gone_battery_normal
    alias: Battery back to normal when evcc is gone
    triggers:
      - trigger: state
        entity_id: binary_sensor.evcc_alive
        to: ["off", "unavailable", "unknown"]
        for: "00:05:00"
      - trigger: homeassistant
        event: start
        id: started
    actions:
      - if:
          - condition: trigger
            id: started
        then:
          - delay: "00:05:00"
          - condition: not
            conditions:
              - condition: state
                entity_id: binary_sensor.evcc_alive
                state: "on"
      - action: script.evcc_battery_normal
```

It is for a house where evcc alone steers the battery: it also ends a forced charge you
set by hand while evcc is off. The wallbox is left as it was.

## If something does not work

- **A mode was not set**: read the notification, then the log. A dongle in a busy house
  can drop writes or read back an old value.
- **evcc reports a timeout for a command that worked**: raise `timeout`.
- **A value is missing in evcc**: the entity is `unavailable` or `unknown` in Home
  Assistant, or the id is wrong.
