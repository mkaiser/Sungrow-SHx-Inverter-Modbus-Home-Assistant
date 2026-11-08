# The entity names

**335 entities** that modern mode can create (Hybrid inverter 196, SBR battery 34, Wallbox 21, SG string inverter 84).

The **entity id**
column is what a dashboard and years of history are keyed to, and a name supplies
it -- but only at creation. Rename later and anybody who already has the entity
keeps the id they were born with; only the label changes. So the cost of a late
rename is **divergence** between houses set up before and after, not lost
history, and where that matters a registry rename moves the early one across.

Each id begins with its **device's name**, which differs between houses; one
real model stands in for each device below. **YAML** and **YAML entity id** are
what the YAML package calls the same entity: a user who migrates keeps that
id, and a fresh install gets the entity id. A **←** marks a YAML name the
**English** one differs from.

**Datasheet** is Sungrow's own name for the register, with its number: the hybrid's
*Communication Protocol of Residential Hybrid Inverter* V1.1.11, the SG's *Modbus
Register Protokoll* V1.1.58 (`scripts/generate/tables/datasheet_names.json`). Empty
for a derived entity and for the battery and wallbox, which have no Sungrow
datasheet here.

**Deutsch** is the German name for each, decided beside the English one and
shipped in `translations/de.json`; entity ids stay English in every
language. The names live in `GERMAN` in
`scripts/generate/tables/naming.py`, with the German word each recurring idea
must use (`GERMAN_TERMS`). Every other text in `strings.json` -- the setup and
options flows, repairs, actions and error messages -- is in
[text_translation_review.md](../plans/text_translation_review.md), English above German.

A name with an open question has it **To discuss** under its table: what the
entity is and the names to choose from (`NAME_DISCUSSION` in `naming.py`).

A further 21 sensors exist **only in legacy mode** and are listed at the
end. Their ids are the YAML package's, kept so that history keyed to them
carries on, and modern mode replaces each with something better.


## Hybrid inverter (196)

The inverter's own device, named after the model unless the owner named it. Ids shown for `SH10RT`.

### Actions (2)

| Datasheet | YAML | English | Deutsch | Entity id | YAML entity id | Unit |
| --- | --- | --- | --- | --- | --- | --- |
|  |  | Diagnosis: run extended | Diagnose: erweitert ausführen | `button.sh10rt_diagnosis_run_extended` |  |  |
|  |  | Diagnosis: run read-only | Diagnose: nur lesend ausführen | `button.sh10rt_diagnosis_run_read_only` |  |  |

### Backup power (12)

| Datasheet | YAML | English | Deutsch | Entity id | YAML entity id | Unit |
| --- | --- | --- | --- | --- | --- | --- |
| Backup Frequency (5734) |  | Backup frequency | Backup Frequenz | `sensor.sh10rt_backup_frequency` |  | Hz |
| Off-grid option (13075) | Backup Mode **←** | Backup mode | Backup-Modus | `switch.sh10rt_backup_mode` | `switch.backup_mode` |  |
| Phase A Backup Current (5720) |  | Backup phase A current | Backup Phase A Strom | `sensor.sh10rt_backup_phase_a_current` |  | A |
| Phase A Backup Power (5723) | Backup phase A power | Backup phase A power | Backup Phase A Leistung | `sensor.sh10rt_backup_phase_a_power` | `sensor.backup_phase_a_power` | W |
| Phase A Backup Voltage (5731) |  | Backup phase A voltage | Backup Phase A Spannung | `sensor.sh10rt_backup_phase_a_voltage` |  | V |
| Phase B Backup Current (5721) |  | Backup phase B current | Backup Phase B Strom | `sensor.sh10rt_backup_phase_b_current` |  | A |
| Phase B Backup Power (5724) | Backup phase B power | Backup phase B power | Backup Phase B Leistung | `sensor.sh10rt_backup_phase_b_power` | `sensor.backup_phase_b_power` | W |
| Phase B Backup Voltage (5732) |  | Backup phase B voltage | Backup Phase B Spannung | `sensor.sh10rt_backup_phase_b_voltage` |  | V |
| Phase C Backup Current (5722) |  | Backup phase C current | Backup Phase C Strom | `sensor.sh10rt_backup_phase_c_current` |  | A |
| Phase C Backup Power (5725) | Backup phase C power | Backup phase C power | Backup Phase C Leistung | `sensor.sh10rt_backup_phase_c_power` | `sensor.backup_phase_c_power` | W |
| Phase C Backup Voltage (5733) |  | Backup phase C voltage | Backup Phase C Spannung | `sensor.sh10rt_backup_phase_c_voltage` |  | V |
| Total Backup Power (5726) | Total backup power | Total backup power | Backup Gesamtleistung | `sensor.sh10rt_total_backup_power` | `sensor.total_backup_power` | W |

### Control (17)

| Datasheet | YAML | English | Deutsch | Entity id | YAML entity id | Unit |
| --- | --- | --- | --- | --- | --- | --- |
|  |  | Active power limitation | Wirkleistungsbegrenzung | `binary_sensor.sh10rt_active_power_limitation` |  |  |
| Active Power Limit Ratio (13090) | Active power limitation ratio raw **←** | Active power limitation ratio | Wirkleistungsbegrenzung prozentual | `sensor.sh10rt_active_power_limitation_ratio` | `sensor.active_power_limitation_ratio_raw` | % |
| EMS mode selection (13050) | EMS mode | EMS mode | EMS-Modus | `select.sh10rt_ems_mode` | `select.ems_mode` |  |
| Feed-in Limitation Ratio (13088) |  | Feed-in limit ratio | Einspeiselimit prozentual | `sensor.sh10rt_feed_in_limit_ratio` |  | % |
| Forced Charging Valid Time (33209) |  | Forced charging days | Zwangsladung Tage | `select.sh10rt_forced_charging_days` |  |  |
| Forced Charging End Time 1(h) (33212) |  | Forced charging end 1 | Zwangsladung Ende 1 | `time.sh10rt_forced_charging_end_1` |  |  |
| Forced Charging End Time 2(h) (33217) |  | Forced charging end 2 | Zwangsladung Ende 2 | `time.sh10rt_forced_charging_end_2` |  |  |
| Forced Charging (33208) |  | Forced charging schedule | Zwangsladung Zeitplan | `switch.sh10rt_forced_charging_schedule` |  |  |
| Forced Charging Start Time 1(h) (33210) |  | Forced charging start 1 | Zwangsladung Start 1 | `time.sh10rt_forced_charging_start_1` |  |  |
| Forced Charging Start Time 2(h) (33215) |  | Forced charging start 2 | Zwangsladung Start 2 | `time.sh10rt_forced_charging_start_2` |  |  |
| Forced Charging Target SOC1 (33214) |  | Forced charging target SoC 1 | Zwangsladung Ziel-Ladezustand 1 | `number.sh10rt_forced_charging_target_soc_1` |  | % |
| Forced Charging Target SOC 2 (33219) |  | Forced charging target SoC 2 | Zwangsladung Ziel-Ladezustand 2 | `number.sh10rt_forced_charging_target_soc_2` |  | % |
|  |  | Weekday discharge window 1 | Entladefenster Werktag 1 | `sensor.sh10rt_weekday_discharge_window_1` |  |  |
|  |  | Weekday discharge window 2 | Entladefenster Werktag 2 | `sensor.sh10rt_weekday_discharge_window_2` |  |  |
|  |  | Weekend discharge | Entladung am Wochenende | `binary_sensor.sh10rt_weekend_discharge` |  |  |
|  |  | Weekend discharge window 1 | Entladefenster Wochenende 1 | `sensor.sh10rt_weekend_discharge_window_1` |  |  |
|  |  | Weekend discharge window 2 | Entladefenster Wochenende 2 | `sensor.sh10rt_weekend_discharge_window_2` |  |  |

### Everything else (5)

| Datasheet | YAML | English | Deutsch | Entity id | YAML entity id | Unit |
| --- | --- | --- | --- | --- | --- | --- |
| Forced Startup Under Low SOC Standby (13017) |  | Forced startup under low SoC | Zwangsstart bei niedrigem Ladezustand | `switch.sh10rt_forced_startup_under_low_soc` |  |  |
| Power factor (5035) | Power factor | Power factor | Leistungsfaktor | `sensor.sh10rt_power_factor` | `sensor.power_factor` |  |
| Power Flow Status (13001) | Power Flow Status **←** | Power flow code | Leistungsfluss Code | `sensor.sh10rt_power_flow_code` | `sensor.power_flow_status` |  |
|  | Sungrow inverter state **←** | Running state | Betriebszustand | `sensor.sh10rt_running_state` | `sensor.sungrow_inverter_state` |  |
|  |  | Shutdown inverter when limited to 0 % power | Abschalten bei Begrenzung auf 0 % Leistung | `binary_sensor.sh10rt_shutdown_inverter_when_limited_to_0_power` |  |  |

