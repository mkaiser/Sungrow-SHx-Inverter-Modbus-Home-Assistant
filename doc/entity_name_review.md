# The entity names, for review

**306 entities** that modern mode can create (Hybrid inverter 190, SBR battery 34, Wallbox 21, SG string inverter 61).

The **entity id**
column is what a dashboard and years of history are keyed to, and a name supplies
it -- but only at creation. Rename later and anybody who already has the entity
keeps the id they were born with; only the label changes. So the cost of a late
rename is **divergence** between houses set up before and after, not lost
history, and where that matters a registry rename moves the early one across.

Each id begins with its **device's name**, which differs between houses; one
real model stands in for each device below. The **legacy name** and **legacy
entity id** are what the YAML package calls the same entity: a user who
migrates keeps that id, and a fresh install gets the entity id. A **←**
marks a name that differs.

A further 20 sensors exist **only in legacy mode** and are listed at the
end. Their names need no judgement: they are the YAML package's, kept so that
history keyed to them carries on, and modern mode replaces each with something
better.


## Hybrid inverter (190)

The inverter's own device, named after the model unless the owner named it. Ids shown for `SH10RT`.

### Actions (2)

| Name | Entity id | Unit | Legacy name | Legacy entity id |
| --- | --- | --- | --- | --- |
| Run complete diagnosis and tests | `button.sh10rt_run_complete_diagnosis_and_tests` |  |  |  |
| Run read only diagnosis | `button.sh10rt_run_read_only_diagnosis` |  |  |  |

### Backup power (12)

| Name | Entity id | Unit | Legacy name | Legacy entity id |
| --- | --- | --- | --- | --- |
| Backup frequency | `sensor.sh10rt_backup_frequency` | Hz |  |  |
| Backup mode | `switch.sh10rt_backup_mode` |  | Backup Mode **←** | `switch.backup_mode` |
| Backup phase A current | `sensor.sh10rt_backup_phase_a_current` | A |  |  |
| Backup phase A power | `sensor.sh10rt_backup_phase_a_power` | W | Backup phase A power | `sensor.backup_phase_a_power` |
| Backup phase A voltage | `sensor.sh10rt_backup_phase_a_voltage` | V |  |  |
| Backup phase B current | `sensor.sh10rt_backup_phase_b_current` | A |  |  |
| Backup phase B power | `sensor.sh10rt_backup_phase_b_power` | W | Backup phase B power | `sensor.backup_phase_b_power` |
| Backup phase B voltage | `sensor.sh10rt_backup_phase_b_voltage` | V |  |  |
| Backup phase C current | `sensor.sh10rt_backup_phase_c_current` | A |  |  |
| Backup phase C power | `sensor.sh10rt_backup_phase_c_power` | W | Backup phase C power | `sensor.backup_phase_c_power` |
| Backup phase C voltage | `sensor.sh10rt_backup_phase_c_voltage` | V |  |  |
| Total backup power | `sensor.sh10rt_total_backup_power` | W | Total backup power | `sensor.total_backup_power` |

### Control (17)

| Name | Entity id | Unit | Legacy name | Legacy entity id |
| --- | --- | --- | --- | --- |
| Active power limitation | `binary_sensor.sh10rt_active_power_limitation` |  |  |  |
| Active power limitation ratio | `sensor.sh10rt_active_power_limitation_ratio` | % | Active power limitation ratio raw **←** | `sensor.active_power_limitation_ratio_raw` |
| EMS mode | `select.sh10rt_ems_mode` |  | EMS mode | `select.ems_mode` |
| Feed-in limitation ratio | `sensor.sh10rt_feed_in_limitation_ratio` | % |  |  |
| Forced charging days | `select.sh10rt_forced_charging_days` |  |  |  |
| Forced charging end 1 | `time.sh10rt_forced_charging_end_1` |  |  |  |
| Forced charging end 2 | `time.sh10rt_forced_charging_end_2` |  |  |  |
| Forced charging schedule | `switch.sh10rt_forced_charging_schedule` |  |  |  |
| Forced charging start 1 | `time.sh10rt_forced_charging_start_1` |  |  |  |
| Forced charging start 2 | `time.sh10rt_forced_charging_start_2` |  |  |  |
| Forced charging target SoC 1 | `number.sh10rt_forced_charging_target_soc_1` | % |  |  |
| Forced charging target SoC 2 | `number.sh10rt_forced_charging_target_soc_2` | % |  |  |
| Weekday discharge window 1 | `sensor.sh10rt_weekday_discharge_window_1` |  |  |  |
| Weekday discharge window 2 | `sensor.sh10rt_weekday_discharge_window_2` |  |  |  |
| Weekend discharge | `binary_sensor.sh10rt_weekend_discharge` |  |  |  |
| Weekend discharge window 1 | `sensor.sh10rt_weekend_discharge_window_1` |  |  |  |
| Weekend discharge window 2 | `sensor.sh10rt_weekend_discharge_window_2` |  |  |  |

### Everything else (5)

| Name | Entity id | Unit | Legacy name | Legacy entity id |
| --- | --- | --- | --- | --- |
| Active power limitation shutdown at zero | `sensor.sh10rt_active_power_limitation_shutdown_at_zero` |  | APL shutdown at zero raw **←** | `sensor.apl_shutdown_at_zero_raw` |
| Forced startup under low SoC raw | `sensor.sh10rt_forced_startup_under_low_soc_raw` |  |  |  |
| Power factor | `sensor.sh10rt_power_factor` |  | Power factor | `sensor.power_factor` |
| Power flow status | `sensor.sh10rt_power_flow_status` |  | Power Flow Status **←** | `sensor.power_flow_status` |
| Running state | `sensor.sh10rt_running_state` |  | Sungrow inverter state **←** | `sensor.sungrow_inverter_state` |

