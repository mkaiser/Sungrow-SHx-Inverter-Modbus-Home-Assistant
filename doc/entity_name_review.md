# The entity names, for review

**139 entities**, which is everything modern mode creates. The **entity id**
column is what a dashboard and years of history are keyed to, and a name supplies
it -- but only at creation. Rename later and anybody who already has the entity
keeps the id they were born with; only the label changes. So the cost of a late
rename is **divergence** between houses set up before and after, not lost
history, and where that matters a registry rename moves the early one across.

The **legacy name** is what a migrating user calls the same reading today, and
a **←** marks the ones that differ.

A further 19 sensors exist **only in legacy mode** and are listed at the
end. Their names need no judgement: they are the YAML package's, kept so that
history keyed to them carries on, and modern mode replaces each with something
better.


## Backup power (5)

| Name | Entity id | Unit | Legacy name |
| --- | --- | --- | --- |
| Backup mode | `switch.sh10rt_backup_mode` |  | Backup Mode **←** |
| Backup phase A power | `sensor.sh10rt_backup_phase_a_power` | W | Backup phase A power |
| Backup phase B power | `sensor.sh10rt_backup_phase_b_power` | W | Backup phase B power |
| Backup phase C power | `sensor.sh10rt_backup_phase_c_power` | W | Backup phase C power |
| Total backup power | `sensor.sh10rt_total_backup_power` | W | Total backup power |

## Control (4)

| Name | Entity id | Unit | Legacy name |
| --- | --- | --- | --- |
| Active power limitation | `binary_sensor.sh10rt_active_power_limitation` |  |  |
| Active power limitation ratio | `sensor.sh10rt_active_power_limitation_ratio` | % | Active power limitation ratio raw **←** |
| EMS mode | `select.sh10rt_ems_mode` |  | EMS mode |
| Feed-in limitation ratio | `sensor.sh10rt_feed_in_limitation_ratio` | % |  |

## Energy totals (7)

| Name | Entity id | Unit | Legacy name |
| --- | --- | --- | --- |
| Daily consumed energy | `sensor.sh10rt_daily_consumed_energy` | kWh | Daily consumed energy |
| Daily consumed energy (smoothed) | `sensor.sh10rt_daily_consumed_energy_smoothed` | kWh | Daily consumed energy (filtered) **←** |
| Daily direct energy consumption | `sensor.sh10rt_daily_direct_energy_consumption` | kWh | Daily direct energy consumption |
| Total DC power | `sensor.sh10rt_total_dc_power` | W | Total DC power |
| Total active power | `sensor.sh10rt_total_active_power` | W | Total active power |
| Total consumed energy | `sensor.sh10rt_total_consumed_energy` | kWh | Total consumed energy |
| Total direct energy consumption | `sensor.sh10rt_total_direct_energy_consumption` | kWh | Total direct energy consumption |

## Everything else (13)

| Name | Entity id | Unit | Legacy name |
| --- | --- | --- | --- |
| ARM software version | `sensor.sh10rt_arm_software_version` |  | Sungrow Arm Software **←** |
| Active power limitation shutdown at zero | `sensor.sh10rt_active_power_limitation_shutdown_at_zero` |  | APL shutdown at zero raw **←** |
| BDC rated power | `sensor.sh10rt_bdc_rated_power` | W | BDC rated power |
| DSP software version | `sensor.sh10rt_dsp_software_version` |  | Sungrow DSP Software **←** |
| Firmware version part 1 | `sensor.sh10rt_firmware_version_part_1` |  | Sungrow Version 1 **←** |
| Firmware version part 2 | `sensor.sh10rt_firmware_version_part_2` |  | Sungrow Version 2 **←** |
| Firmware version part 3 | `sensor.sh10rt_firmware_version_part_3` |  | Sungrow Version 3 **←** |
| Power factor | `sensor.sh10rt_power_factor` |  | Power factor |
| Power flow status | `sensor.sh10rt_power_flow_status` |  | Power Flow Status **←** |
| Protocol version | `sensor.sh10rt_protocol_version` |  | Sungrow Protocol Version **←** |
| Rated output power | `sensor.sh10rt_rated_output_power` | W | Inverter rated output **←** |
| Reactive power | `sensor.sh10rt_reactive_power` | W | Reactive power |
| Running state | `sensor.sh10rt_running_state` |  | Sungrow inverter state **←** |

