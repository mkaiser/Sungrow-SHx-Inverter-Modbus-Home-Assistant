
# Migration guide from modbus_sungrow.yaml versions before 2026

## Single Inverter setup
 0) Backup your modbus_sungrow.yaml file (keep in mind to rename the file ending from .yaml to yaml.bak to avoid a double inclusion by the deprecated (!)```!include_dir_named``` directive in configuration.yaml)

 1) Adapt ```secrets.yaml```:
    - Rename ```sungrow_modbus_slave``` to ```sungrow_modbus_device_address```
    - Add ```sungrow_modbus_battery_max_power: 5000``` (use the max supported power of your battery, see [comments in secrets.yaml](../secrets.yaml) for details)
    - Add ```sungrow_modbus_wait_milliseconds``` (choose 5 ms for LAN, 20 or higher for WiNet-S

 2) Swap your modbus_sungrow.yaml file with the [current version](../modbus_sungrow.yaml)

 3) Restart Home Assistant: ```Developer tools --> Check Configuration --> Restart```

 4) Check the Log for errors: ```Settings --> System --> Log``` (or hotkey ```c``` followed by ```log```)

 5) If everything is fine, update the [default dashboard provided in the git](../dashboards/DefaultDashboard/dashboard.yaml):
    - Open the file
    - Copy all content
    - In Home Assistant: ```Settings --> Dashboards --> Select your dashboard --> 3-dots menu (top right) --> Edit Dashboard --> 3-dots menu (top right) --> Raw configuration editor```
    - Replace all content with the copied content from the file and save

 6) Remove orphaned / unavailable sensors
 
    [see this how-to guide to cleanup](cleanup_entities.md)


 7) Update the new "Energy Dashboard" (introduced in HA 25.12)

    ```Home Assisant --> Energy --> Edit Dashboard (top right):```

     **Electricity grid**

       ```Grid consumption``` --> ```Total imported energy```

       ```Return to grid``` --> ```Total exported energy```

       ```Grid power``` --> ```Meter active power```

     **Solar Panels**

       ```Solar production energy``` --> ```Total PV generation```

       ```Solar production power``` --> ```Total DC power```

     **Home battery storage**

       ```Energy charged into the battery``` --> ```Total battery charge```

       ```Energy discharged from the battery``` --> ```Total battery discharge```

       ```Battery power``` --> ```Battery discharging power signed```

   8) If you see unavailable entities in Home Assistant after upgrading the integration due to renaming, you can follow the steps in [cleanup_entities.md](cleanup_entities.md) to remove them from your installation.
   Please note that depending on your inverter and the way to connect it to Home Assistant (Lan, WiNet-S Wifi or WiNet-S LAN) some entities might not be available in your installation.
         

## Multiple Inverters

Option A: if you have a running installation with one inverter based on modbus_sungrow.yaml and want to add a second one, use [modbus_sungrow_multiple_inverters_2.yaml](../modbus_sungrow_multiple_inverters_2.yaml) (or *_3 for a third one)

Option B: if you are setting up multiple inverters for the first time in HA, use [modbus_sungrow_multiple_inverters_1.yaml](../modbus_sungrow_multiple_inverters_1.yaml) and
[modbus_sungrow_multiple_inverters_2.yaml](../modbus_sungrow_multiple_inverters_2.yaml) or
 (or *_3 for a third one)

---

## Migrating from the YAML package to the HACS integration (v2.0)

Starting with **v2.0** this project ships as a proper Home Assistant custom
integration (`sungrow_shx`) with a UI config flow, per-device entities, and
tunable polling intervals — replacing the hand-written `modbus_sungrow*.yaml`
packages entirely. The Modbus traffic, register map, and sensor semantics are
unchanged; what moves is **where the configuration lives** (UI instead of
YAML) and **how entities are named** (scoped per device, no more global
`sungrow_*` prefixes).

### Step-by-step

1. **Install via HACS.** In HACS → *Custom Repositories*, add this repo
   (`https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant`)
   with category *Integration*, then install **Sungrow SHx Inverter** and
   restart Home Assistant.
2. **Add the integration.** Go to **Settings → Devices & services → Add
   Integration** and pick *Sungrow SHx Inverter*. Enter the same host, port,
   inverter unit ID, battery (SBR) unit ID, battery max power, and inter-request
   delay you had in `secrets.yaml`.
3. **Remove the package entries.** In `configuration.yaml`, delete (or comment
   out) every `packages:` entry that referenced
   `modbus_sungrow.yaml` / `modbus_sungrow_multiple_inverters_{1,2,3}.yaml`.
4. **Remove the `!include` lines.** If your `sensor:`, `template:`,
   `automation:`, or `modbus:` top-level blocks use
   `!include modbus_sungrow*.yaml` (directly or via a packages dir), remove or
   comment them out as well. Restart Home Assistant.
5. **Multi-inverter users.** Add the integration **once per inverter** —
   each config entry becomes a separate device with its own set of entities.
   The legacy `_inv_2` / `_inv_3` suffixes disappear; use the HA device page
   to rename devices (e.g. "Sungrow Garage", "Sungrow Shed") and the scoped
   entity IDs will follow.