### Faults and alarms (9)

| Name | Entity id | Unit | Legacy name | Legacy entity id |
| --- | --- | --- | --- | --- |
| Alarm | `sensor.sh10rt_alarm` |  |  |  |
| Alarm reported | `binary_sensor.sh10rt_alarm_reported` |  |  |  |
| BDC-side fault | `sensor.sh10rt_bdc_side_fault` |  |  |  |
| BDC-side permanent fault | `sensor.sh10rt_bdc_side_permanent_fault` |  |  |  |
| DC-side fault | `sensor.sh10rt_dc_side_fault` |  |  |  |
| Fault reported | `binary_sensor.sh10rt_fault_reported` |  |  |  |
| Permanent fault | `sensor.sh10rt_permanent_fault` |  |  |  |
| System fault 1 | `sensor.sh10rt_system_fault_1` |  |  |  |
| System fault 2 | `sensor.sh10rt_system_fault_2` |  |  |  |

### Identity and firmware (11)

| Name | Entity id | Unit | Legacy name | Legacy entity id |
| --- | --- | --- | --- | --- |
| ARM software version | `sensor.sh10rt_arm_software_version` |  | Sungrow Arm Software **←** | `sensor.sungrow_arm_software` |
| Communication module firmware version | `sensor.sh10rt_communication_module_firmware_version` |  | Communication Module Firmware Version **←** | `sensor.communication_module_firmware_version` |
| DSP software version | `sensor.sh10rt_dsp_software_version` |  | Sungrow DSP Software **←** | `sensor.sungrow_dsp_software` |
| Device type | `sensor.sh10rt_device_type` |  | Sungrow device type **←** | `sensor.sungrow_device_type` |
| Device type code | `sensor.sh10rt_device_type_code` |  | Sungrow device type code **←** | `sensor.sungrow_device_type_code` |
| Firmware version | `sensor.sh10rt_firmware_version` |  | Inverter Firmware Version **←** | `sensor.inverter_firmware_version` |
| Firmware version part 1 | `sensor.sh10rt_firmware_version_part_1` |  | Sungrow Version 1 **←** | `sensor.sungrow_version_1` |
| Firmware version part 2 | `sensor.sh10rt_firmware_version_part_2` |  | Sungrow Version 2 **←** | `sensor.sungrow_version_2` |
| Firmware version part 3 | `sensor.sh10rt_firmware_version_part_3` |  | Sungrow Version 3 **←** | `sensor.sungrow_version_3` |
| Protocol version | `sensor.sh10rt_protocol_version` |  | Sungrow Protocol Version **←** | `sensor.sungrow_protocol_version` |
| Serial number | `sensor.sh10rt_serial_number` |  | Sungrow inverter serial **←** | `sensor.sungrow_inverter_serial` |

### Per phase (9)

| Name | Entity id | Unit | Legacy name | Legacy entity id |
| --- | --- | --- | --- | --- |
| Phase A current | `sensor.sh10rt_phase_a_current` | A | Phase A current | `sensor.phase_a_current` |
| Phase A power | `sensor.sh10rt_phase_a_power` | W | Phase A power | `sensor.phase_a_power` |
| Phase A voltage | `sensor.sh10rt_phase_a_voltage` | V | Phase A voltage | `sensor.phase_a_voltage` |
| Phase B current | `sensor.sh10rt_phase_b_current` | A | Phase B current | `sensor.phase_b_current` |
| Phase B power | `sensor.sh10rt_phase_b_power` | W | Phase B power | `sensor.phase_b_power` |
| Phase B voltage | `sensor.sh10rt_phase_b_voltage` | V | Phase B voltage | `sensor.phase_b_voltage` |
| Phase C current | `sensor.sh10rt_phase_c_current` | A | Phase C current | `sensor.phase_c_current` |
| Phase C power | `sensor.sh10rt_phase_c_power` | W | Phase C power | `sensor.phase_c_power` |
| Phase C voltage | `sensor.sh10rt_phase_c_voltage` | V | Phase C voltage | `sensor.phase_c_voltage` |

### Power (5)

| Name | Entity id | Unit | Legacy name | Legacy entity id |
| --- | --- | --- | --- | --- |
| BDC rated power | `sensor.sh10rt_bdc_rated_power` | W | BDC rated power | `sensor.bdc_rated_power` |
| Rated output power | `sensor.sh10rt_rated_output_power` | W | Inverter rated output **←** | `sensor.inverter_rated_output` |
| Reactive power | `sensor.sh10rt_reactive_power` | W | Reactive power | `sensor.reactive_power` |
| Total DC power | `sensor.sh10rt_total_dc_power` | W | Total DC power | `sensor.total_dc_power` |
| Total active power | `sensor.sh10rt_total_active_power` | W | Total active power | `sensor.total_active_power` |

### Temperatures (1)

| Name | Entity id | Unit | Legacy name | Legacy entity id |
| --- | --- | --- | --- | --- |
| Internal temperature | `sensor.sh10rt_internal_temperature` | °C | Inverter temperature **←** | `sensor.inverter_temperature` |

### The PV trackers (26)