## Identity and firmware (5)

| Name | Entity id | Unit | Legacy name |
| --- | --- | --- | --- |
| Communication module firmware version | `sensor.sh10rt_communication_module_firmware_version` |  | Communication Module Firmware Version **←** |
| Device type | `sensor.sh10rt_device_type` |  | Sungrow device type **←** |
| Device type code | `sensor.sh10rt_device_type_code` |  | Sungrow device type code **←** |
| Firmware version | `sensor.sh10rt_firmware_version` |  | Inverter Firmware Version **←** |
| Serial number | `sensor.sh10rt_serial_number` |  | Sungrow inverter serial **←** |

## Per phase (9)

| Name | Entity id | Unit | Legacy name |
| --- | --- | --- | --- |
| Phase A current | `sensor.sh10rt_phase_a_current` | A | Phase A current |
| Phase A power | `sensor.sh10rt_phase_a_power` | W | Phase A power |
| Phase A voltage | `sensor.sh10rt_phase_a_voltage` | V | Phase A voltage |
| Phase B current | `sensor.sh10rt_phase_b_current` | A | Phase B current |
| Phase B power | `sensor.sh10rt_phase_b_power` | W | Phase B power |
| Phase B voltage | `sensor.sh10rt_phase_b_voltage` | V | Phase B voltage |
| Phase C current | `sensor.sh10rt_phase_c_current` | A | Phase C current |
| Phase C power | `sensor.sh10rt_phase_c_power` | W | Phase C power |
| Phase C voltage | `sensor.sh10rt_phase_c_voltage` | V | Phase C voltage |

## Temperatures (1)

| Name | Entity id | Unit | Legacy name |
| --- | --- | --- | --- |
| Temperature | `sensor.sh10rt_temperature` | °C | Inverter temperature **←** |

## The PV trackers (19)

| Name | Entity id | Unit | Legacy name |
| --- | --- | --- | --- |
| Daily PV generation | `sensor.sh10rt_daily_pv_generation` | kWh | Daily PV generation |
| Daily exported energy from PV | `sensor.sh10rt_daily_exported_energy_from_pv` | kWh | Daily exported energy from PV |
| MPPT1 current | `sensor.sh10rt_mppt1_current` | A | MPPT1 current |
| MPPT1 power | `sensor.sh10rt_mppt1_power` | W | MPPT1 power |
| MPPT1 voltage | `sensor.sh10rt_mppt1_voltage` | V | MPPT1 voltage |
| MPPT2 current | `sensor.sh10rt_mppt2_current` | A | MPPT2 current |
| MPPT2 power | `sensor.sh10rt_mppt2_power` | W | MPPT2 power |
| MPPT2 voltage | `sensor.sh10rt_mppt2_voltage` | V | MPPT2 voltage |
| MPPT3 current | `sensor.sh10rt_mppt3_current` | A | MPPT3 current |
| MPPT3 power | `sensor.sh10rt_mppt3_power` | W | MPPT3 power |
| MPPT3 voltage | `sensor.sh10rt_mppt3_voltage` | V | MPPT3 voltage |
| MPPT4 current | `sensor.sh10rt_mppt4_current` | A | MPPT4 current |
| MPPT4 power | `sensor.sh10rt_mppt4_power` | W | MPPT4 power |
| MPPT4 voltage | `sensor.sh10rt_mppt4_voltage` | V | MPPT4 voltage |
| PV generating | `binary_sensor.sh10rt_pv_generating` |  | PV generating |
| PV generating (delayed) | `binary_sensor.sh10rt_pv_generating_delayed` |  | PV generating (delay) **←** |
| PV power limitation | `binary_sensor.sh10rt_pv_power_limitation` |  |  |
| Total PV generation | `sensor.sh10rt_total_pv_generation` | kWh | Total PV generation |
| Total exported energy from PV | `sensor.sh10rt_total_exported_energy_from_pv` | kWh | Total exported energy from PV |