### Faults and alarms (9)

| Datasheet | YAML | English | Deutsch | Entity id | YAML entity id | Unit |
| --- | --- | --- | --- | --- | --- | --- |
|  |  | Any alarm | Alarm aktiv | `binary_sensor.sh10rt_any_alarm` |  |  |
| BDC-side fault (13062) |  | BDC-side fault | BDC-seitiger Fehler | `sensor.sh10rt_bdc_side_fault` |  |  |
| BDC-side permanent fault (13064) |  | BDC-side permanent fault | BDC-seitiger permanenter Fehler | `sensor.sh10rt_bdc_side_permanent_fault` |  |  |
| DC-side fault (13058) |  | DC-side fault | DC-seitiger Fehler | `sensor.sh10rt_dc_side_fault` |  |  |
| Inverter alarm (13050) |  | Device alarm | Gerätealarm | `sensor.sh10rt_device_alarm` |  |  |
|  |  | Fault reported | Fehler gemeldet | `binary_sensor.sh10rt_fault_reported` |  |  |
| Permanent fault (13060) |  | Permanent fault | Permanenter Fehler | `sensor.sh10rt_permanent_fault` |  |  |
| System fault 1 (13054) |  | System fault 1 | Systemfehler 1 | `sensor.sh10rt_system_fault_1` |  |  |
| System fault 2 (13056) |  | System fault 2 | Systemfehler 2 | `sensor.sh10rt_system_fault_2` |  |  |

### Identity and firmware (11)

| Datasheet | YAML | English | Deutsch | Entity id | YAML entity id | Unit |
| --- | --- | --- | --- | --- | --- | --- |
| Certification version of ARM Software (4954) | Sungrow Arm Software **←** | ARM software version | ARM-Software-Version | `sensor.sh10rt_arm_software_version` | `sensor.sungrow_arm_software` |  |
| Communication Module Firmware Information (13265) | Communication Module Firmware Version **←** | Communication module firmware version | Firmware-Version Kommunikationsmodul | `sensor.sh10rt_communication_module_firmware_version` | `sensor.communication_module_firmware_version` |  |
| Certification version of DSP Software (4969) | Sungrow DSP Software **←** | DSP software version | DSP-Software-Version | `sensor.sh10rt_dsp_software_version` | `sensor.sungrow_dsp_software` |  |
|  | Sungrow device type **←** | Device type | Gerätetyp | `sensor.sh10rt_device_type` | `sensor.sungrow_device_type` |  |
| Device type code (5000) | Sungrow device type code **←** | Device type code | Gerätetypcode | `sensor.sh10rt_device_type_code` | `sensor.sungrow_device_type_code` |  |
| Inverter Firmware Information (13250) | Inverter Firmware Version **←** | Firmware version | Firmware-Version | `sensor.sh10rt_firmware_version` | `sensor.inverter_firmware_version` |  |
| *not in the datasheet* (2582) | Sungrow Version 1 **←** | Firmware version part 1 | Firmware-Version Teil 1 | `sensor.sh10rt_firmware_version_part_1` | `sensor.sungrow_version_1` |  |
| *not in the datasheet* (2597) | Sungrow Version 2 **←** | Firmware version part 2 | Firmware-Version Teil 2 | `sensor.sh10rt_firmware_version_part_2` | `sensor.sungrow_version_2` |  |
| *not in the datasheet* (2613) | Sungrow Version 3 **←** | Firmware version part 3 | Firmware-Version Teil 3 | `sensor.sh10rt_firmware_version_part_3` | `sensor.sungrow_version_3` |  |
| Protocol version (4952) | Sungrow Protocol Version **←** | Protocol version | Protokollversion | `sensor.sh10rt_protocol_version` | `sensor.sungrow_protocol_version` |  |
| *not in the datasheet* (4990) | Sungrow inverter serial **←** | Serial number | Seriennummer | `sensor.sh10rt_serial_number` | `sensor.sungrow_inverter_serial` |  |

### Per phase (9)

| Datasheet | YAML | English | Deutsch | Entity id | YAML entity id | Unit |
| --- | --- | --- | --- | --- | --- | --- |
| Phase A current (13031) | Phase A current | Phase A current | Phase A Strom | `sensor.sh10rt_phase_a_current` | `sensor.phase_a_current` | A |
|  | Phase A power | Phase A power | Phase A Leistung | `sensor.sh10rt_phase_a_power` | `sensor.phase_a_power` | W |
| A-B line voltage/phase A voltage (5019) | Phase A voltage | Phase A voltage | Phase A Spannung | `sensor.sh10rt_phase_a_voltage` | `sensor.phase_a_voltage` | V |
| Phase B current (13032) | Phase B current | Phase B current | Phase B Strom | `sensor.sh10rt_phase_b_current` | `sensor.phase_b_current` | A |
|  | Phase B power | Phase B power | Phase B Leistung | `sensor.sh10rt_phase_b_power` | `sensor.phase_b_power` | W |
| B-C line voltage/phase B voltage (5020) | Phase B voltage | Phase B voltage | Phase B Spannung | `sensor.sh10rt_phase_b_voltage` | `sensor.phase_b_voltage` | V |
| Phase C current (13033) | Phase C current | Phase C current | Phase C Strom | `sensor.sh10rt_phase_c_current` | `sensor.phase_c_current` | A |
|  | Phase C power | Phase C power | Phase C Leistung | `sensor.sh10rt_phase_c_power` | `sensor.phase_c_power` | W |
| C-A line voltage/phase voltage (5021) | Phase C voltage | Phase C voltage | Phase C Spannung | `sensor.sh10rt_phase_c_voltage` | `sensor.phase_c_voltage` | V |

### Power (5)

| Datasheet | YAML | English | Deutsch | Entity id | YAML entity id | Unit |
| --- | --- | --- | --- | --- | --- | --- |
| BDC rated power (5628) | BDC rated power | BDC rated power | BDC-Nennleistung | `sensor.sh10rt_bdc_rated_power` | `sensor.bdc_rated_power` | W |
| Nominal output power (5001) | Inverter rated output **←** | Rated output power | Nennausgangsleistung | `sensor.sh10rt_rated_output_power` | `sensor.inverter_rated_output` | W |
| Reactive power (5033) | Reactive power | Reactive power | Blindleistung | `sensor.sh10rt_reactive_power` | `sensor.reactive_power` | W |
| Total DC power (5017) | Total DC power **←** | Total PV input power | Gesamte PV-Eingangsleistung | `sensor.sh10rt_total_pv_input_power` | `sensor.total_dc_power` | W |
| Total active power (13034) | Total active power | Total active power | Gesamte Wirkleistung | `sensor.sh10rt_total_active_power` | `sensor.total_active_power` | W |

### Temperatures (1)

| Datasheet | YAML | English | Deutsch | Entity id | YAML entity id | Unit |
| --- | --- | --- | --- | --- | --- | --- |
| Inside Temperature (5008) | Inverter temperature **←** | Device temperature | Gerätetemperatur | `sensor.sh10rt_device_temperature` | `sensor.inverter_temperature` | °C |

### The PV trackers (30)