| Name | Entity id | Unit | Legacy name | Legacy entity id |
| --- | --- | --- | --- | --- |
| Cut PV generation | `switch.sh10rt_cut_pv_generation` |  |  |  |
| Daily PV generation | `sensor.sh10rt_daily_pv_generation` | kWh | Daily PV generation | `sensor.daily_pv_generation` |
| Daily exported energy from PV | `sensor.sh10rt_daily_exported_energy_from_pv` | kWh | Daily exported energy from PV | `sensor.daily_exported_energy_from_pv` |
| Export from PV this month | `sensor.sh10rt_export_from_pv_this_month` | kWh |  |  |
| Export from PV this year | `sensor.sh10rt_export_from_pv_this_year` | kWh |  |  |
| MPPT1 current | `sensor.sh10rt_mppt1_current` | A | MPPT1 current | `sensor.mppt1_current` |
| MPPT1 power | `sensor.sh10rt_mppt1_power` | W | MPPT1 power | `sensor.mppt1_power` |
| MPPT1 voltage | `sensor.sh10rt_mppt1_voltage` | V | MPPT1 voltage | `sensor.mppt1_voltage` |
| MPPT2 current | `sensor.sh10rt_mppt2_current` | A | MPPT2 current | `sensor.mppt2_current` |
| MPPT2 power | `sensor.sh10rt_mppt2_power` | W | MPPT2 power | `sensor.mppt2_power` |
| MPPT2 voltage | `sensor.sh10rt_mppt2_voltage` | V | MPPT2 voltage | `sensor.mppt2_voltage` |
| MPPT3 current | `sensor.sh10rt_mppt3_current` | A | MPPT3 current | `sensor.mppt3_current` |
| MPPT3 power | `sensor.sh10rt_mppt3_power` | W | MPPT3 power | `sensor.mppt3_power` |
| MPPT3 voltage | `sensor.sh10rt_mppt3_voltage` | V | MPPT3 voltage | `sensor.mppt3_voltage` |
| MPPT4 current | `sensor.sh10rt_mppt4_current` | A | MPPT4 current | `sensor.mppt4_current` |
| MPPT4 power | `sensor.sh10rt_mppt4_power` | W | MPPT4 power | `sensor.mppt4_power` |
| MPPT4 voltage | `sensor.sh10rt_mppt4_voltage` | V | MPPT4 voltage | `sensor.mppt4_voltage` |
| PV generating | `binary_sensor.sh10rt_pv_generating` |  | PV generating | `binary_sensor.pv_generating` |
| PV generating (delayed) | `binary_sensor.sh10rt_pv_generating_delayed` |  | PV generating (delay) **←** | `binary_sensor.pv_generating_delay` |
| PV generation cut | `binary_sensor.sh10rt_pv_generation_cut` |  |  |  |
| PV generation this month | `sensor.sh10rt_pv_generation_this_month` | kWh |  |  |
| PV generation this year | `sensor.sh10rt_pv_generation_this_year` | kWh |  |  |
| PV power limitation | `binary_sensor.sh10rt_pv_power_limitation` |  |  |  |
| Total PV generation | `sensor.sh10rt_total_pv_generation` | kWh | Total PV generation | `sensor.total_pv_generation` |
| Total exported energy from PV | `sensor.sh10rt_total_exported_energy_from_pv` | kWh | Total exported energy from PV | `sensor.total_exported_energy_from_pv` |
| Total site PV power | `sensor.sh10rt_total_site_pv_power` | W |  |  |

### The battery (47)

