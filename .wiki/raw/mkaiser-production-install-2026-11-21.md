# The maintainer's production Home Assistant, 2026-11-21: the integration beside the YAML package, behind a modbus proxy

Raw note. Times UTC. No address, serial or lifetime figure is in this note.

## The instance before

- Home Assistant 2026.11.2. The YAML package running and polling (150 of its entities live). The preview
  channel installed through the Marketplace at a45, no `sungrow_modbus` config entry.
- A modbus-proxy add-on (1.1.0), top-level `upstreamhost` only (no `devices:`), in front of the SH10RT's own
  LAN port; the YAML package reads through it.
- The YAML package's three automations fire only on scene activation (`scene.max_export_power`,
  `scene.self_consumption_mode_max_battery_discharge`) and a dashboard toggle, so nothing of the package's
  writes while the integration tests.

## The update and the entry

- The Marketplace's update entity showed the previous commit until the Marketplace entry was reloaded,
  as at gerd's; `update.install`, a config check, a restart: `0.1.0a46` loaded.
- Entry added by the manual step on the proxy add-on's internal hostname, port 502, unit 1. The
  setup dialog said the YAML package was still running with 150 entities holding ids, and offered only
  *new* ids; chosen.
- The device came back with its area and the diagnosis entities' last states from an earlier, deleted
  entry (ids restored by unique id).
- After about a minute: 209 entities, 1 disabled, 195 with a value, 12 `unknown`, 1 unavailable.
  Firmware read `SAPPHIRE-H_B001.V000.P020`. Nothing from the integration in the error log.
- **Both pollers through one proxy**: the YAML package's entities kept updating every few seconds the
  whole time, through the extended test and its restart included; no timeouts logged on either side.

## Extended test with capability test, 08:44:24-08:59:19

Options: every capability-test permission on, `battery_max_power` 5000 W, `publish_address` off. Mode
*extended* (single run). Conditions at the start: PV about 2.1 kW, load about 2.1 kW, SoC 16.2 %,
Running. Clouds took PV down to about 1.0-1.2 kW from 08:46 on.

- 256 fields read. Outcome "every planned check ran and every readback matched", 0 findings.
  21/54 passed, 0 failed, 5 not supported (the five *upper bound of battery_...power* checks: nothing
  measurable), 28 not run yet (plausibility checks waiting for observations, the thresholds, the
  charge ceiling with the battery at 16 %).
- **Site import limit (32998), with PV present but below the load**: under the forced charge the house
  imported 2439 W (sizing 2462 W); cap commanded 1830 W; import during 1876.5 W (ratio 1.03, MAD 6);
  after 2323 W (drift 116 W). Verdict "the inverter did as it was told". PV about 1.05 kW and load about
  2.09 kW during the step. So the cap held on grid import with PV contributing; the case where PV exceeds
  the load (T001) was not met.
- 32998 probe words: 0 refused (0x04), 5001 refused (0x04), 5000 taken; restored to 20000 (20 kW).
- `export_scale` answered "multiplies a written word by ten" (held 10000 refused 0x04 three times), as
  in October.
- Export limit at 1250 W: feed-in ratio 100 % -> 12.5 % -> back. EMS mode words 2, 3, 4 taken.
- Restart: Key stop at about 08:56:10, Standby, Starting from about 08:58:30, Running by 08:59:19 --
  roughly 3 min in daylight, as on 2026-10-16.
- Restore: 5 fields written back (the forced-charging window 1 times and target SoC) and read back at
  their originals; 40 already at their originals.

## Inverter self consumption (estimated), daylight (T002)

- 43 W at 08:42 (PV about 2 kW), 109 W at 09:00 (PV 1.8 kW, load 2.1 kW), Running. Single readings; the
  day's series is in the instance's recorder under the new entity.
- The recorder's series, 08:40-14:10, 3913 values, Running throughout but for the restart: median 248 W,
  10th-90th percentile 104-416 W, min -178 W, max 601 W. Hourly medians (UTC): 08h 143, 09h 241, 10h 266,
  11h 365 (PV ~8.4 kW, battery charging to full), 12h 159, 13h 281, 14h 285 W. It rises with the power
  converted, and single readings scatter by a few hundred watts either side, negatives included.

## Second extended test, 09:17:19-09:19:58, PV above the load

Restart permission off, *skip established* off, otherwise as above. PV 2.5-4.1 kW, load about 2.1 kW,
under passing clouds.

- Forced charge, forced discharge and the forced-charging window: "could not tell -- the input was
  already unstable" (PV swinging).
- **Site import limit: not run.** "the forced charge drew only 582 W from the grid, too little for a cap
  under it to be told from the house moving; PV was covering it". The engine commands its fixed 1250 W
  (`FORCED_EFFECT_W`), which a PV surplus of that size absorbs, so the engine cannot measure the
  PV-above-the-load case by design; it needs a forced charge above the surplus.
- Upper bounds: 13057 refused 101 % (0x04); 5100 W taken and stored for the max charge, max discharge and
  forced power, 1010 W for both start powers (bounds not enforced), as in the first run's "nothing
  measurable". Write paths 13075, 13011, 13002, 33179 took their own words. Everything at its original.

## T001 by hand through the integration's entities, 09:21:38-09:27:18

Snapshot of EMS mode, forced command, forced power and grid import limit to a file before the first
write; restore in `finally`, retried until the entity read back. Entities sampled every ~3 s (the
integration polls its fast group every 5 s; PV is the YAML package's sensor, polled separately, so
single rows mix moments).

- Self-consumption: PV 2.3-2.7 kW, load 2.1 kW, export ~50 W, SoC 16.2 %.
- Forced charge 4500 W (EMS forced): within ~15 s battery 4500 W, grid import 3.8-4.5 kW, PV
  2.4-2.7 kW, load 2.1 kW. Median of the last 15 samples 4386 W.
- **Cap 2190 W** (half of that import; nothing to subtract, since 4386 < 4500): within ~10 s the battery
  dropped to 2.4-3.0 kW and import to 1.5-2.5 kW while PV read 2.6-3.6 kW, **above** the 2.0-2.2 kW
  load. Median import over the 2 min 1933 W, against 2190 W. Single samples went back to battery 4500 W
  and import 3.8-4.2 kW where PV dipped (09:24:03, 09:24:51), then down again within ~10 s.
  Reading: the cap limits the grid's share; PV keeps feeding the battery on top of it.
- Cap lifted to 20000 W: PV swung 3.4-7.4 kW, import 0-3.3 kW, battery 4500 W; no clean after-bracket.
- Restored: EMS mode self_consumption, command stop, power 0, limit 20000 W, each read back on the first
  attempt. Running throughout. SoC 16.2 -> 18.7 %.
- Not a clean measurement: PV swung by up to 5 kW within seconds. A steady hour (clear sky, or a uniform
  overcast with PV a few hundred watts over the load) would give a bracket.

Options and *skip established* put back afterwards (restart permission on, skip on).
