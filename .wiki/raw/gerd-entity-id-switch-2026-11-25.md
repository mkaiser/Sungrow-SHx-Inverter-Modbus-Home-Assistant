# gerd's own Home Assistant, 2026-11-25: from the YAML package's ids to device-scoped ids

Raw note. Home Assistant 2026.11.3, integration 0.1.0a55, recorder on MariaDB, over VPN. Times are CET.
A full backup was taken and copied off the host first (its size matches; not test-restored). Auto repeat was stopped for it.

## Found before

- The YAML package is not running: no `template` component loaded; its 41 remaining registry rows (modbus, template, input_*)
  were `restored` placeholders.
- **The seven `_2` ids of 2026-11-21 were not the owner's own templates.** Both rows of each pair came from YAML package
  versions: the plain id from the older one (until 2025-12-30), the `_2` from the newer one, which had another platform
  or unique id. (`sungrow_version_2` is a slot and no collision.)
- The older package's month and year sensors ended on 2025-12-30; their statistics are still in the recorder.
- Five lifetime counters outside the Energy dashboard still had the negative hour of the first start.

## Done

- The options' *Entity IDs* switch to device-scoped ids, submitted: 119 renamed, 20 legacy-only removed, no archives. Statistics: every
  renamed id that had them has them under the new id, and none is left under the old.
- **The six `_2` ids (four meter powers, two consumed energies) were left out by the switch**: they were not on the legacy id it
  expected. Renamed in the registry by hand; the statistics followed.
- Energy preferences: the ids replaced, `energy/validate` clean. **The two automatic cost sensors read unavailable after the save
  and came back, under their old ids, after a restart.**
- Three dashboards rewritten, one deleted.
- `recorder/adjust_sum_statistics` on the five counters.
- `recorder/import_statistics`: the older hours of the total consumed energy and the four meter powers joined onto the new ids
  (17874 and 17887 rows each); the rows already there stayed identical. The energy series' old sums were shifted by one constant.
  **The daily consumed energy was not joined**: its older `sum` is about 13 times the lifetime counter's over the same hours.
- The 41 rows removed. Series that had rows keep them (three checked).

## Not done

- No dashboard was looked at in a browser; every entity id in the three exists.
- Total direct energy consumption has an older negative hour (January 2025) that was left.
- The error log over the API answered nothing; only `system_log/list` was read.
- InfluxDB (connected there): nothing rewritten, so its series are split at the rename.