| Name | Entity id | Unit | Legacy name | Legacy entity id |
| --- | --- | --- | --- | --- |
| BMS alarm | `sensor.sh10rt_bms_alarm` |  |  |  |
| BMS alarm 2 | `sensor.sh10rt_bms_alarm_2` |  |  |  |
| BMS fault 1 | `sensor.sh10rt_bms_fault_1` |  |  |  |
| BMS fault 2 | `sensor.sh10rt_bms_fault_2` |  |  |  |
| BMS max charging current | `sensor.sh10rt_bms_max_charging_current` | A | BMS max. charging current **←** | `sensor.bms_max_charging_current` |
| BMS max discharging current | `sensor.sh10rt_bms_max_discharging_current` | A | BMS max. discharging current **←** | `sensor.bms_max_discharging_current` |
| BMS protection | `sensor.sh10rt_bms_protection` |  |  |  |
| Battery alarm | `sensor.sh10rt_battery_alarm` |  |  |  |
| Battery capacity high precision | `sensor.sh10rt_battery_capacity_high_precision` | kWh | Battery capacity high precision | `sensor.battery_capacity_high_precision` |
| Battery charge | `sensor.sh10rt_battery_charge` | kWh | Battery charge | `sensor.battery_charge` |
| Battery charge (health-rated) | `sensor.sh10rt_battery_charge_health_rated` | kWh | Battery charge (health-rated) | `sensor.battery_charge_health_rated` |
| Battery charge (nominal) | `sensor.sh10rt_battery_charge_nominal` | kWh | Battery charge (nominal) | `sensor.battery_charge_nominal` |
| Battery charging | `binary_sensor.sh10rt_battery_charging` |  | Battery charging | `binary_sensor.battery_charging` |
| Battery charging (delayed) | `binary_sensor.sh10rt_battery_charging_delayed` |  | Battery charging (delay) **←** | `binary_sensor.battery_charging_delay` |
| Battery charging power | `sensor.sh10rt_battery_charging_power` | W | Battery charging power | `sensor.battery_charging_power` |
| Battery charging power signed | `sensor.sh10rt_battery_charging_power_signed` | W | Battery charging power signed | `sensor.battery_charging_power_signed` |
| Battery charging start power | `number.sh10rt_battery_charging_start_power` | W | Battery charging start power | `number.battery_charging_start_power` |
| Battery current | `sensor.sh10rt_battery_current` | A | Battery current | `sensor.battery_current` |
| Battery discharging | `binary_sensor.sh10rt_battery_discharging` |  | Battery discharging | `binary_sensor.battery_discharging` |
| Battery discharging (delayed) | `binary_sensor.sh10rt_battery_discharging_delayed` |  | Battery discharging (delay) **←** | `binary_sensor.battery_discharging_delay` |
| Battery discharging power | `sensor.sh10rt_battery_discharging_power` | W | Battery discharging power | `sensor.battery_discharging_power` |
| Battery discharging power signed | `sensor.sh10rt_battery_discharging_power_signed` | W | Battery discharging power signed | `sensor.battery_discharging_power_signed` |
| Battery discharging start power | `number.sh10rt_battery_discharging_start_power` | W | Battery discharging start power | `number.battery_discharging_start_power` |
| Battery fault | `sensor.sh10rt_battery_fault` |  |  |  |
| Battery firmware version | `sensor.sh10rt_battery_firmware_version` |  | Battery Firmware Version **←** | `sensor.battery_firmware_version` |
| Battery forced charge/discharge | `select.sh10rt_battery_forced_charge_discharge` |  | Battery forced charge discharge **←** | `select.battery_forced_charge_discharge` |
| Battery forced charge/discharge power | `number.sh10rt_battery_forced_charge_discharge_power` | W | Battery forced charge discharge power **←** | `number.battery_forced_charge_discharge_power` |
| Battery level | `sensor.sh10rt_battery_level` | % | Battery level | `sensor.battery_level` |
| Battery level (nominal) | `sensor.sh10rt_battery_level_nominal` | % | Battery level (nominal) | `sensor.battery_level_nominal` |
| Battery max SoC | `number.sh10rt_battery_max_soc` | % | Battery Max Soc **←** | `number.battery_max_soc` |
| Battery max charging power | `number.sh10rt_battery_max_charging_power` | W | Battery max charge power **←** | `number.battery_max_charge_power` |
| Battery max discharging power | `number.sh10rt_battery_max_discharging_power` | W | Battery max discharge power **←** | `number.battery_max_discharge_power` |
| Battery min SoC | `number.sh10rt_battery_min_soc` | % | Battery Min Soc **←** | `number.battery_min_soc` |
| Battery power | `sensor.sh10rt_battery_power` | W | Battery power | `sensor.battery_power` |
| Battery reserved SoC for backup | `number.sh10rt_battery_reserved_soc_for_backup` | % | Battery Reserved SoC for Backup **←** | `number.battery_reserved_soc_for_backup` |
| Battery state of health | `sensor.sh10rt_battery_state_of_health` | % | Battery state of health | `sensor.battery_state_of_health` |
| Battery temperature | `sensor.sh10rt_battery_temperature` | °C | Battery temperature | `sensor.battery_temperature` |
| Battery voltage | `sensor.sh10rt_battery_voltage` | V | Battery voltage | `sensor.battery_voltage` |
| Daily PV generation & battery discharge | `sensor.sh10rt_daily_pv_generation_battery_discharge` | kWh | Daily PV generation & battery discharge | `sensor.daily_pv_generation_battery_discharge` |
| Daily battery charge energy | `sensor.sh10rt_daily_battery_charge_energy` | kWh | Daily battery charge **←** | `sensor.daily_battery_charge` |
| Daily battery charge energy from PV | `sensor.sh10rt_daily_battery_charge_energy_from_pv` | kWh | Daily battery charge from PV **←** | `sensor.daily_battery_charge_from_pv` |
| Daily battery discharge energy | `sensor.sh10rt_daily_battery_discharge_energy` | kWh | Daily battery discharge **←** | `sensor.daily_battery_discharge` |
| Firmware version part 4 (Sungrow battery) | `sensor.sh10rt_firmware_version_part_4_sungrow_battery` |  | Sungrow Version 4 (Sungrow Battery) **←** | `sensor.sungrow_version_4_sungrow_battery` |
| Total PV generation & battery discharge | `sensor.sh10rt_total_pv_generation_battery_discharge` | kWh | Total PV generation & battery discharge | `sensor.total_pv_generation_battery_discharge` |
| Total battery charge energy | `sensor.sh10rt_total_battery_charge_energy` | kWh | Total battery charge **←** | `sensor.total_battery_charge` |
| Total battery charge energy from PV | `sensor.sh10rt_total_battery_charge_energy_from_pv` | kWh | Total battery charge from PV **←** | `sensor.total_battery_charge_from_pv` |
| Total battery discharge energy | `sensor.sh10rt_total_battery_discharge_energy` | kWh | Total battery discharge **←** | `sensor.total_battery_discharge` |

### The grid (16)