## The battery (40)

| Name | Entity id | Unit | Legacy name |
| --- | --- | --- | --- |
| BMS max charging current | `sensor.sh10rt_bms_max_charging_current` | A | BMS max. charging current **←** |
| BMS max discharging current | `sensor.sh10rt_bms_max_discharging_current` | A | BMS max. discharging current **←** |
| Battery capacity high precision | `sensor.sh10rt_battery_capacity_high_precision` | kWh | Battery capacity high precision |
| Battery charge | `sensor.sh10rt_battery_charge` | kWh | Battery charge |
| Battery charge (health-rated) | `sensor.sh10rt_battery_charge_health_rated` | kWh | Battery charge (health-rated) |
| Battery charge (nominal) | `sensor.sh10rt_battery_charge_nominal` | kWh | Battery charge (nominal) |
| Battery charging | `binary_sensor.sh10rt_battery_charging` |  | Battery charging |
| Battery charging (delayed) | `binary_sensor.sh10rt_battery_charging_delayed` |  | Battery charging (delay) **←** |
| Battery charging power | `sensor.sh10rt_battery_charging_power` | W | Battery charging power |
| Battery charging power signed | `sensor.sh10rt_battery_charging_power_signed` | W | Battery charging power signed |
| Battery charging start power | `number.sh10rt_battery_charging_start_power` | W | Battery charging start power |
| Battery current | `sensor.sh10rt_battery_current` | A | Battery current |
| Battery discharging | `binary_sensor.sh10rt_battery_discharging` |  | Battery discharging |
| Battery discharging (delayed) | `binary_sensor.sh10rt_battery_discharging_delayed` |  | Battery discharging (delay) **←** |
| Battery discharging power | `sensor.sh10rt_battery_discharging_power` | W | Battery discharging power |
| Battery discharging power signed | `sensor.sh10rt_battery_discharging_power_signed` | W | Battery discharging power signed |
| Battery discharging start power | `number.sh10rt_battery_discharging_start_power` | W | Battery discharging start power |
| Battery firmware version | `sensor.sh10rt_battery_firmware_version` |  | Battery Firmware Version **←** |
| Battery forced charge discharge | `select.sh10rt_battery_forced_charge_discharge` |  | Battery forced charge discharge |
| Battery forced charge/discharge power | `number.sh10rt_battery_forced_charge_discharge_power` | W | Battery forced charge discharge power **←** |
| Battery level | `sensor.sh10rt_battery_level` | % | Battery level |
| Battery level (nominal) | `sensor.sh10rt_battery_level_nominal` | % | Battery level (nominal) |
| Battery max SoC | `number.sh10rt_battery_max_soc` | % | Battery Max Soc **←** |
| Battery max charge power | `number.sh10rt_battery_max_charge_power` | W | Battery max charge power |
| Battery max discharge power | `number.sh10rt_battery_max_discharge_power` | W | Battery max discharge power |
| Battery min SoC | `number.sh10rt_battery_min_soc` | % | Battery Min Soc **←** |
| Battery power | `sensor.sh10rt_battery_power` | W | Battery power |
| Battery reserved SoC for backup | `number.sh10rt_battery_reserved_soc_for_backup` | % | Battery Reserved SoC for Backup **←** |
| Battery state of health | `sensor.sh10rt_battery_state_of_health` | % | Battery state of health |
| Battery temperature | `sensor.sh10rt_battery_temperature` | °C | Battery temperature |
| Battery voltage | `sensor.sh10rt_battery_voltage` | V | Battery voltage |
| Daily PV generation & battery discharge | `sensor.sh10rt_daily_pv_generation_battery_discharge` | kWh | Daily PV generation & battery discharge |
| Daily battery charge | `sensor.sh10rt_daily_battery_charge` | kWh | Daily battery charge |
| Daily battery charge from PV | `sensor.sh10rt_daily_battery_charge_from_pv` | kWh | Daily battery charge from PV |
| Daily battery discharge | `sensor.sh10rt_daily_battery_discharge` | kWh | Daily battery discharge |
| Firmware version part 4 (Sungrow battery) | `sensor.sh10rt_firmware_version_part_4_sungrow_battery` |  | Sungrow Version 4 (Sungrow Battery) **←** |
| Total PV generation & battery discharge | `sensor.sh10rt_total_pv_generation_battery_discharge` | kWh | Total PV generation & battery discharge |
| Total battery charge | `sensor.sh10rt_total_battery_charge` | kWh | Total battery charge |
| Total battery charge from PV | `sensor.sh10rt_total_battery_charge_from_pv` | kWh | Total battery charge from PV |
| Total battery discharge | `sensor.sh10rt_total_battery_discharge` | kWh | Total battery discharge |

