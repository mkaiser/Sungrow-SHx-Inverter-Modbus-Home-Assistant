# gerd's own Home Assistant, 2026-11-21: the integration goes in, behind a modbus proxy

Raw note. The first time the integration (0.1.0a46, from the preview channel) was set up on a production
Home Assistant that had once run the YAML package. Reached through the maintainer's host (its tunnel; none
in the devcontainer). Times are CET. No address, serial or lifetime figure is in this note; the owner's
own sensors are named by kind only.

## The instance before

- Home Assistant 2026.11.1, the preview channel installed through the Marketplace at the previous preview
  (a45), **no** `sungrow_modbus` entry. The recorder is MariaDB, with InfluxDB beside it.
- The YAML package was gone, and the entities it had made were 104 registry entries of the `modbus`
  platform, all unavailable and flagged `restored`: placeholders, not live states. Their statistics
  had stopped 12.6 days before the integration's first start.
- A modbus-proxy add-on (1.1.0) in front of both paths: the inverter's own LAN port on host port 502, the
  WiNet-S on 503. Its configuration read `devices:` for the dongle and top-level `upstreamhost` for the
  cable; **with `devices:` set the add-on ignored the top-level pair**, so the cable's proxy never started
  and 502 refused. Both in the `devices:` list, both ports published on its Network tab, it served both.
- Read through each port before the entries were made: unit 1 answered `0x0E0E` on both, register 13000
  read `8` on the cable and `5120` on the dongle (re-encoded, as known), and unit 3 (the wallbox) answered
  only through the dongle's port.

## The update

- The Marketplace's update entity (`update.<repository>`) still read the previous commit an hour after
  the mirror had synced the new release; `homeassistant.update_entity` changed nothing. **Reloading the
  Marketplace config entry** made it see the new commit; `update.install` installed it, and a restart
  loaded it. Nothing logged an error from the integration.
- After the restart every legacy id was still a `restored` placeholder; the setup dialog said so
  ("the YAML package is not running, so its entity ids are free to take over") and counted 150 known ids.

## The entries

- The inverter, added by address through the proxy's cable port (manual step; unit 1): created, title the
  model. **A pending zeroconf card for the same inverter (the dongle's announcement) made the manual
  flow abort with `already_in_progress`**; dismissing that card (not ignoring it) let the manual flow
  through. The wallbox's own card was left and used for its entry.
- Answered *migrate legacy ids*: **150 ids adopted**, `sensor.total_dc_power` and the rest of the Energy
  dashboard's sensors now belong to `sungrow_modbus` under their old ids. Seven kept a `_2`, because the
  owner's own template sensors already held the plain id (the meter's powers and two consumed-energy
  counters); two series numbers (`..._1`, `..._2`) are slots, not collisions.
- The wallbox, from its discovery card (TLS, its own address): created; its options offered exactly one
  inverter to be managed by, chosen.
- After two minutes: 235 inverter, 24 battery and 40 wallbox entities, 222, 18 and 33 with a value. The
  rest were unavailable (no car; features this model lacks).
- Options saved with every capability test and `publish_address` off; both default **on** in the options
  form for the inverter entry.

## The Energy dashboard after the gap

- Today's solar read a very large negative amount: the hour of the first start had a `change` of
  minus the whole sum the series had built up. The same on all five counters the dashboard uses (solar,
  import, export, battery in and out); `validate_statistics` named none of them.
- Rows: the last old hourly row's `sum` was large and its `state` a little below the counter's value
  at the first start; the first new row had `sum` 0.0 (or 0.1) and the counter's value as `state`.
  The old series stopped 12.6 days earlier. HA continues a sum from the **short-term** (5-minute)
  table, which keeps ten days; with no row there the sum starts again at zero.
- `recorder/adjust_sum_statistics` per counter, `start_time` the first new hour (UTC), `adjustment` the
  old final sum minus the new first sum, unit kWh: the series is continuous, the gap's energy is in no
  hour, and the day after read plausibly (a few tenths of a kWh of solar at 08:00, import a few kWh
  overnight). The preferences before and the registry were saved first, with a full backup that holds
  the recorder.
- The wallbox's lifetime counter, in Wh, was added to the Energy preferences as a device with its power
  as the rate; `energy/validate` returned no issue.

## Cards

- Entities that belong to a device are shown as the device's name followed by their own; the YAML
  package's had no device. A row that sets `name:` shows its own name only. The owner's dashboard, built
  for entities without a device, showed "<model> Device type" until each row was given a name.
- The owner's Quick view used four `custom:` cards from the Marketplace. After the update they showed
  "Custom element doesn't exist" until the page was reloaded in the browser; their files were served
  (HTTP 200) the whole time.