| Name | Entity id | Unit | Legacy name | Legacy entity id |
| --- | --- | --- | --- | --- |
| Daily exported energy | `sensor.sh10rt_daily_exported_energy` | kWh | Daily exported energy | `sensor.daily_exported_energy` |
| Daily imported energy | `sensor.sh10rt_daily_imported_energy` | kWh | Daily imported energy | `sensor.daily_imported_energy` |
| Export power | `sensor.sh10rt_export_power` | W | Export power | `sensor.export_power` |
| Export power limit | `number.sh10rt_export_power_limit` | W | Export power limit | `number.export_power_limit` |
| Export power limit max | `sensor.sh10rt_export_power_limit_max` | W | Export power limit max | `sensor.export_power_limit_max` |
| Export power limit min | `sensor.sh10rt_export_power_limit_min` | W | Export power limit min | `sensor.export_power_limit_min` |
| Export power limit mode | `switch.sh10rt_export_power_limit_mode` |  | Export power limit **←** | `switch.export_power_limit` |
| Exporting power | `binary_sensor.sh10rt_exporting_power` |  | Exporting Power **←** | `binary_sensor.exporting_power` |
| Exporting power (delayed) | `binary_sensor.sh10rt_exporting_power_delayed` |  | Exporting Power (delay) **←** | `binary_sensor.exporting_power_delay` |
| Grid frequency | `sensor.sh10rt_grid_frequency` | Hz | Grid frequency | `sensor.grid_frequency` |
| Grid-side fault | `sensor.sh10rt_grid_side_fault` |  |  |  |
| Import power | `sensor.sh10rt_import_power` | W | Import power | `sensor.import_power` |
| Importing power | `binary_sensor.sh10rt_importing_power` |  | Importing Power **←** | `binary_sensor.importing_power` |
| Importing power (delayed) | `binary_sensor.sh10rt_importing_power_delayed` |  | Importing Power (delay) **←** | `binary_sensor.importing_power_delay` |
| Total exported energy | `sensor.sh10rt_total_exported_energy` | kWh | Total exported energy | `sensor.total_exported_energy` |
| Total imported energy | `sensor.sh10rt_total_imported_energy` | kWh | Total imported energy | `sensor.total_imported_energy` |

### The house (16)

| Name | Entity id | Unit | Legacy name | Legacy entity id |
| --- | --- | --- | --- | --- |
| Corrected load power | `sensor.sh10rt_corrected_load_power` | W |  |  |
| Daily consumed energy | `sensor.sh10rt_daily_consumed_energy` | kWh | Daily consumed energy | `sensor.daily_consumed_energy` |
| Daily consumed energy (smoothed) | `sensor.sh10rt_daily_consumed_energy_smoothed` | kWh | Daily consumed energy (filtered) **←** | `sensor.daily_consumed_energy_filtered` |
| Daily direct energy consumption | `sensor.sh10rt_daily_direct_energy_consumption` | kWh | Daily direct energy consumption | `sensor.daily_direct_energy_consumption` |
| Direct consumption this month | `sensor.sh10rt_direct_consumption_this_month` | kWh |  |  |
| Direct consumption this year | `sensor.sh10rt_direct_consumption_this_year` | kWh |  |  |
| Load control | `switch.sh10rt_load_control` |  | Load adjustment mode **←** | `switch.load_adjustment_mode` |
| Load control mode | `select.sh10rt_load_control_mode` |  | Load adjustment mode **←** | `select.load_adjustment_mode` |
| Load power | `sensor.sh10rt_load_power` | W | Load power | `sensor.load_power` |
| Negative load power | `binary_sensor.sh10rt_negative_load_power` |  | Negative Load Power **←** | `binary_sensor.negative_load_power` |
| Negative load power (delayed) | `binary_sensor.sh10rt_negative_load_power_delayed` |  | Negative Load Power (delay) **←** | `binary_sensor.negative_load_power_delay` |
| Positive load power | `binary_sensor.sh10rt_positive_load_power` |  | Positive Load Power **←** | `binary_sensor.positive_load_power` |
| Positive load power (delayed) | `binary_sensor.sh10rt_positive_load_power_delayed` |  | Positive Load Power (delay) **←** | `binary_sensor.positive_load_power_delay` |
| Self-consumption of today | `sensor.sh10rt_self_consumption_of_today` | % |  |  |
| Total consumed energy | `sensor.sh10rt_total_consumed_energy` | kWh | Total consumed energy | `sensor.total_consumed_energy` |
| Total direct energy consumption | `sensor.sh10rt_total_direct_energy_consumption` | kWh | Total direct energy consumption | `sensor.total_direct_energy_consumption` |

### The meter (14)

| Name | Entity id | Unit | Legacy name | Legacy entity id |
| --- | --- | --- | --- | --- |
| Meter active power | `sensor.sh10rt_meter_active_power` | W | Meter active power | `sensor.meter_active_power` |
| Meter channel 2 phase A active power | `sensor.sh10rt_meter_channel_2_phase_a_active_power` | W |  |  |
| Meter channel 2 phase B active power | `sensor.sh10rt_meter_channel_2_phase_b_active_power` | W |  |  |
| Meter channel 2 phase C active power | `sensor.sh10rt_meter_channel_2_phase_c_active_power` | W |  |  |
| Meter channel 2 total active power | `sensor.sh10rt_meter_channel_2_total_active_power` | W |  |  |
| Meter phase A active power | `sensor.sh10rt_meter_phase_a_active_power` | W | Meter phase A active power | `sensor.meter_phase_a_active_power` |
| Meter phase A current | `sensor.sh10rt_meter_phase_a_current` | A | Meter phase A current | `sensor.meter_phase_a_current` |
| Meter phase A voltage | `sensor.sh10rt_meter_phase_a_voltage` | V | Meter phase A voltage | `sensor.meter_phase_a_voltage` |
| Meter phase B active power | `sensor.sh10rt_meter_phase_b_active_power` | W | Meter phase B active power | `sensor.meter_phase_b_active_power` |
| Meter phase B current | `sensor.sh10rt_meter_phase_b_current` | A | Meter phase B current | `sensor.meter_phase_b_current` |
| Meter phase B voltage | `sensor.sh10rt_meter_phase_b_voltage` | V | Meter phase B voltage | `sensor.meter_phase_b_voltage` |
| Meter phase C active power | `sensor.sh10rt_meter_phase_c_active_power` | W | Meter phase C active power | `sensor.meter_phase_c_active_power` |
| Meter phase C current | `sensor.sh10rt_meter_phase_c_current` | A | Meter phase C current | `sensor.meter_phase_c_current` |
| Meter phase C voltage | `sensor.sh10rt_meter_phase_c_voltage` | V | Meter phase C voltage | `sensor.meter_phase_c_voltage` |