## The grid (15)

| Name | Entity id | Unit | Legacy name |
| --- | --- | --- | --- |
| Daily exported energy | `sensor.sh10rt_daily_exported_energy` | kWh | Daily exported energy |
| Daily imported energy | `sensor.sh10rt_daily_imported_energy` | kWh | Daily imported energy |
| Export power | `sensor.sh10rt_export_power` | W | Export power |
| Export power limit | `number.sh10rt_export_power_limit` | W | Export power limit |
| Export power limit max | `sensor.sh10rt_export_power_limit_max` | W | Export power limit max |
| Export power limit min | `sensor.sh10rt_export_power_limit_min` | W | Export power limit min |
| Export power limit mode | `switch.sh10rt_export_power_limit_mode` |  | Export power limit **←** |
| Exporting power | `binary_sensor.sh10rt_exporting_power` |  | Exporting Power **←** |
| Exporting power (delayed) | `binary_sensor.sh10rt_exporting_power_delayed` |  | Exporting Power (delay) **←** |
| Grid frequency | `sensor.sh10rt_grid_frequency` | Hz | Grid frequency |
| Import power | `sensor.sh10rt_import_power` | W | Import power |
| Importing power | `binary_sensor.sh10rt_importing_power` |  | Importing Power **←** |
| Importing power (delayed) | `binary_sensor.sh10rt_importing_power_delayed` |  | Importing Power (delay) **←** |
| Total exported energy | `sensor.sh10rt_total_exported_energy` | kWh | Total exported energy |
| Total imported energy | `sensor.sh10rt_total_imported_energy` | kWh | Total imported energy |

## The house (7)

| Name | Entity id | Unit | Legacy name |
| --- | --- | --- | --- |
| Load adjustment | `switch.sh10rt_load_adjustment` |  | Load adjustment mode **←** |
| Load adjustment mode | `select.sh10rt_load_adjustment_mode` |  | Load adjustment mode |
| Load power | `sensor.sh10rt_load_power` | W | Load power |
| Negative load power | `binary_sensor.sh10rt_negative_load_power` |  | Negative Load Power **←** |
| Negative load power (delayed) | `binary_sensor.sh10rt_negative_load_power_delayed` |  | Negative Load Power (delay) **←** |
| Positive load power | `binary_sensor.sh10rt_positive_load_power` |  | Positive Load Power **←** |
| Positive load power (delayed) | `binary_sensor.sh10rt_positive_load_power_delayed` |  | Positive Load Power (delay) **←** |

## The meter (14)