| Datasheet | YAML | English | Deutsch | Entity id | YAML entity id | Unit |
| --- | --- | --- | --- | --- | --- | --- |
| *not in the datasheet* (31211) |  | Cut PV generation | PV-Erzeugung abschalten | `switch.sh10rt_cut_pv_generation` |  |  |
| Daily PV Generation (13002) | Daily PV generation | Daily PV generation | Tägliche PV-Erzeugung | `sensor.sh10rt_daily_pv_generation` | `sensor.daily_pv_generation` | kWh |
| Daily export power from PV (13005) | Daily exported energy from PV | Daily exported energy from PV | Täglich aus PV eingespeiste Energie | `sensor.sh10rt_daily_exported_energy_from_pv` | `sensor.daily_exported_energy_from_pv` | kWh |
|  |  | Export from PV this month | Einspeisung aus PV diesen Monat | `sensor.sh10rt_export_from_pv_this_month` |  | kWh |
|  |  | Export from PV this year | Einspeisung aus PV dieses Jahr | `sensor.sh10rt_export_from_pv_this_year` |  | kWh |
| MPPT 1 Current (5012) | MPPT1 current | MPPT1 current | MPPT1 Strom | `sensor.sh10rt_mppt1_current` | `sensor.mppt1_current` | A |
|  |  | MPPT1 energy | MPPT1 Energie | `sensor.sh10rt_mppt1_energy` |  | kWh |
|  | MPPT1 power | MPPT1 power | MPPT1 Leistung | `sensor.sh10rt_mppt1_power` | `sensor.mppt1_power` | W |
| MPPT 1 Voltage (5011) | MPPT1 voltage | MPPT1 voltage | MPPT1 Spannung | `sensor.sh10rt_mppt1_voltage` | `sensor.mppt1_voltage` | V |
| MPPT 2 Current (5014) | MPPT2 current | MPPT2 current | MPPT2 Strom | `sensor.sh10rt_mppt2_current` | `sensor.mppt2_current` | A |
|  |  | MPPT2 energy | MPPT2 Energie | `sensor.sh10rt_mppt2_energy` |  | kWh |
|  | MPPT2 power | MPPT2 power | MPPT2 Leistung | `sensor.sh10rt_mppt2_power` | `sensor.mppt2_power` | W |
| MPPT 2 Voltage (5013) | MPPT2 voltage | MPPT2 voltage | MPPT2 Spannung | `sensor.sh10rt_mppt2_voltage` | `sensor.mppt2_voltage` | V |
| MPPT 3 Current (5016) | MPPT3 current | MPPT3 current | MPPT3 Strom | `sensor.sh10rt_mppt3_current` | `sensor.mppt3_current` | A |
|  |  | MPPT3 energy | MPPT3 Energie | `sensor.sh10rt_mppt3_energy` |  | kWh |
|  | MPPT3 power | MPPT3 power | MPPT3 Leistung | `sensor.sh10rt_mppt3_power` | `sensor.mppt3_power` | W |
| MPPT 3 Voltage (5015) | MPPT3 voltage | MPPT3 voltage | MPPT3 Spannung | `sensor.sh10rt_mppt3_voltage` | `sensor.mppt3_voltage` | V |
| MPPT 4 Current (5116) | MPPT4 current | MPPT4 current | MPPT4 Strom | `sensor.sh10rt_mppt4_current` | `sensor.mppt4_current` | A |
|  |  | MPPT4 energy | MPPT4 Energie | `sensor.sh10rt_mppt4_energy` |  | kWh |
|  | MPPT4 power | MPPT4 power | MPPT4 Leistung | `sensor.sh10rt_mppt4_power` | `sensor.mppt4_power` | W |
| MPPT 4 Voltage (5115) | MPPT4 voltage | MPPT4 voltage | MPPT4 Spannung | `sensor.sh10rt_mppt4_voltage` | `sensor.mppt4_voltage` | V |
|  | PV generating | PV generating | PV erzeugt | `binary_sensor.sh10rt_pv_generating` | `binary_sensor.pv_generating` |  |
|  | PV generating (delay) **←** | PV generating (delayed) | PV erzeugt (verzögert) | `binary_sensor.sh10rt_pv_generating_delayed` | `binary_sensor.pv_generating_delay` |  |
|  |  | PV generation cut | PV-Erzeugung abgeschaltet | `binary_sensor.sh10rt_pv_generation_cut` |  |  |
|  |  | PV generation this month | PV-Erzeugung diesen Monat | `sensor.sh10rt_pv_generation_this_month` |  | kWh |
|  |  | PV generation this year | PV-Erzeugung dieses Jahr | `sensor.sh10rt_pv_generation_this_year` |  | kWh |
|  |  | PV power limitation | PV-Leistungsbegrenzung | `binary_sensor.sh10rt_pv_power_limitation` |  |  |
| Total PV Generation (13003) | Total PV generation | Total PV generation | Gesamte PV-Erzeugung | `sensor.sh10rt_total_pv_generation` | `sensor.total_pv_generation` | kWh |
| Total export energy from PV (13006) | Total exported energy from PV | Total exported energy from PV | Gesamt aus PV eingespeiste Energie | `sensor.sh10rt_total_exported_energy_from_pv` | `sensor.total_exported_energy_from_pv` | kWh |
| Total DC power (5017) |  | Total site PV power | Gesamte PV-Leistung der Anlage | `sensor.sh10rt_total_site_pv_power` |  | W |

### The battery (47)

