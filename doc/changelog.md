# Changelog

## v2.0.0

Full rewrite: the project is now a proper Home Assistant **custom
integration** (`sungrow_shx`) instead of a YAML package. See the
[migration guide](migration_guide.md) for the upgrade path and entity-ID
mapping.

- **HACS distribution** — install as a custom repository
  (Integration category). Manual drop-in install into
  `custom_components/sungrow_shx/` is also supported.
- **UI config flow** — configure host, port, slave, SBR slave, battery
  max power, and inter-request delay from *Settings → Devices & services*.
  No more `secrets.yaml` entries, no more `!include`.
- **Options flow** — four polling buckets (realtime / fast / medium /
  slowest) are now tunable per device without editing YAML.
- **UI-based multi-inverter support** — add the integration once per
  inverter. Each entry is a separate device with its own entities.
- **Dropped the regex-based multi-inverter generator** — the
  `modbus_sungrow_multiple_inverters_{1,2,3}.yaml` files and the Python
  generator under `scripts/` are no longer part of the install path
  (they remain on the `legacy` branch).
- **Breaking: entity IDs have changed.** Entities are now scoped under
  the device name (`sensor.sungrow_inverter_*` by default) instead of
  the global `sensor.sg_*` / `sensor.sungrow_*` prefixes. See the
  mapping table in the migration guide; rename the device *before*
  rebuilding automations to keep slugs stable.
- The legacy YAML package is **frozen** on the `legacy` branch/tag —
  no new features.

Known gaps:
- Dashboards under `dashboards/` have **not yet been updated** to the new
  entity IDs; this is planned as a follow-up.

## Versions before 2026

The new 2026 version is a major rework of the integration and comes with minor breaking changes (see [migration guide](doc/migration_guide.md) for details).

Major Changes: 
 - Compatibility for the new Home Assistant Energy Dashboard introduced in 2025.12
 - Create a "howto migrate to version 2" guide
 - Generate python script to generate config files for multiple inverter setups with _inv_1 and _inv_2 ... as suffix
 - Update doc for HA Energy dashboard configuration ("Use Battery discharging power signed" as battery power sensor)
 - Rename secret sungrow_modbus_slave to sungrow_modbus_device_address to match modbus naming
 - Add MIT licence
 - Rename "System state" to "Running state"
 - Use nan_value to eliminate Template sensors for Meter [phase 1-3] active power and MPPT3 voltage/current
 - Use compact maps for decoding the "running state" (updated from modbus spec) and for device type code
 - Use a switch (Sungrow dashboard enable danger mode) with an automation to hide / show dangerous elements in the dashboard (works with the default dashboard)
 - Use more YAML anchors: Define register addresses when defining the sensors and reuse the variables in automations
 - Move automation for inputs into the template sections (https://github.com/theunknown86/unknown_sungrow/blob/ec2464f3c9abcc6cc6c11041499d6f380ba05201/modbus_sungrow_inv1.yaml#L1682-L1699)
 - Rename "running state" to "power flow status" and update code for binary sensors: https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/565
 - Use secrets for battery parametershttps://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/blob/dev/doc/faq.md
 - Remove unnecessary parentheses in if-else statements.
 - Implement MPPT3 for SH*T inverters, not resulting in broken / unknown sensors for SH*RT inverters
 - Use YAML anchors different scan_intervals (e.g. scan_interval_slowest, scan_interval_mid, scan_interval_frequent, scan_interval_realtime)
 - Update modbus sensor registers after modbus writes in input number templates
 - Use scenes instead of automations