# Scenes for the integration

The YAML package carried seven scenes — *Zero Export Power*, *Battery Forced
Charge* and the rest — and they went when the package file went. This page
has them again, written for the integration, plus the two automations two of
them need.

Copy what you want. Nothing here is installed for you: a scene that changes
how your battery behaves should be something you chose, not something an
update added.

## Why the old ones cannot simply be pasted back

They look like they should work. The entity IDs are the same, because the
integration takes over the IDs the package used. But the *values* changed.

The package's dropdowns held their text: `Forced discharge`,
`Self-consumption mode (default)`. The integration's hold a short code —
`discharge`, `self_consumption` — and show you the text, translated into your
language. A scene that asks for text no dropdown offers is skipped, with a
line in the log and nothing on screen.

**And only that entity is skipped.** The rest of the scene still runs. So a
pasted *Self-Consumption Mode (no battery discharge)* would set the discharge
power to 10 W and leave the mode alone, and a pasted *Battery Forced Charge*
would do nothing at all while looking like it worked. That is why these are
rewritten rather than patched.

## Check your entity IDs first

The IDs below are the ones the YAML package used, which is what you have if
you migrated and kept them.

If you installed fresh, or chose the newer IDs during setup, yours carry the
device name — `select.sh10rt_ems_mode` rather than `select.ems_mode`. Open
**Developer tools → States**, type `ems_mode`, and use what you see there.
One substitution, the same everywhere below.

## The scenes

Put these in `scenes.yaml`, or under `scene:` in `configuration.yaml`, and
reload scenes (**Developer tools → YAML → Scenes**).

```yaml
- name: Self-Consumption Mode (max battery discharge)
  entities:
    select.ems_mode: self_consumption
    select.battery_forced_charge_discharge: stop
    # Your battery's maximum, in watts. Developer tools → States shows the
    # highest it accepts, as the number's "max" attribute. Or leave this
    # line out and use the automation below, which reads it from the
    # inverter.
    number.battery_max_discharge_power: 5000

- name: Self-Consumption Mode (no battery discharge)
  entities:
    select.ems_mode: self_consumption
    select.battery_forced_charge_discharge: stop
    # 10 W is the lowest the inverter accepts, and is as close to "stop
    # discharging" as this setting goes.
    number.battery_max_discharge_power: 10

- name: Zero Export Power
  entities:
    switch.export_power_limit: "on"
    number.export_power_limit: 0

- name: Max Export Power
  entities:
    switch.export_power_limit: "on"
    # The automation below sets the limit itself: a scene cannot ask the
    # inverter what its maximum is.

- name: Battery Bypass Mode
  entities:
    select.ems_mode: forced
    select.battery_forced_charge_discharge: stop

- name: Battery Forced Discharge
  entities:
    select.ems_mode: forced
    select.battery_forced_charge_discharge: discharge

- name: Battery Forced Charge
  entities:
    select.ems_mode: forced
    select.battery_forced_charge_discharge: charge
```

## The two automations

A scene stores fixed values, so it cannot ask the inverter what its own
maximum is. These two do that when the matching scene is activated. They are
the same trick the YAML package used, without its secrets file: the limit
comes from the entity itself.

```yaml
- alias: Max export power scene sets the inverter's own limit
  id: sungrow_max_export_scene
  triggers:
    - trigger: state
      entity_id: scene.max_export_power
  actions:
    - action: number.set_value
      target:
        entity_id: number.export_power_limit
      data:
        value: "{{ state_attr('number.export_power_limit', 'max') | float }}"
  mode: single

- alias: Max battery discharge scene sets the battery's own limit
  id: sungrow_max_battery_discharge_scene
  triggers:
    - trigger: state
      entity_id: scene.self_consumption_mode_max_battery_discharge
  actions:
    - action: number.set_value
      target:
        entity_id: number.battery_max_discharge_power
      data:
        value: >
          {{ state_attr('number.battery_max_discharge_power', 'max') | float }}
  mode: single
```

If you used the second automation, drop the
`number.battery_max_discharge_power` line from the first scene — otherwise
the scene sets one value and the automation immediately sets another.

## What the scenes do to your inverter

Worth knowing before you press one.

- **Self-consumption** is the inverter's normal mode: it uses your own
  production first and the battery to cover what is left.
- **Forced mode** hands the battery over to you: it charges, discharges or
  stops because you said so, not because of what the house is using. The
  battery stays that way until something changes it back.
- **Zero export** stops the inverter feeding the grid. If your contract or
  your grid operator requires a specific limit, set that number instead of
  0 — this scene is not a substitute for a configured feed-in limit.
- **Battery bypass** leaves the battery idle while the inverter carries on
  with PV and the grid.

## If you kept the old scenes

Delete them once these work, or you will have two scenes with the same name
and no way to tell which one a dashboard button is pressing. Reinstalling the
YAML package brings the originals back, so there is nothing to preserve.