| Datasheet | YAML | English | Deutsch | Entity id | YAML entity id | Unit |
| --- | --- | --- | --- | --- | --- | --- |
| BMS alarm (13070) |  | BMS alarm | BMS-Alarm | `sensor.sh10rt_bms_alarm` |  |  |
| BMS alarm 2 (13078) |  | BMS alarm 2 | BMS-Alarm 2 | `sensor.sh10rt_bms_alarm_2` |  |  |
| BMS fault 1 (13074) |  | BMS fault 1 | BMS-Fehler 1 | `sensor.sh10rt_bms_fault_1` |  |  |
| BMS fault 2 (13076) |  | BMS fault 2 | BMS-Fehler 2 | `sensor.sh10rt_bms_fault_2` |  |  |
| Max. Charging Current (BMS) (5635) | BMS max. charging current **←** | BMS max charging current | BMS maximaler Ladestrom | `sensor.sh10rt_bms_max_charging_current` | `sensor.bms_max_charging_current` | A |
| Max. Discharging Current (BMS) (5636) | BMS max. discharging current **←** | BMS max discharging current | BMS maximaler Entladestrom | `sensor.sh10rt_bms_max_discharging_current` | `sensor.bms_max_discharging_current` | A |
| BMS protection (13072) |  | BMS protection | BMS-Schutz | `sensor.sh10rt_bms_protection` |  |  |
| Battery alarm (13068) |  | Battery alarm | Batteriealarm | `sensor.sh10rt_battery_alarm` |  |  |
| Battery Capacity- High precision (5639) | Battery capacity high precision | Battery capacity high precision | Batteriekapazität (hohe Genauigkeit) | `sensor.sh10rt_battery_capacity_high_precision` | `sensor.battery_capacity_high_precision` | kWh |
|  | Battery charge | Battery charge | Gespeicherte Energie | `sensor.sh10rt_battery_charge` | `sensor.battery_charge` | kWh |
|  | Battery charge (health-rated) | Battery charge (health-rated) | Gespeicherte Energie (gesundheitsbereinigt) | `sensor.sh10rt_battery_charge_health_rated` | `sensor.battery_charge_health_rated` | kWh |
|  | Battery charge (nominal) | Battery charge (nominal) | Gespeicherte Energie (nominal) | `sensor.sh10rt_battery_charge_nominal` | `sensor.battery_charge_nominal` | kWh |
|  | Battery charging | Battery charging | Batterie lädt | `binary_sensor.sh10rt_battery_charging` | `binary_sensor.battery_charging` |  |
|  | Battery charging (delay) **←** | Battery charging (delayed) | Batterie lädt (verzögert) | `binary_sensor.sh10rt_battery_charging_delayed` | `binary_sensor.battery_charging_delay` |  |
|  | Battery charging power | Battery charging power | Batterie-Ladeleistung | `sensor.sh10rt_battery_charging_power` | `sensor.battery_charging_power` | W |
|  | Battery charging power signed | Battery charging power signed | Batterie-Ladeleistung (mit Vorzeichen) | `sensor.sh10rt_battery_charging_power_signed` | `sensor.battery_charging_power_signed` | W |
| *not in the datasheet* (33149) | Battery charging start power | Battery charging start power | Batterie Ladestartleistung | `number.sh10rt_battery_charging_start_power` | `number.battery_charging_start_power` | W |
| Battery Current (5631) | Battery current | Battery current | Batteriestrom | `sensor.sh10rt_battery_current` | `sensor.battery_current` | A |
|  | Battery discharging | Battery discharging | Batterie entlädt | `binary_sensor.sh10rt_battery_discharging` | `binary_sensor.battery_discharging` |  |
|  | Battery discharging (delay) **←** | Battery discharging (delayed) | Batterie entlädt (verzögert) | `binary_sensor.sh10rt_battery_discharging_delayed` | `binary_sensor.battery_discharging_delay` |  |
|  | Battery discharging power | Battery discharging power | Batterie-Entladeleistung | `sensor.sh10rt_battery_discharging_power` | `sensor.battery_discharging_power` | W |
|  | Battery discharging power signed | Battery discharging power signed | Batterie-Entladeleistung (mit Vorzeichen) | `sensor.sh10rt_battery_discharging_power_signed` | `sensor.battery_discharging_power_signed` | W |
| *not in the datasheet* (33150) | Battery discharging start power | Battery discharging start power | Batterie Entladestartleistung | `number.sh10rt_battery_discharging_start_power` | `number.battery_discharging_start_power` | W |
| Battery fault (13066) |  | Battery fault | Batteriefehler | `sensor.sh10rt_battery_fault` |  |  |
| Battery Firmware Information (13280) | Battery Firmware Version **←** | Battery firmware version | Batterie Firmware-Version | `sensor.sh10rt_battery_firmware_version` | `sensor.battery_firmware_version` |  |
| Charge/discharge command (13051) | Battery forced charge discharge **←** | Battery forced charge/discharge | Batterie Zwangsladung/-entladung | `select.sh10rt_battery_forced_charge_discharge` | `select.battery_forced_charge_discharge` |  |
| Charge/discharge power (13052) | Battery forced charge discharge power **←** | Battery forced charge/discharge power | Batterie Zwangsladung/-entladung Leistung | `number.sh10rt_battery_forced_charge_discharge_power` | `number.battery_forced_charge_discharge_power` | W |
| Battery SOC (13023) | Battery level | Battery level | Batterie-Ladestand | `sensor.sh10rt_battery_level` | `sensor.battery_level` | % |
|  | Battery level (nominal) | Battery level (nominal) | Batterie-Ladestand (nominal) | `sensor.sh10rt_battery_level_nominal` | `sensor.battery_level_nominal` | % |
| Max. SOC (13058) | Battery Max Soc **←** | Battery max SoC | Maximaler Batterie-Ladezustand | `number.sh10rt_battery_max_soc` | `number.battery_max_soc` | % |
| Max. Charging Power (33047) | Battery max charge power **←** | Battery max charging power | Maximale Batterie-Ladeleistung | `number.sh10rt_battery_max_charging_power` | `number.battery_max_charge_power` | W |
| Max. Discharging Power (33048) | Battery max discharge power **←** | Battery max discharging power | Maximale Batterie-Entladeleistung | `number.sh10rt_battery_max_discharging_power` | `number.battery_max_discharge_power` | W |
| Min. SOC (13059) | Battery Min Soc **←** | Battery min SoC | Minimaler Batterie-Ladezustand | `number.sh10rt_battery_min_soc` | `number.battery_min_soc` | % |
| Battery power (5214) | Battery power | Battery power | Batterieleistung | `sensor.sh10rt_battery_power` | `sensor.battery_power` | W |
| Reserved SOC for backup (13100) | Battery Reserved SoC for Backup **←** | Battery reserved SoC for backup | Reservierter Batterie-Ladezustand für Backup | `number.sh10rt_battery_reserved_soc_for_backup` | `number.battery_reserved_soc_for_backup` | % |
| Battery SOH (13024) | Battery state of health | Battery state of health | Batterie-Gesundheitszustand | `sensor.sh10rt_battery_state_of_health` | `sensor.battery_state_of_health` | % |
| Battery temperature (13025) | Battery temperature | Battery temperature | Batterietemperatur | `sensor.sh10rt_battery_temperature` | `sensor.battery_temperature` | °C |
| Battery voltage (13020) | Battery voltage | Battery voltage | Batteriespannung | `sensor.sh10rt_battery_voltage` | `sensor.battery_voltage` | V |
| Daily Output Energy (5003) | Daily PV generation & battery discharge | Daily PV generation & battery discharge | Tägliche PV-Erzeugung und Batterieentladung | `sensor.sh10rt_daily_pv_generation_battery_discharge` | `sensor.daily_pv_generation_battery_discharge` | kWh |
| Daily Charge Energy (13040) | Daily battery charge **←** | Daily battery charge energy | Tägliche Batterie-Ladeenergie | `sensor.sh10rt_daily_battery_charge_energy` | `sensor.daily_battery_charge` | kWh |
| Daily battery charge energy from PV (13012) | Daily battery charge from PV **←** | Daily battery charge energy from PV | Tägliche Batterie-Ladeenergie aus PV | `sensor.sh10rt_daily_battery_charge_energy_from_pv` | `sensor.daily_battery_charge_from_pv` | kWh |
| Daily battery discharge energy (13026) | Daily battery discharge **←** | Daily battery discharge energy | Tägliche Batterie-Entladeenergie | `sensor.sh10rt_daily_battery_discharge_energy` | `sensor.daily_battery_discharge` | kWh |
| *not in the datasheet* (2629) | Sungrow Version 4 (Sungrow Battery) **←** | Firmware version part 4 (Sungrow battery) | Firmware-Version Teil 4 (Sungrow-Batterie) | `sensor.sh10rt_firmware_version_part_4_sungrow_battery` | `sensor.sungrow_version_4_sungrow_battery` |  |
| Total Output Energy (5004) | Total PV generation & battery discharge | Total PV generation & battery discharge | Gesamte PV-Erzeugung und Batterieentladung | `sensor.sh10rt_total_pv_generation_battery_discharge` | `sensor.total_pv_generation_battery_discharge` | kWh |
| Total Charge Energy (13041) | Total battery charge **←** | Total battery charge energy | Gesamte Batterie-Ladeenergie | `sensor.sh10rt_total_battery_charge_energy` | `sensor.total_battery_charge` | kWh |
| Total battery charge energy from PV (13013) | Total battery charge from PV **←** | Total battery charge energy from PV | Gesamte Batterie-Ladeenergie aus PV | `sensor.sh10rt_total_battery_charge_energy_from_pv` | `sensor.total_battery_charge_from_pv` | kWh |
| Total battery discharge energy (13027) | Total battery discharge **←** | Total battery discharge energy | Gesamte Batterie-Entladeenergie | `sensor.sh10rt_total_battery_discharge_energy` | `sensor.total_battery_discharge` | kWh |

### The grid (18)

| Datasheet | YAML | English | Deutsch | Entity id | YAML entity id | Unit |
| --- | --- | --- | --- | --- | --- | --- |
| Daily export energy (13045) | Daily exported energy | Daily exported energy | Täglich eingespeiste Energie | `sensor.sh10rt_daily_exported_energy` | `sensor.daily_exported_energy` | kWh |
| Daily Import Energy (13036) | Daily imported energy | Daily imported energy | Täglich bezogene Energie | `sensor.sh10rt_daily_imported_energy` | `sensor.daily_imported_energy` | kWh |
|  | Export power | Export power | Einspeiseleistung | `sensor.sh10rt_export_power` | `sensor.export_power` | W |
|  | Exporting Power **←** | Exporting power | Einspeisung | `binary_sensor.sh10rt_exporting_power` | `binary_sensor.exporting_power` |  |
|  | Exporting Power (delay) **←** | Exporting power (delayed) | Einspeisung (verzögert) | `binary_sensor.sh10rt_exporting_power_delayed` | `binary_sensor.exporting_power_delay` |  |
| Feed-in Limitation Value (13074) | Export power limit **←** | Feed-in limit | Einspeiselimit | `number.sh10rt_feed_in_limit` | `number.export_power_limit` | W |
| Max. Feed-in Power Limitation Value (5623) | Export power limit max **←** | Feed-in limit maximum | Einspeiselimit Maximum | `sensor.sh10rt_feed_in_limit_maximum` | `sensor.export_power_limit_max` | W |
| Min. Feed-in Power Limitation Value (5622) | Export power limit min **←** | Feed-in limit minimum | Einspeiselimit Minimum | `sensor.sh10rt_feed_in_limit_minimum` | `sensor.export_power_limit_min` | W |
| Feed-in Limitation (13087) | Export power limit **←** | Feed-in limit mode | Einspeiselimit-Modus | `switch.sh10rt_feed_in_limit_mode` | `switch.export_power_limit` |  |
| Grid Frequency (5242) | Grid frequency | Grid frequency | Netzfrequenz | `sensor.sh10rt_grid_frequency` | `sensor.grid_frequency` | Hz |
| *not in the datasheet* (32998) |  | Grid import limit | Netzbezugslimit | `number.sh10rt_grid_import_limit` |  | W |
| *not in the datasheet* (32998) |  | Grid import limit | Netzbezugslimit | `sensor.sh10rt_grid_import_limit` |  | kW |
| Grid-side fault (13052) |  | Grid-side fault | Netzseitiger Fehler | `sensor.sh10rt_grid_side_fault` |  |  |
|  | Import power | Import power | Bezugsleistung | `sensor.sh10rt_import_power` | `sensor.import_power` | W |
|  | Importing Power **←** | Importing power | Netzbezug | `binary_sensor.sh10rt_importing_power` | `binary_sensor.importing_power` |  |
|  | Importing Power (delay) **←** | Importing power (delayed) | Netzbezug (verzögert) | `binary_sensor.sh10rt_importing_power_delayed` | `binary_sensor.importing_power_delay` |  |
| Total export energy (13046) | Total exported energy | Total exported energy | Gesamt eingespeiste Energie | `sensor.sh10rt_total_exported_energy` | `sensor.total_exported_energy` | kWh |
| Total Import Energy (13037) | Total imported energy | Total imported energy | Gesamt bezogene Energie | `sensor.sh10rt_total_imported_energy` | `sensor.total_imported_energy` | kWh |

