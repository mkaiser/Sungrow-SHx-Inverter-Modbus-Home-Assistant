# Using the integration

What people use it for, what it can be asked to do from an automation or
script, what it cannot do on your hardware, and what to try when something
does not work.
[integration_options.md](integration_options.md) lists the settings.

## What people use it for

- **Replacing the YAML package** without losing years of history: the
  entities can take over the package's entity ids, statistics and
  dashboards included ([integration_migration.md](integration_migration.md)).
- **Watching the house**: generation, consumption, import and export, the
  battery's charge and the wallbox's sessions, for the Energy dashboard and
  for automations.
- **Steering the battery and the export**: the charge limits, the export
  power limit and the forced-charging schedule are entities an automation
  can set, for example to charge from the grid at a cheap tariff or to cap
  export where the grid operator requires it.
- **Stopping at a negative price**: the actions below.
- **Telling the project what your installation can do**: the survey reads
  it and writes a document, so support for your model is measured rather
  than guessed.

## Actions

Under **Developer tools → Actions**, or in an automation. Each takes the
Sungrow device to act on.

| Action | What it does |
| --- | --- |
| `sungrow_modbus.start_inverter` | Boots an inverter that has been shut down |
| `sungrow_modbus.stop_inverter` | Shuts it down: no generation, no charging, no discharging, until started again |
| `sungrow_modbus.run_survey` | Reads the installation and produces the survey document; writes nothing. Same as the **Run read only diagnosis** button |
| `sungrow_modbus.run_control_test` | Writes each control, checks it and puts it back. **Changes settings while it runs**; same as **Run complete diagnosis and tests**. Read [what it does](../device-survey/README.md#it-reads-and-writes-only-if-you-say-yes) first |

Start and stop are actions rather than buttons on purpose: a button has no
confirmation dialog. Who may call them, and who may run the control test, is
under **Configure → Permissions**; both default to administrators.

An action that cannot be carried out says why: the device is not loaded, a
survey is already running, or the inverter did not take the write.

An automation that stops the inverter when the price of export goes negative,
and starts it again when it recovers:

```yaml
automation:
  - alias: Stop the inverter at a negative export price
    triggers:
      - trigger: numeric_state
        entity_id: sensor.export_price
        below: 0
    actions:
      - action: sungrow_modbus.stop_inverter
        data:
          device_id: YOUR_INVERTER_DEVICE_ID
  - alias: Start it again
    triggers:
      - trigger: numeric_state
        entity_id: sensor.export_price
        above: 0
    actions:
      - action: sungrow_modbus.start_inverter
        data:
          device_id: YOUR_INVERTER_DEVICE_ID
```

`sensor.export_price` stands for whatever price sensor you have.

## Known limitations

- **Few connections.** A Sungrow accepts very few Modbus sessions at once and
  needs about 90 seconds of quiet to recover from too many. The integration
  shares one connection between everything it reads and writes; a second
  client is what breaks it.
- **Through a WiNet-S dongle**, some registers are not forwarded:
  - the daily, monthly and yearly history registers (6100 and up), which
    Sungrow documents as cable-only;
  - the inverter's sub-controller and battery firmware versions;
  - an SBR battery's cell and module details.

  A dongle also answers *0* for hardware the inverter does not have, and
  reads back a written setting from a stale cache, so the control test
  through a dongle can only judge what the inverter visibly does.
- **WiFi or Ethernet** on a dongle cannot be told apart over Modbus; the
  survey asks you.
- **Not supported yet:** the iHomeManager, the Sungrow Logger, SBH batteries,
  an SBR's per-module entities, and writing to the wallbox.
- **The preview sets up diagnostics only**: it identifies the inverter and
  runs the survey, and creates no sensors for the readings.

[compatibility.md](compatibility.md) lists every surveyed model and firmware.

## Troubleshooting

**"Could not reach" when adding it, or entities going unavailable.**
Something else is polling the inverter: the YAML package, a second Home
Assistant, EVCC, a logger. Stop it, wait two minutes, and reload the
integration. The log names the register group that stopped answering, and
says so again when it answers.

**Some entities unavailable, the rest fine.** Each register group is judged
on its own: a dongle that refuses one group takes only that group's
entities with it. If they never come back, it is likely one of the
[limitations](#known-limitations) above.

**"The YAML package is still running"** when taking over its entity ids.
Remove `modbus_sungrow.yaml` from your configuration, restart, and try again;
its entities hold the ids while it runs.
[integration_migration.md](integration_migration.md) has the whole move.

**A battery or wallbox that is gone** stays as a device, because one that
misses a single start-up usually answers at the next. Delete it from its
device page once you know it is gone; the integration refuses while it still
answers.

**Wrong address after a router change.** **Reconfigure** on the entry.

**Anything else:** open an
[issue](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues)
with **Download diagnostics** from the device page attached (serial and
address removed) and the version HACS shows.