## SBR battery (34)

A device of its own under the inverter, named after the pack its capacity matches, `Battery` where none does. Per-module entities exist for the fitted modules only, and are disabled by default. Ids shown for `SBR096`.

### Everything (34)

| Name | Entity id | Unit | Legacy name | Legacy entity id |
| --- | --- | --- | --- | --- |
| Cell voltage spread | `sensor.sbr096_cell_voltage_spread` | mV |  |  |
| Coolest module | `sensor.sbr096_coolest_module` |  |  |  |
| Coolest module temperature | `sensor.sbr096_coolest_module_temperature` | °C |  |  |
| Highest cell module | `sensor.sbr096_highest_cell_module` |  |  |  |
| Highest cell number | `sensor.sbr096_highest_cell_number` |  |  |  |
| Highest cell voltage | `sensor.sbr096_highest_cell_voltage` | V |  |  |
| Lowest cell module | `sensor.sbr096_lowest_cell_module` |  |  |  |
| Lowest cell number | `sensor.sbr096_lowest_cell_number` |  |  |  |
| Lowest cell voltage | `sensor.sbr096_lowest_cell_voltage` | V |  |  |
| Module 1 highest cell voltage | `sensor.sbr096_module_1_highest_cell_voltage` | V |  |  |
| Module 1 lowest cell voltage | `sensor.sbr096_module_1_lowest_cell_voltage` | V |  |  |
| Module 2 highest cell voltage | `sensor.sbr096_module_2_highest_cell_voltage` | V |  |  |
| Module 2 lowest cell voltage | `sensor.sbr096_module_2_lowest_cell_voltage` | V |  |  |
| Module 3 highest cell voltage | `sensor.sbr096_module_3_highest_cell_voltage` | V |  |  |
| Module 3 lowest cell voltage | `sensor.sbr096_module_3_lowest_cell_voltage` | V |  |  |
| Module 4 highest cell voltage | `sensor.sbr096_module_4_highest_cell_voltage` | V |  |  |
| Module 4 lowest cell voltage | `sensor.sbr096_module_4_lowest_cell_voltage` | V |  |  |
| Module 5 highest cell voltage | `sensor.sbr096_module_5_highest_cell_voltage` | V |  |  |
| Module 5 lowest cell voltage | `sensor.sbr096_module_5_lowest_cell_voltage` | V |  |  |
| Module 6 highest cell voltage | `sensor.sbr096_module_6_highest_cell_voltage` | V |  |  |
| Module 6 lowest cell voltage | `sensor.sbr096_module_6_lowest_cell_voltage` | V |  |  |
| Module 7 highest cell voltage | `sensor.sbr096_module_7_highest_cell_voltage` | V |  |  |
| Module 7 lowest cell voltage | `sensor.sbr096_module_7_lowest_cell_voltage` | V |  |  |
| Module 8 highest cell voltage | `sensor.sbr096_module_8_highest_cell_voltage` | V |  |  |
| Module 8 lowest cell voltage | `sensor.sbr096_module_8_lowest_cell_voltage` | V |  |  |
| Pack current | `sensor.sbr096_pack_current` | A |  |  |
| Pack level | `sensor.sbr096_pack_level` | % |  |  |
| Pack state of health | `sensor.sbr096_pack_state_of_health` | % |  |  |
| Pack temperature | `sensor.sbr096_pack_temperature` | °C |  |  |
| Pack total charge energy | `sensor.sbr096_pack_total_charge_energy` | kWh |  |  |
| Pack total discharge energy | `sensor.sbr096_pack_total_discharge_energy` | kWh |  |  |
| Pack voltage | `sensor.sbr096_pack_voltage` | V |  |  |
| Warmest module | `sensor.sbr096_warmest_module` |  |  |  |
| Warmest module temperature | `sensor.sbr096_warmest_module_temperature` | °C |  |  |

## Wallbox (21)

A device of its own under the inverter, named after the model it reports, `Wallbox` where it reports none. Ids shown for `AC22E-01`.

### Everything (21)

