# Changelog

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