### The house (16)

| Datasheet | YAML | English | Deutsch | Entity id | YAML entity id | Unit |
| --- | --- | --- | --- | --- | --- | --- |
| Load power (13008) |  | Corrected load power | Korrigierte Leistungsaufnahme Verbraucher | `sensor.sh10rt_corrected_load_power` |  | W |
|  | Daily consumed energy | Daily consumed energy | Tägliche Energieaufnahme Verbraucher | `sensor.sh10rt_daily_consumed_energy` | `sensor.daily_consumed_energy` | kWh |
|  | Daily consumed energy (filtered) **←** | Daily consumed energy (smoothed) | Tägliche Energieaufnahme Verbraucher (geglättet) | `sensor.sh10rt_daily_consumed_energy_smoothed` | `sensor.daily_consumed_energy_filtered` | kWh |
| Daily direct energy consumption (13017) | Daily direct energy consumption | Daily direct energy consumption | Täglicher Direktverbrauch | `sensor.sh10rt_daily_direct_energy_consumption` | `sensor.daily_direct_energy_consumption` | kWh |
|  |  | Direct consumption this month | Direktverbrauch diesen Monat | `sensor.sh10rt_direct_consumption_this_month` |  | kWh |
|  |  | Direct consumption this year | Direktverbrauch dieses Jahr | `sensor.sh10rt_direct_consumption_this_year` |  | kWh |
| Load ON/OFF mode (13011) | Load adjustment mode **←** | Load control | Laststeuerung | `switch.sh10rt_load_control` | `switch.load_adjustment_mode` |  |
| Load Control Mode (13002) | Load adjustment mode **←** | Load control mode | Laststeuerungsmodus | `select.sh10rt_load_control_mode` | `select.load_adjustment_mode` |  |
| Load power (13008) | Load power | Load power | Leistungsaufnahme Verbraucher | `sensor.sh10rt_load_power` | `sensor.load_power` | W |
|  | Negative Load Power **←** | Negative load power | Negative Leistungsaufnahme Verbraucher | `binary_sensor.sh10rt_negative_load_power` | `binary_sensor.negative_load_power` |  |
|  | Negative Load Power (delay) **←** | Negative load power (delayed) | Negative Leistungsaufnahme Verbraucher (verzögert) | `binary_sensor.sh10rt_negative_load_power_delayed` | `binary_sensor.negative_load_power_delay` |  |
|  | Positive Load Power **←** | Positive load power | Positive Leistungsaufnahme Verbraucher | `binary_sensor.sh10rt_positive_load_power` | `binary_sensor.positive_load_power` |  |
|  | Positive Load Power (delay) **←** | Positive load power (delayed) | Positive Leistungsaufnahme Verbraucher (verzögert) | `binary_sensor.sh10rt_positive_load_power_delayed` | `binary_sensor.positive_load_power_delay` |  |
| Self-consumption of today (13029) |  | Self-consumption of today | Eigenverbrauch heute | `sensor.sh10rt_self_consumption_of_today` |  | % |
|  | Total consumed energy | Total consumed energy | Gesamte Energieaufnahme Verbraucher | `sensor.sh10rt_total_consumed_energy` | `sensor.total_consumed_energy` | kWh |
| Total direct energy consumption (13018) | Total direct energy consumption | Total direct energy consumption | Gesamter Direktverbrauch | `sensor.sh10rt_total_direct_energy_consumption` | `sensor.total_direct_energy_consumption` | kWh |

### The meter (14)

| Datasheet | YAML | English | Deutsch | Entity id | YAML entity id | Unit |
| --- | --- | --- | --- | --- | --- | --- |
| Meter Active Power (5601) | Meter active power | Meter active power | Zähler Wirkleistung | `sensor.sh10rt_meter_active_power` | `sensor.meter_active_power` | W |
| Channel 2 Phase A Active Power (13202) |  | Meter channel 2 phase A active power | Zähler Kanal 2 Phase A Wirkleistung | `sensor.sh10rt_meter_channel_2_phase_a_active_power` |  | W |
| Channel 2 Phase B Active Power (13204) |  | Meter channel 2 phase B active power | Zähler Kanal 2 Phase B Wirkleistung | `sensor.sh10rt_meter_channel_2_phase_b_active_power` |  | W |
| Channel 2 Phase C Active Power (13206) |  | Meter channel 2 phase C active power | Zähler Kanal 2 Phase C Wirkleistung | `sensor.sh10rt_meter_channel_2_phase_c_active_power` |  | W |
| Channel 2 Total Active Power (13200) |  | Meter channel 2 total active power | Zähler Kanal 2 Gesamtwirkleistung | `sensor.sh10rt_meter_channel_2_total_active_power` |  | W |
| Meter Phase A Active Power (5603) | Meter phase A active power | Meter phase A active power | Zähler Phase A Wirkleistung | `sensor.sh10rt_meter_phase_a_active_power` | `sensor.meter_phase_a_active_power` | W |
| *not in the datasheet* (5744) | Meter phase A current | Meter phase A current | Zähler Phase A Strom | `sensor.sh10rt_meter_phase_a_current` | `sensor.meter_phase_a_current` | A |
| *not in the datasheet* (5741) | Meter phase A voltage | Meter phase A voltage | Zähler Phase A Spannung | `sensor.sh10rt_meter_phase_a_voltage` | `sensor.meter_phase_a_voltage` | V |
| Meter Phase B Active Power (5605) | Meter phase B active power | Meter phase B active power | Zähler Phase B Wirkleistung | `sensor.sh10rt_meter_phase_b_active_power` | `sensor.meter_phase_b_active_power` | W |
| *not in the datasheet* (5745) | Meter phase B current | Meter phase B current | Zähler Phase B Strom | `sensor.sh10rt_meter_phase_b_current` | `sensor.meter_phase_b_current` | A |
| *not in the datasheet* (5742) | Meter phase B voltage | Meter phase B voltage | Zähler Phase B Spannung | `sensor.sh10rt_meter_phase_b_voltage` | `sensor.meter_phase_b_voltage` | V |
| Meter Phase C Active Power (5607) | Meter phase C active power | Meter phase C active power | Zähler Phase C Wirkleistung | `sensor.sh10rt_meter_phase_c_active_power` | `sensor.meter_phase_c_active_power` | W |
| *not in the datasheet* (5746) | Meter phase C current | Meter phase C current | Zähler Phase C Strom | `sensor.sh10rt_meter_phase_c_current` | `sensor.meter_phase_c_current` | A |
| *not in the datasheet* (5743) | Meter phase C voltage | Meter phase C voltage | Zähler Phase C Spannung | `sensor.sh10rt_meter_phase_c_voltage` | `sensor.meter_phase_c_voltage` | V |

## SBR battery (34)

A device of its own under the inverter, named after the pack its capacity matches, `Battery` where none does. Per-module entities exist for the fitted modules only, and are disabled by default. Ids shown for `SBR096`.

### Everything (34)