| Name | Entity id | Unit | Legacy name | Legacy entity id |
| --- | --- | --- | --- | --- |
| Available current | `sensor.ac22e_01_available_current` | A |  |  |
| Charging | `binary_sensor.ac22e_01_charging` |  |  |  |
| Charging power | `sensor.ac22e_01_charging_power` | W |  |  |
| Charging status | `sensor.ac22e_01_charging_status` |  |  |  |
| Configured output current | `sensor.ac22e_01_configured_output_current` | A |  |  |
| Control pilot voltage | `sensor.ac22e_01_control_pilot_voltage` | V |  |  |
| Enabled | `binary_sensor.ac22e_01_enabled` |  |  |  |
| Firmware version | `sensor.ac22e_01_firmware_version` |  |  |  |
| Lifetime energy | `sensor.ac22e_01_lifetime_energy` | Wh |  |  |
| Maximum charging power | `sensor.ac22e_01_maximum_charging_power` | W |  |  |
| Minimum charging power | `sensor.ac22e_01_minimum_charging_power` | W |  |  |
| Phase A current | `sensor.ac22e_01_phase_a_current` | A |  |  |
| Phase A voltage | `sensor.ac22e_01_phase_a_voltage` | V |  |  |
| Phase B current | `sensor.ac22e_01_phase_b_current` | A |  |  |
| Phase B voltage | `sensor.ac22e_01_phase_b_voltage` | V |  |  |
| Phase C current | `sensor.ac22e_01_phase_c_current` | A |  |  |
| Phase C voltage | `sensor.ac22e_01_phase_c_voltage` | V |  |  |
| Phase mode | `sensor.ac22e_01_phase_mode` |  |  |  |
| Rated current | `sensor.ac22e_01_rated_current` | A |  |  |
| Session energy | `sensor.ac22e_01_session_energy` | Wh |  |  |
| Start mode | `sensor.ac22e_01_start_mode` |  |  |  |

## SG string inverter (61)

An entry of its own, never beside a hybrid. Trackers and phases exist only where the model serves them, so this is every one a model can have. Ids shown for `SG5.0RS`.

### Everything (61)

| Name | Entity id | Unit | Legacy name | Legacy entity id |
| --- | --- | --- | --- | --- |
| Bus voltage | `sensor.sg5_0rs_bus_voltage` | V |  |  |
| Daily PV generation | `sensor.sg5_0rs_daily_pv_generation` | kWh |  |  |
| Daily direct energy consumption | `sensor.sg5_0rs_daily_direct_energy_consumption` | kWh |  |  |
| Daily exported energy | `sensor.sg5_0rs_daily_exported_energy` | kWh |  |  |
| Daily imported energy | `sensor.sg5_0rs_daily_imported_energy` | kWh |  |  |
| Daily running time | `sensor.sg5_0rs_daily_running_time` | min |  |  |
| Fault reported | `binary_sensor.sg5_0rs_fault_reported` |  |  |  |
| Grid frequency | `sensor.sg5_0rs_grid_frequency` | Hz |  |  |
| Internal temperature | `sensor.sg5_0rs_internal_temperature` | °C |  |  |
| Load power | `sensor.sg5_0rs_load_power` | W |  |  |
| MPPT1 current | `sensor.sg5_0rs_mppt1_current` | A |  |  |
| MPPT1 voltage | `sensor.sg5_0rs_mppt1_voltage` | V |  |  |
| MPPT10 current | `sensor.sg5_0rs_mppt10_current` | A |  |  |
| MPPT10 voltage | `sensor.sg5_0rs_mppt10_voltage` | V |  |  |
| MPPT11 current | `sensor.sg5_0rs_mppt11_current` | A |  |  |
| MPPT11 voltage | `sensor.sg5_0rs_mppt11_voltage` | V |  |  |
| MPPT12 current | `sensor.sg5_0rs_mppt12_current` | A |  |  |
| MPPT12 voltage | `sensor.sg5_0rs_mppt12_voltage` | V |  |  |
| MPPT2 current | `sensor.sg5_0rs_mppt2_current` | A |  |  |
| MPPT2 voltage | `sensor.sg5_0rs_mppt2_voltage` | V |  |  |
| MPPT3 current | `sensor.sg5_0rs_mppt3_current` | A |  |  |
| MPPT3 voltage | `sensor.sg5_0rs_mppt3_voltage` | V |  |  |
| MPPT4 current | `sensor.sg5_0rs_mppt4_current` | A |  |  |
| MPPT4 voltage | `sensor.sg5_0rs_mppt4_voltage` | V |  |  |
| MPPT5 current | `sensor.sg5_0rs_mppt5_current` | A |  |  |
| MPPT5 voltage | `sensor.sg5_0rs_mppt5_voltage` | V |  |  |
| MPPT6 current | `sensor.sg5_0rs_mppt6_current` | A |  |  |
| MPPT6 voltage | `sensor.sg5_0rs_mppt6_voltage` | V |  |  |
| MPPT7 current | `sensor.sg5_0rs_mppt7_current` | A |  |  |
| MPPT7 voltage | `sensor.sg5_0rs_mppt7_voltage` | V |  |  |
| MPPT8 current | `sensor.sg5_0rs_mppt8_current` | A |  |  |
| MPPT8 voltage | `sensor.sg5_0rs_mppt8_voltage` | V |  |  |
| MPPT9 current | `sensor.sg5_0rs_mppt9_current` | A |  |  |
| MPPT9 voltage | `sensor.sg5_0rs_mppt9_voltage` | V |  |  |
| Meter active power | `sensor.sg5_0rs_meter_active_power` | W |  |  |
| Meter phase A power | `sensor.sg5_0rs_meter_phase_a_power` | W |  |  |
| Meter phase B power | `sensor.sg5_0rs_meter_phase_b_power` | W |  |  |
| Meter phase C power | `sensor.sg5_0rs_meter_phase_c_power` | W |  |  |
| Monthly PV generation | `sensor.sg5_0rs_monthly_pv_generation` | kWh |  |  |
| Negative voltage to ground | `sensor.sg5_0rs_negative_voltage_to_ground` | V |  |  |
| Phase A current | `sensor.sg5_0rs_phase_a_current` | A |  |  |
| Phase A voltage | `sensor.sg5_0rs_phase_a_voltage` | V |  |  |
| Phase B current | `sensor.sg5_0rs_phase_b_current` | A |  |  |
| Phase B voltage | `sensor.sg5_0rs_phase_b_voltage` | V |  |  |
| Phase C current | `sensor.sg5_0rs_phase_c_current` | A |  |  |
| Phase C voltage | `sensor.sg5_0rs_phase_c_voltage` | V |  |  |
| Power factor | `sensor.sg5_0rs_power_factor` |  |  |  |
| Power limit | `sensor.sg5_0rs_power_limit` | % |  |  |
| Power limitation | `sensor.sg5_0rs_power_limitation` |  |  |  |
| Reactive power | `sensor.sg5_0rs_reactive_power` | var |  |  |
| Run read only diagnosis | `button.sg5_0rs_run_read_only_diagnosis` |  |  |  |
| Total DC power | `sensor.sg5_0rs_total_dc_power` | W |  |  |
| Total PV generation | `sensor.sg5_0rs_total_pv_generation` | kWh |  |  |
| Total PV generation (precise) | `sensor.sg5_0rs_total_pv_generation_precise` | kWh |  |  |
| Total active power | `sensor.sg5_0rs_total_active_power` | W |  |  |
| Total apparent power | `sensor.sg5_0rs_total_apparent_power` | VA |  |  |
| Total direct energy consumption | `sensor.sg5_0rs_total_direct_energy_consumption` | kWh |  |  |
| Total exported energy | `sensor.sg5_0rs_total_exported_energy` | kWh |  |  |
| Total imported energy | `sensor.sg5_0rs_total_imported_energy` | kWh |  |  |
| Total running time | `sensor.sg5_0rs_total_running_time` | h |  |  |
| Work state | `sensor.sg5_0rs_work_state` |  |  |  |