### Entity ID mapping

The new integration scopes entities under each device, so unique IDs are
stable across renames but the old free-form `sensor.sungrow_*` entity IDs
change. Below is a sample of the most-used entities — you may need to
**rename entities** in the UI (Settings → Devices & services → Sungrow SHx →
entity → ✏️) to preserve existing automations, scripts, or history graphs.

| Old entity ID (YAML package) | New entity ID (integration) | Notes |
|---|---|---|
| `sensor.sg_total_pv_power` | `sensor.sungrow_inverter_total_pv_power` | Realtime PV power |
| `sensor.sg_total_dc_power` | `sensor.sungrow_inverter_total_dc_power` | MPPT sum |
| `sensor.sg_mppt1_voltage` | `sensor.sungrow_inverter_mppt1_voltage` | Per-string |
| `sensor.sg_mppt1_current` | `sensor.sungrow_inverter_mppt1_current` | Per-string |
| `sensor.sg_battery_power` | `sensor.sungrow_inverter_battery_power` | Unsigned; see signed variant below |
| `sensor.sg_battery_level` | `sensor.sungrow_inverter_battery_level` | State of charge % |
| `sensor.sg_meter_active_power` | `sensor.sungrow_inverter_meter_active_power` | Grid power, signed |
| `sensor.sg_daily_pv_generation` | `sensor.sungrow_inverter_daily_pv_generation` | Daily kWh, energy dashboard |
| `sensor.sg_total_pv_generation` | `sensor.sungrow_inverter_total_pv_generation` | Lifetime kWh |
| `sensor.sg_inverter_temperature` | `sensor.sungrow_inverter_inverter_temperature` | Inverter internal temp |
| `sensor.sg_grid_frequency` | `sensor.sungrow_inverter_grid_frequency` | Hz |
| `sensor.sg_inverter_serial` | `sensor.sungrow_inverter_serial_number` | Now lives on the device info page too |
| `sensor.sg_running_state` | `sensor.sungrow_inverter_running_state` | Decoded state string |
| `sensor.sg_battery_discharging_power_signed` | `sensor.sungrow_inverter_battery_discharging_power_signed` | Signed, for Energy Dashboard battery |
| `switch.sg_ems_mode_self_consumption` | `switch.sungrow_inverter_ems_mode_self_consumption` | EMS mode toggle |

> The slug `sungrow_inverter` above comes from the *device name* at creation
> time. If you rename the device to, say, **Garage Inverter**, HA will migrate
> future entity IDs to `sensor.garage_inverter_*`. To keep automations happy,
> rename the device **before** you rebuild dashboards.

### Troubleshooting

* **Repairs panel shows "Legacy Sungrow YAML package is still loaded".**
  A `modbus:` hub whose name starts with `SungrowSHx` is still configured.
  Check your `configuration.yaml`, `packages:` directory, and any
  `!include modbus_sungrow*.yaml` lines, remove them, and restart.
* **Repairs panel shows "Sungrow SHx entry imported from YAML".**
  Means the short-lived `sungrow_shx:` YAML import block did its job — delete
  the block from `configuration.yaml`, restart, then click *Submit* in the
  Repairs card to dismiss.
* **Duplicate / unavailable entities after the switch.** The package-era
  entities stay in the entity registry until removed; follow
  [cleanup_entities.md](cleanup_entities.md).

### Rollback

The legacy YAML package keeps working as long as you keep its files. If the
integration doesn't work for you, pull the repo at the `legacy` git tag (or
the `legacy` branch) — those snapshots predate the move to the custom
component and ship only the `modbus_sungrow*.yaml` files. Remove the
integration from *Settings → Devices & services* before falling back, to
avoid double-polling the inverter over Modbus.
Edit [secrets.yaml](../secrets.yaml) accordingly:

  ```
  # Inverter 1:
  sungrow_modbus_host_ip_inv_1: 192.168.4.xxx # TODO update with the IP of your inverter. No default. Check your router.
  sungrow_modbus_port_inv_1: 502 # Modbus port of your inverter. Default is '502'
  sungrow_modbus_device_address_inv_1: 1 # device address of your inverter. Default is '1'
  sungrow_modbus_wait_milliseconds_inv_1: 5 # "Choose 5 ms for LAN, 20 or higher for WiNet-S"
  sungrow_modbus_battery_max_power_inv_1: 5000  # TODO update with the maximum charge power of your battery in W. 

  # Inverter 2:
  sungrow_modbus_host_ip_inv_2: 192.168.4.xxx # TODO update with the IP of your inverter. No default. Check your router.
  sungrow_modbus_port_inv_2: 502 # Modbus port of your inverter. Default is '502'
  sungrow_modbus_device_address_inv_2: 2 # device address of your inverter. Default is '1'
  sungrow_modbus_wait_milliseconds_inv_2: 5 # "Choose 5 ms for LAN, 20 or higher for WiNet-S"
  sungrow_modbus_battery_max_power_inv_2: 5000  # TODO update with the maximum charge power of your battery in W. 
  ```

