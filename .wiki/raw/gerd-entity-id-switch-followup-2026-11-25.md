# gerd's own Home Assistant, 2026-11-25: after the switch

Raw note, follows `gerd-entity-id-switch-2026-11-25.md`. Over VPN and SSH.

- The first views of his three dashboards, the integration's own and Home Assistant's Energy page were opened in Chromium: no error
  card, no console error, values everywhere, the 24-hour graphs without a visible break at the rename.
- **The joined total consumed energy had two restarts of its own sum inside the old series** (2025-01-25, 2025-03-08), not looked for before the
  join; *Total direct energy consumption* had the same two dates. All four adjusted with `recorder/adjust_sum_statistics`; no sum falls
  by more than 1 kWh in either now. The other totals of the inverter: none, except one dip of 1.6 kWh in imported energy in 2023.
- The older daily consumed energy was rounded to whole kWh and `total_increasing`: its sum is about 5.4 times the daily end values. The
  cause is inferred (a fall of one whole kWh taken for a reset): hourly rows do not show the falls. The newer one, `total` without
  `last_reset`, has a sum that did not grow over 315 days.
- The 32 automations and 4 scripts of the YAML package, all `restored`, were deleted; the package's link was renamed.