## Legacy mode only (20)

Not created in modern mode. Each is a second copy of something a user
already has, so the column on the right is where the reading went instead,
with its modern-mode id.

| Name | Legacy entity id | Replaced in modern mode by |
| --- | --- | --- |
| Active power limitation raw | `sensor.active_power_limitation_raw` | Active power limitation (`binary_sensor.sh10rt_active_power_limitation`) |
| Backup mode raw | `sensor.backup_mode_raw` | Backup mode (`switch.sh10rt_backup_mode`) |
| Battery charging start power | `sensor.battery_charging_start_power` | Battery charging start power (`number.sh10rt_battery_charging_start_power`) |
| Battery discharging start power | `sensor.battery_discharging_start_power` | Battery discharging start power (`number.sh10rt_battery_discharging_start_power`) |
| Battery forced charge/discharge command raw | `sensor.battery_forced_charge_discharge_cmd_raw` | Battery forced charge/discharge (`select.sh10rt_battery_forced_charge_discharge`) |
| Battery forced charge/discharge power | `sensor.battery_forced_charge_discharge_power` | Battery forced charge/discharge power (`number.sh10rt_battery_forced_charge_discharge_power`) |
| Battery max SoC | `sensor.battery_max_soc` | Battery max SoC (`number.sh10rt_battery_max_soc`) |
| Battery max charging power | `sensor.battery_max_charge_power` | Battery max charging power (`number.sh10rt_battery_max_charging_power`) |
| Battery max discharging power | `sensor.battery_max_discharge_power` | Battery max discharging power (`number.sh10rt_battery_max_discharging_power`) |
| Battery min SoC | `sensor.battery_min_soc` | Battery min SoC (`number.sh10rt_battery_min_soc`) |
| Battery reserved SoC for backup | `sensor.battery_reserved_soc_for_backup` | Battery reserved SoC for backup (`number.sh10rt_battery_reserved_soc_for_backup`) |
| EMS mode selection raw | `sensor.ems_mode_selection_raw` | EMS mode (`select.sh10rt_ems_mode`) |
| Export power limit | `sensor.export_power_limit` | Export power limit (`number.sh10rt_export_power_limit`) |
| Export power limit mode raw | `sensor.export_power_limit_mode_raw` | Export power limit mode (`switch.sh10rt_export_power_limit_mode`) |
| Export power raw | `sensor.export_power_raw` | Export power (`sensor.sh10rt_export_power`) |
| Load control mode enable raw | `sensor.load_adjustment_mode_enable_raw` | Load control (`switch.sh10rt_load_control`) |
| Load control mode selection raw | `sensor.load_adjustment_mode_selection_raw` | Load control mode (`select.sh10rt_load_control_mode`) |
| PV generation cut raw | (not in the YAML) | PV generation cut (`binary_sensor.sh10rt_pv_generation_cut`) |
| PV power limitation raw | (not in the YAML) | PV power limitation (`binary_sensor.sh10rt_pv_power_limitation`) |
| Running state raw | `sensor.running_state_raw` | Running state (`sensor.sh10rt_running_state`) |

## Not ported (3)

Entities of the YAML package that the integration does not create. Why, and
what replaces each, is in [integration_migration.md](integration_migration.md),
which also covers the package's scenes and automations: they are not entities
of the integration, and go when the file goes.

| Legacy entity id | Legacy name |
| --- | --- |
| `button.start_inverter` | Start inverter |
| `button.stop_inverter` | Stop inverter |
| `switch.sungrow_dashboard_enable_danger_mode` | Sungrow dashboard enable danger mode |
