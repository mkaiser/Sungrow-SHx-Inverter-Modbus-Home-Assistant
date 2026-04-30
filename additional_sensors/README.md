# Additional sensors

This folder contains optional sensors that are not part of the default setup.

## `modbus_sungrow_SBR_battery.yaml`

Extra Modbus settings for SBR batteries - provides per-module cell information.

**Installation:** Copy the relevant sections into your `modbus_sungrow*.yaml` file.

---

## `multiple_inverter_aggregate_sensors.yaml`

Template sensors for multi-inverter installations.

These aggregate selected PV generation values across all inverter-specific entities:

- Total DC Power (All Inverters)
- Daily PV Generation (All Inverters)
- Total PV Generation (All Inverters)
- PV Generating (All Inverters)

**Note:** The aggregate template sensors assume the default naming schemes used by this project. They match both unsuffixed single-inverter entities such as `sensor.total_dc_power` and inverter-specific entities suffixed with `_inv_1`, `_inv_2`, etc. If you have manually renamed entities or use a different naming scheme, you may need to adjust the templates accordingly.

**Installation:**

1. Copy `multiple_inverter_aggregate_sensors.yaml` to: `/config/templates/`
2. Ensure your `configuration.yaml` includes:

```yaml
template: !include_dir_merge_list templates/
```

3. Restart Home Assistant (or reload template entities).