| Datasheet | YAML | English | Deutsch | Entity id | YAML entity id | Unit |
| --- | --- | --- | --- | --- | --- | --- |
|  |  | Cell voltage spread | Zellspannungsdifferenz | `sensor.sbr096_cell_voltage_spread` |  | mV |
|  |  | Coolest module | Kühlstes Modul | `sensor.sbr096_coolest_module` |  |  |
|  |  | Coolest module temperature | Temperatur kühlstes Modul | `sensor.sbr096_coolest_module_temperature` |  | °C |
|  |  | Highest cell number | Höchste Zellnummer | `sensor.sbr096_highest_cell_number` |  |  |
|  |  | Highest cell voltage | Höchste Zellspannung | `sensor.sbr096_highest_cell_voltage` |  | V |
|  |  | Lowest cell number | Niedrigste Zellnummer | `sensor.sbr096_lowest_cell_number` |  |  |
|  |  | Lowest cell voltage | Niedrigste Zellspannung | `sensor.sbr096_lowest_cell_voltage` |  | V |
|  |  | Module 1 highest cell voltage | Modul 1 höchste Zellspannung | `sensor.sbr096_module_1_highest_cell_voltage` |  | V |
|  |  | Module 1 lowest cell voltage | Modul 1 niedrigste Zellspannung | `sensor.sbr096_module_1_lowest_cell_voltage` |  | V |
|  |  | Module 2 highest cell voltage | Modul 2 höchste Zellspannung | `sensor.sbr096_module_2_highest_cell_voltage` |  | V |
|  |  | Module 2 lowest cell voltage | Modul 2 niedrigste Zellspannung | `sensor.sbr096_module_2_lowest_cell_voltage` |  | V |
|  |  | Module 3 highest cell voltage | Modul 3 höchste Zellspannung | `sensor.sbr096_module_3_highest_cell_voltage` |  | V |
|  |  | Module 3 lowest cell voltage | Modul 3 niedrigste Zellspannung | `sensor.sbr096_module_3_lowest_cell_voltage` |  | V |
|  |  | Module 4 highest cell voltage | Modul 4 höchste Zellspannung | `sensor.sbr096_module_4_highest_cell_voltage` |  | V |
|  |  | Module 4 lowest cell voltage | Modul 4 niedrigste Zellspannung | `sensor.sbr096_module_4_lowest_cell_voltage` |  | V |
|  |  | Module 5 highest cell voltage | Modul 5 höchste Zellspannung | `sensor.sbr096_module_5_highest_cell_voltage` |  | V |
|  |  | Module 5 lowest cell voltage | Modul 5 niedrigste Zellspannung | `sensor.sbr096_module_5_lowest_cell_voltage` |  | V |
|  |  | Module 6 highest cell voltage | Modul 6 höchste Zellspannung | `sensor.sbr096_module_6_highest_cell_voltage` |  | V |
|  |  | Module 6 lowest cell voltage | Modul 6 niedrigste Zellspannung | `sensor.sbr096_module_6_lowest_cell_voltage` |  | V |
|  |  | Module 7 highest cell voltage | Modul 7 höchste Zellspannung | `sensor.sbr096_module_7_highest_cell_voltage` |  | V |
|  |  | Module 7 lowest cell voltage | Modul 7 niedrigste Zellspannung | `sensor.sbr096_module_7_lowest_cell_voltage` |  | V |
|  |  | Module 8 highest cell voltage | Modul 8 höchste Zellspannung | `sensor.sbr096_module_8_highest_cell_voltage` |  | V |
|  |  | Module 8 lowest cell voltage | Modul 8 niedrigste Zellspannung | `sensor.sbr096_module_8_lowest_cell_voltage` |  | V |
|  |  | Module with highest cell | Modul mit höchster Zelle | `sensor.sbr096_module_with_highest_cell` |  |  |
|  |  | Module with lowest cell | Modul mit niedrigster Zelle | `sensor.sbr096_module_with_lowest_cell` |  |  |
|  |  | Pack current | Packstrom | `sensor.sbr096_pack_current` |  | A |
|  |  | Pack level | Pack-Ladestand | `sensor.sbr096_pack_level` |  | % |
|  |  | Pack state of health | Pack-Gesundheitszustand | `sensor.sbr096_pack_state_of_health` |  | % |
|  |  | Pack temperature | Packtemperatur | `sensor.sbr096_pack_temperature` |  | °C |
|  |  | Pack voltage | Packspannung | `sensor.sbr096_pack_voltage` |  | V |
|  |  | Total pack charge energy | Gesamte Pack-Ladeenergie | `sensor.sbr096_total_pack_charge_energy` |  | kWh |
|  |  | Total pack discharge energy | Gesamte Pack-Entladeenergie | `sensor.sbr096_total_pack_discharge_energy` |  | kWh |
|  |  | Warmest module | Wärmstes Modul | `sensor.sbr096_warmest_module` |  |  |
|  |  | Warmest module temperature | Temperatur wärmstes Modul | `sensor.sbr096_warmest_module_temperature` |  | °C |

## Wallbox (21)

A device of its own under the inverter, named after the model it reports, `Wallbox` where it reports none. Ids shown for `AC22E-01`.

### Everything (21)

| Datasheet | YAML | English | Deutsch | Entity id | YAML entity id | Unit |
| --- | --- | --- | --- | --- | --- | --- |
|  |  | Charger enabled | Ladestation aktiviert | `binary_sensor.ac22e_01_charger_enabled` |  |  |
|  |  | Charging | Lädt | `binary_sensor.ac22e_01_charging` |  |  |
|  |  | Charging current setpoint | Ladestrom-Sollwert | `sensor.ac22e_01_charging_current_setpoint` |  | A |
|  |  | Charging power | Ladeleistung | `sensor.ac22e_01_charging_power` |  | W |
|  |  | Charging status | Ladestatus | `sensor.ac22e_01_charging_status` |  |  |
|  |  | Control pilot voltage | Control-Pilot-Spannung | `sensor.ac22e_01_control_pilot_voltage` |  | V |
|  |  | Firmware version | Firmware-Version | `sensor.ac22e_01_firmware_version` |  |  |
|  |  | Maximum charging current | Maximaler Ladestrom | `sensor.ac22e_01_maximum_charging_current` |  | A |
|  |  | Maximum charging power | Maximale Ladeleistung | `sensor.ac22e_01_maximum_charging_power` |  | W |
|  |  | Minimum charging power | Minimale Ladeleistung | `sensor.ac22e_01_minimum_charging_power` |  | W |
|  |  | Offered charging current | Freigegebener Ladestrom | `sensor.ac22e_01_offered_charging_current` |  | A |
|  |  | Phase A charging current | Ladestrom Phase A | `sensor.ac22e_01_phase_a_charging_current` |  | A |
|  |  | Phase A voltage | Phase A Spannung | `sensor.ac22e_01_phase_a_voltage` |  | V |
|  |  | Phase B charging current | Ladestrom Phase B | `sensor.ac22e_01_phase_b_charging_current` |  | A |
|  |  | Phase B voltage | Phase B Spannung | `sensor.ac22e_01_phase_b_voltage` |  | V |
|  |  | Phase C charging current | Ladestrom Phase C | `sensor.ac22e_01_phase_c_charging_current` |  | A |
|  |  | Phase C voltage | Phase C Spannung | `sensor.ac22e_01_phase_c_voltage` |  | V |
|  |  | Phase mode | Phasenmodus | `sensor.ac22e_01_phase_mode` |  |  |
|  |  | Session energy | Energie der Ladesitzung | `sensor.ac22e_01_session_energy` |  | Wh |
|  |  | Start mode | Startmodus | `sensor.ac22e_01_start_mode` |  |  |
|  |  | Total charged energy | Gesamte Ladeenergie | `sensor.ac22e_01_total_charged_energy` |  | Wh |

## SG string inverter (84)

An entry of its own, never beside a hybrid. Trackers and phases exist only where the model serves them, so this is every one a model can have. Ids shown for `SG5.0RS`.

### Everything (84)