| Name | Entity id | Unit | Legacy name |
| --- | --- | --- | --- |
| Meter active power | `sensor.sh10rt_meter_active_power` | W | Meter active power |
| Meter channel 2 phase A active power | `sensor.sh10rt_meter_channel_2_phase_a_active_power` | W |  |
| Meter channel 2 phase B active power | `sensor.sh10rt_meter_channel_2_phase_b_active_power` | W |  |
| Meter channel 2 phase C active power | `sensor.sh10rt_meter_channel_2_phase_c_active_power` | W |  |
| Meter channel 2 total active power | `sensor.sh10rt_meter_channel_2_total_active_power` | W |  |
| Meter phase A active power | `sensor.sh10rt_meter_phase_a_active_power` | W | Meter phase A active power |
| Meter phase A current | `sensor.sh10rt_meter_phase_a_current` | A | Meter phase A current |
| Meter phase A voltage | `sensor.sh10rt_meter_phase_a_voltage` | V | Meter phase A voltage |
| Meter phase B active power | `sensor.sh10rt_meter_phase_b_active_power` | W | Meter phase B active power |
| Meter phase B current | `sensor.sh10rt_meter_phase_b_current` | A | Meter phase B current |
| Meter phase B voltage | `sensor.sh10rt_meter_phase_b_voltage` | V | Meter phase B voltage |
| Meter phase C active power | `sensor.sh10rt_meter_phase_c_active_power` | W | Meter phase C active power |
| Meter phase C current | `sensor.sh10rt_meter_phase_c_current` | A | Meter phase C current |
| Meter phase C voltage | `sensor.sh10rt_meter_phase_c_voltage` | V | Meter phase C voltage |

## Legacy mode only (19)

Not created in modern mode. Each is a second copy of something a user
already has, so the column on the right is where the reading went instead.

| Name | Entity id | Replaced in modern mode by |
| --- | --- | --- |
| Active power limitation raw | `sensor.sh10rt_active_power_limitation_raw` | `binary_sensor.active_power_limitation_enabled` |
| Backup mode raw | `sensor.sh10rt_backup_mode_raw` | `switch.backup_mode` |
| Battery charging start power | `sensor.sh10rt_battery_charging_start_power` | `number.battery_charging_start_power` |
| Battery discharging start power | `sensor.sh10rt_battery_discharging_start_power` | `number.battery_discharging_start_power` |
| Battery forced charge/discharge command raw | `sensor.sh10rt_battery_forced_charge_discharge_command_raw` | `select.battery_forced_charge_discharge` |
| Battery forced charge/discharge power | `sensor.sh10rt_battery_forced_charge_discharge_power` | `number.battery_forced_charge_discharge_power` |
| Battery max SoC | `sensor.sh10rt_battery_max_soc` | `number.battery_max_soc` |
| Battery max charge power | `sensor.sh10rt_battery_max_charge_power` | `number.battery_max_charge_power` |
| Battery max discharge power | `sensor.sh10rt_battery_max_discharge_power` | `number.battery_max_discharge_power` |
| Battery min SoC | `sensor.sh10rt_battery_min_soc` | `number.battery_min_soc` |
| Battery reserved SoC for backup | `sensor.sh10rt_battery_reserved_soc_for_backup` | `number.battery_reserved_soc_for_backup` |
| EMS mode selection raw | `sensor.sh10rt_ems_mode_selection_raw` | `select.ems_mode` |
| Export power limit | `sensor.sh10rt_export_power_limit` | `number.export_power_limit` |
| Export power limit mode raw | `sensor.sh10rt_export_power_limit_mode_raw` | `switch.export_power_limit_mode` |
| Export power raw | `sensor.sh10rt_export_power_raw` | `sensor.export_power` |
| Load adjustment mode enable raw | `sensor.sh10rt_load_adjustment_mode_enable_raw` | `switch.load_adjustment_mode_enable` |
| Load adjustment mode selection raw | `sensor.sh10rt_load_adjustment_mode_selection_raw` | `select.load_adjustment_mode` |
| PV power limitation raw | `sensor.sh10rt_pv_power_limitation_raw` | `binary_sensor.pv_power_limitation_enabled` |
| Running state raw | `sensor.sh10rt_running_state_raw` | `sensor.sungrow_inverter_state` |