| Datasheet | YAML | English | Deutsch | Entity id | YAML entity id | Unit |
| --- | --- | --- | --- | --- | --- | --- |
| Bus voltage (5147) |  | Bus voltage | Zwischenkreisspannung | `sensor.sg5_0rs_bus_voltage` |  | V |
| Daily power yields (5003) |  | Daily PV generation | Tägliche PV-Erzeugung | `sensor.sg5_0rs_daily_pv_generation` |  | kWh |
| Daily direct energy consumption (5101) |  | Daily direct energy consumption | Täglicher Direktverbrauch | `sensor.sg5_0rs_daily_direct_energy_consumption` |  | kWh |
| Daily export energy (5093) |  | Daily exported energy | Täglich eingespeiste Energie | `sensor.sg5_0rs_daily_exported_energy` |  | kWh |
| Daily import energy (5097) |  | Daily imported energy | Täglich bezogene Energie | `sensor.sg5_0rs_daily_imported_energy` |  | kWh |
| Daily running time (5113) |  | Daily running time | Tägliche Laufzeit | `sensor.sg5_0rs_daily_running_time` |  | min |
| Internal temperature (5008) |  | Device temperature | Gerätetemperatur | `sensor.sg5_0rs_device_temperature` |  | °C |
|  |  | Diagnosis: run read-only | Diagnose: nur lesend ausführen | `button.sg5_0rs_diagnosis_run_read_only` |  |  |
|  |  | Fault reported | Fehler gemeldet | `binary_sensor.sg5_0rs_fault_reported` |  |  |
| Grid frequency (5036) |  | Grid frequency | Netzfrequenz | `sensor.sg5_0rs_grid_frequency` |  | Hz |
| Load power (5091) |  | Load power | Leistungsaufnahme Verbraucher | `sensor.sg5_0rs_load_power` |  | W |
| MPPT 1 current (5012) |  | MPPT1 current | MPPT1 Strom | `sensor.sg5_0rs_mppt1_current` |  | A |
|  |  | MPPT1 energy | MPPT1 Energie | `sensor.sg5_0rs_mppt1_energy` |  | kWh |
|  |  | MPPT1 power | MPPT1 Leistung | `sensor.sg5_0rs_mppt1_power` |  | W |
| MPPT 1 voltage (5011) |  | MPPT1 voltage | MPPT1 Spannung | `sensor.sg5_0rs_mppt1_voltage` |  | V |
| MPPT 10 current (5133) |  | MPPT10 current | MPPT10 Strom | `sensor.sg5_0rs_mppt10_current` |  | A |
|  |  | MPPT10 energy | MPPT10 Energie | `sensor.sg5_0rs_mppt10_energy` |  | kWh |
|  |  | MPPT10 power | MPPT10 Leistung | `sensor.sg5_0rs_mppt10_power` |  | W |
| MPPT 10 voltage (5132) |  | MPPT10 voltage | MPPT10 Spannung | `sensor.sg5_0rs_mppt10_voltage` |  | V |
| MPPT 11 current (5135) |  | MPPT11 current | MPPT11 Strom | `sensor.sg5_0rs_mppt11_current` |  | A |
|  |  | MPPT11 energy | MPPT11 Energie | `sensor.sg5_0rs_mppt11_energy` |  | kWh |
|  |  | MPPT11 power | MPPT11 Leistung | `sensor.sg5_0rs_mppt11_power` |  | W |
| MPPT 11 voltage (5134) |  | MPPT11 voltage | MPPT11 Spannung | `sensor.sg5_0rs_mppt11_voltage` |  | V |
| MPPT 12 current (5137) |  | MPPT12 current | MPPT12 Strom | `sensor.sg5_0rs_mppt12_current` |  | A |
|  |  | MPPT12 energy | MPPT12 Energie | `sensor.sg5_0rs_mppt12_energy` |  | kWh |
|  |  | MPPT12 power | MPPT12 Leistung | `sensor.sg5_0rs_mppt12_power` |  | W |
| MPPT 12 voltage (5136) |  | MPPT12 voltage | MPPT12 Spannung | `sensor.sg5_0rs_mppt12_voltage` |  | V |
| MPPT 2 current (5014) |  | MPPT2 current | MPPT2 Strom | `sensor.sg5_0rs_mppt2_current` |  | A |
|  |  | MPPT2 energy | MPPT2 Energie | `sensor.sg5_0rs_mppt2_energy` |  | kWh |
|  |  | MPPT2 power | MPPT2 Leistung | `sensor.sg5_0rs_mppt2_power` |  | W |
| MPPT 2 voltage (5013) |  | MPPT2 voltage | MPPT2 Spannung | `sensor.sg5_0rs_mppt2_voltage` |  | V |
| MPPT 3 current (5016) |  | MPPT3 current | MPPT3 Strom | `sensor.sg5_0rs_mppt3_current` |  | A |
|  |  | MPPT3 energy | MPPT3 Energie | `sensor.sg5_0rs_mppt3_energy` |  | kWh |
|  |  | MPPT3 power | MPPT3 Leistung | `sensor.sg5_0rs_mppt3_power` |  | W |
| MPPT 3 voltage (5015) |  | MPPT3 voltage | MPPT3 Spannung | `sensor.sg5_0rs_mppt3_voltage` |  | V |
| MPPT 4 current (5116) |  | MPPT4 current | MPPT4 Strom | `sensor.sg5_0rs_mppt4_current` |  | A |
|  |  | MPPT4 energy | MPPT4 Energie | `sensor.sg5_0rs_mppt4_energy` |  | kWh |
|  |  | MPPT4 power | MPPT4 Leistung | `sensor.sg5_0rs_mppt4_power` |  | W |
| MPPT 4 voltage (5115) |  | MPPT4 voltage | MPPT4 Spannung | `sensor.sg5_0rs_mppt4_voltage` |  | V |
| MPPT 5 current (5118) |  | MPPT5 current | MPPT5 Strom | `sensor.sg5_0rs_mppt5_current` |  | A |
|  |  | MPPT5 energy | MPPT5 Energie | `sensor.sg5_0rs_mppt5_energy` |  | kWh |
|  |  | MPPT5 power | MPPT5 Leistung | `sensor.sg5_0rs_mppt5_power` |  | W |
| MPPT 5 voltage (5117) |  | MPPT5 voltage | MPPT5 Spannung | `sensor.sg5_0rs_mppt5_voltage` |  | V |
| MPPT 6 current (5120) |  | MPPT6 current | MPPT6 Strom | `sensor.sg5_0rs_mppt6_current` |  | A |
|  |  | MPPT6 energy | MPPT6 Energie | `sensor.sg5_0rs_mppt6_energy` |  | kWh |
|  |  | MPPT6 power | MPPT6 Leistung | `sensor.sg5_0rs_mppt6_power` |  | W |
| MPPT 6 voltage (5119) |  | MPPT6 voltage | MPPT6 Spannung | `sensor.sg5_0rs_mppt6_voltage` |  | V |
| MPPT 7 current (5122) |  | MPPT7 current | MPPT7 Strom | `sensor.sg5_0rs_mppt7_current` |  | A |
|  |  | MPPT7 energy | MPPT7 Energie | `sensor.sg5_0rs_mppt7_energy` |  | kWh |
|  |  | MPPT7 power | MPPT7 Leistung | `sensor.sg5_0rs_mppt7_power` |  | W |
| MPPT 7 voltage (5121) |  | MPPT7 voltage | MPPT7 Spannung | `sensor.sg5_0rs_mppt7_voltage` |  | V |
| MPPT 8 current (5124) |  | MPPT8 current | MPPT8 Strom | `sensor.sg5_0rs_mppt8_current` |  | A |
|  |  | MPPT8 energy | MPPT8 Energie | `sensor.sg5_0rs_mppt8_energy` |  | kWh |
|  |  | MPPT8 power | MPPT8 Leistung | `sensor.sg5_0rs_mppt8_power` |  | W |
| MPPT 8 voltage (5123) |  | MPPT8 voltage | MPPT8 Spannung | `sensor.sg5_0rs_mppt8_voltage` |  | V |
| MPPT 9 current (5131) |  | MPPT9 current | MPPT9 Strom | `sensor.sg5_0rs_mppt9_current` |  | A |
|  |  | MPPT9 energy | MPPT9 Energie | `sensor.sg5_0rs_mppt9_energy` |  | kWh |
|  |  | MPPT9 power | MPPT9 Leistung | `sensor.sg5_0rs_mppt9_power` |  | W |
| MPPT 9 voltage (5130) |  | MPPT9 voltage | MPPT9 Spannung | `sensor.sg5_0rs_mppt9_voltage` |  | V |
| Meter power (5083) |  | Meter active power | Zähler Wirkleistung | `sensor.sg5_0rs_meter_active_power` |  | W |
| Meter A phase power (5085) |  | Meter phase A power | Zähler Phase A Leistung | `sensor.sg5_0rs_meter_phase_a_power` |  | W |
| Meter B phase power (5087) |  | Meter phase B power | Zähler Phase B Leistung | `sensor.sg5_0rs_meter_phase_b_power` |  | W |
| Meter C phase power (5089) |  | Meter phase C power | Zähler Phase C Leistung | `sensor.sg5_0rs_meter_phase_c_power` |  | W |
| Monthly power yields (5128) |  | Monthly PV generation | Monatliche PV-Erzeugung | `sensor.sg5_0rs_monthly_pv_generation` |  | kWh |
| Negative voltage to the ground (5146) |  | Negative voltage to ground | Negative Spannung gegen Erde | `sensor.sg5_0rs_negative_voltage_to_ground` |  | V |
| Phase A current (5022) |  | Phase A current | Phase A Strom | `sensor.sg5_0rs_phase_a_current` |  | A |
| A-B line voltage/phase A voltage (5019) |  | Phase A voltage | Phase A Spannung | `sensor.sg5_0rs_phase_a_voltage` |  | V |
| Phase B current (5023) |  | Phase B current | Phase B Strom | `sensor.sg5_0rs_phase_b_current` |  | A |
| B-C line Voltage/phase B Voltage (5020) |  | Phase B voltage | Phase B Spannung | `sensor.sg5_0rs_phase_b_voltage` |  | V |
| Phase C current (5024) |  | Phase C current | Phase C Strom | `sensor.sg5_0rs_phase_c_current` |  | A |
| C-A line Voltage/phase C Voltage (5021) |  | Phase C voltage | Phase C Spannung | `sensor.sg5_0rs_phase_c_voltage` |  | V |
| Power factor (5035) |  | Power factor | Leistungsfaktor | `sensor.sg5_0rs_power_factor` |  |  |
| Power limitation setting (5008) |  | Power limit | Leistungsgrenze | `sensor.sg5_0rs_power_limit` |  | % |
|  |  | Power limit active | Leistungsgrenze aktiv | `sensor.sg5_0rs_power_limit_active` |  |  |
| Total reactive power (5033) |  | Reactive power | Blindleistung | `sensor.sg5_0rs_reactive_power` |  | var |
|  |  | Running state | Betriebszustand | `sensor.sg5_0rs_running_state` |  |  |
| Total power yields (5144) |  | Total PV generation | Gesamte PV-Erzeugung | `sensor.sg5_0rs_total_pv_generation` |  | kWh |
| Total DC power (5017) |  | Total PV input power | Gesamte PV-Eingangsleistung | `sensor.sg5_0rs_total_pv_input_power` |  | W |
| Total active power (5031) |  | Total active power | Gesamte Wirkleistung | `sensor.sg5_0rs_total_active_power` |  | W |
| Total apparent power (5009) |  | Total apparent power | Gesamte Scheinleistung | `sensor.sg5_0rs_total_apparent_power` |  | VA |
| Total direct energy consumption (5103) |  | Total direct energy consumption | Gesamter Direktverbrauch | `sensor.sg5_0rs_total_direct_energy_consumption` |  | kWh |
| Total export energy (5095) |  | Total exported energy | Gesamt eingespeiste Energie | `sensor.sg5_0rs_total_exported_energy` |  | kWh |
| Total import energy (5099) |  | Total imported energy | Gesamt bezogene Energie | `sensor.sg5_0rs_total_imported_energy` |  | kWh |
| Total running time (5006) |  | Total running time | Gesamte Laufzeit | `sensor.sg5_0rs_total_running_time` |  | h |

## Legacy mode only (21)

Not created in modern mode. Each is a second copy of something a user
already has, so the column on the right is where the reading went instead,
with its modern-mode id.

| Datasheet | YAML | English | Deutsch | YAML entity id | Replaced in modern mode by |
| --- | --- | --- | --- | --- | --- |
| Active Power Limitation (13089) | Active power limitation raw | Active power limitation code | Wirkleistungsbegrenzung Code | `sensor.active_power_limitation_raw` | Active power limitation (`binary_sensor.sh10rt_active_power_limitation`) |
| Off-grid option (13075) | Backup mode raw | Backup mode code | Backup-Modus Code | `sensor.backup_mode_raw` | Backup mode (`switch.sh10rt_backup_mode`) |
| *not in the datasheet* (33149) | Battery charging start power | Battery charging start power | Batterie Ladestartleistung | `sensor.battery_charging_start_power` | Battery charging start power (`number.sh10rt_battery_charging_start_power`) |
| *not in the datasheet* (33150) | Battery discharging start power | Battery discharging start power | Batterie Entladestartleistung | `sensor.battery_discharging_start_power` | Battery discharging start power (`number.sh10rt_battery_discharging_start_power`) |
| Charge/discharge command (13051) | Battery forced charge discharge cmd raw | Battery forced charge/discharge command code | Batterie Zwangsladung/-entladung Befehl Code | `sensor.battery_forced_charge_discharge_cmd_raw` | Battery forced charge/discharge (`select.sh10rt_battery_forced_charge_discharge`) |
| Charge/discharge power (13052) | Battery forced charge discharge power | Battery forced charge/discharge power | Batterie Zwangsladung/-entladung Leistung | `sensor.battery_forced_charge_discharge_power` | Battery forced charge/discharge power (`number.sh10rt_battery_forced_charge_discharge_power`) |
| Max. SOC (13058) | Battery max SoC | Battery max SoC | Maximaler Batterie-Ladezustand | `sensor.battery_max_soc` | Battery max SoC (`number.sh10rt_battery_max_soc`) |
| Max. Charging Power (33047) | Battery max charge power | Battery max charging power | Maximale Batterie-Ladeleistung | `sensor.battery_max_charge_power` | Battery max charging power (`number.sh10rt_battery_max_charging_power`) |
| Max. Discharging Power (33048) | Battery max discharge power | Battery max discharging power | Maximale Batterie-Entladeleistung | `sensor.battery_max_discharge_power` | Battery max discharging power (`number.sh10rt_battery_max_discharging_power`) |
| Min. SOC (13059) | Battery min SoC | Battery min SoC | Minimaler Batterie-Ladezustand | `sensor.battery_min_soc` | Battery min SoC (`number.sh10rt_battery_min_soc`) |
| Reserved SOC for backup (13100) | Battery reserved SoC for backup | Battery reserved SoC for backup | Reservierter Batterie-Ladezustand für Backup | `sensor.battery_reserved_soc_for_backup` | Battery reserved SoC for backup (`number.sh10rt_battery_reserved_soc_for_backup`) |
| EMS mode selection (13050) | EMS mode selection raw | EMS mode selection code | EMS-Modus Auswahl Code | `sensor.ems_mode_selection_raw` | EMS mode (`select.sh10rt_ems_mode`) |
| Export power (13010) | Export power raw | Export power signed | Einspeiseleistung (mit Vorzeichen) | `sensor.export_power_raw` | Export power (`sensor.sh10rt_export_power`) |
| Feed-in Limitation Value (13074) | Export power limit | Feed-in limit | Einspeiselimit | `sensor.export_power_limit` | Feed-in limit (`number.sh10rt_feed_in_limit`) |
| Feed-in Limitation (13087) | Export power limit mode raw | Feed-in limit mode code | Einspeiselimit-Modus Code | `sensor.export_power_limit_mode_raw` | Feed-in limit mode (`switch.sh10rt_feed_in_limit_mode`) |
| Load ON/OFF mode (13011) | Load adjustment mode enable raw | Load control mode enable code | Laststeuerungsmodus Aktivierung Code | `sensor.load_adjustment_mode_enable_raw` | Load control (`switch.sh10rt_load_control`) |
| Load Control Mode (13002) | Load adjustment mode selection raw | Load control mode selection code | Laststeuerungsmodus Auswahl Code | `sensor.load_adjustment_mode_selection_raw` | Load control mode (`select.sh10rt_load_control_mode`) |
| *not in the datasheet* (31211) |  | PV generation cut code | PV-Erzeugung abgeschaltet Code | (not in the YAML) | PV generation cut (`binary_sensor.sh10rt_pv_generation_cut`) |
| PV power limitation (13018) |  | PV power limitation code | PV-Leistungsbegrenzung Code | (not in the YAML) | PV power limitation (`binary_sensor.sh10rt_pv_power_limitation`) |
| Running state (13000) | Running state raw | Running state code | Betriebszustand Code | `sensor.running_state_raw` | Running state (`sensor.sh10rt_running_state`) |
| *not in the datasheet* (31213) | APL shutdown at zero raw | Shutdown inverter when limited to 0 % power code | Abschalten bei Begrenzung auf 0 % Leistung Code | `sensor.apl_shutdown_at_zero_raw` | Shutdown inverter when limited to 0 % power (`binary_sensor.sh10rt_shutdown_inverter_when_limited_to_0_power`) |

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
