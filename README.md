A Home Assistant **custom integration** for Sungrow SHx hybrid inverters, distributed via HACS with a UI-based config flow.

[![Discord Chat](https://img.shields.io/discord/1127341524770898062.svg)](https://discord.gg/ZvYBejFkm2)

---

> ## BREAKING: v2.0 is a full rewrite
>
> As of **v2.0** this project is no longer a YAML package — it is now a proper
> Home Assistant **custom integration** (`sungrow_shx`) installed via HACS and
> configured from the UI. The Modbus register map and sensor semantics are
> unchanged, but **entity IDs have changed** and all configuration has moved
> out of `secrets.yaml` / `configuration.yaml`.
>
> **If you are upgrading from the pre-2.0 YAML package, read
> [`doc/migration_guide.md`](doc/migration_guide.md) before installing.**
>
> Users who cannot migrate yet can stay on the frozen
> [`legacy`](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/tree/legacy)
> branch — see [Legacy (YAML)](#9-legacy-yaml) below.

---

# Contents
- [1. Overview](#1-overview)
- [2. Installation via HACS](#2-installation-via-hacs)
- [3. Configuration](#3-configuration)
- [4. Multi-inverter setups](#4-multi-inverter-setups)
- [5. Documentation](#5-documentation)
- [6. Supported hardware / Tested configurations](#6-supported-hardware--tested-configurations)
- [7. Support](#7-support)
- [8. Visual impressions](#8-visual-impressions)
- [9. Legacy (YAML)](#9-legacy-yaml)
- [10. Status and future work](#10-status-and-future-work)
- [11. Contributions](#11-contributions)
- [12. Related work](#12-related-work)
- [13. Acknowledgements](#13-acknowledgements)


# 1. Overview

This integration lets you gather sensor data and control the EMS (Energy Management System) of a wide range of Sungrow inverters. It is primarily tested against a **SH10RT** connected via LAN cable. Other inverters such as SH\*RS, SH\*RT-V112, SH\*K-20 are supported partially — some sensors or controls may not be available. A battery is not required, but several sensors will be unavailable without one.

If available on your inverter, connect it to the Home Assistant network using the inverter's **internal LAN port**. The WiNet-S Ethernet port and the WiNet-S Wi-Fi also work, but tend to be slower and have some restrictions imposed by Sungrow on which data is available.

<figure>
  <img src="doc/images/overview_modbus_connection.drawio.svg" width="600">
  <figcaption>SHxRT connections overview</figcaption>
</figure>


<figure>
  <img src="doc/images/Inverter_LAN_ports.drawio.svg" width="600">
  <figcaption>SHxRT LAN connection</figcaption>
</figure>


# 2. Installation via HACS

### One-click

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mkaiser&repository=Sungrow-SHx-Inverter-Modbus-Home-Assistant&category=integration)

Click the badge above to open the HACS "Add custom repository" dialog
pre-filled for this repo, then press **Add** → **Install** → **Restart Home
Assistant**. <!-- TODO: verify the my.home-assistant.io redirect URL once the repo is registered in HACS default -->

### Manual HACS steps

1. Open **HACS** in the Home Assistant sidebar.
2. Click the **⋮** menu (top right) → **Custom repositories**.
3. Paste the repository URL:
   `https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant`
4. Select category **Integration** → click **Add**.
5. Find **Sungrow SHx Inverter** in the HACS integration list and click
   **Download**.
6. **Restart Home Assistant.**

### Without HACS (manual custom component install)

If you don't run HACS, you can drop the integration directly into your HA
configuration:

1. Clone / download this repository.
2. Copy the directory `custom_components/sungrow_shx/` into your Home
   Assistant config folder so it lives at
   `<config>/custom_components/sungrow_shx/`.
3. Restart Home Assistant.

For detailed prerequisites and post-install sanity checks, see
[`doc/installation.md`](doc/installation.md).


# 3. Configuration

Configuration is done entirely from the UI — there is **no YAML** to edit.

1. Go to **Settings → Devices & services → Add Integration**.
2. Search for **Sungrow SHx Inverter** and pick it.
3. Fill in the form:

![Config flow](doc/images/config_flow.png) <!-- TODO: add screenshot of the config flow -->

| Field | Description | Typical value |
|---|---|---|
| **Host** | IP address or hostname of the inverter's Modbus endpoint (LAN port or WiNet-S). | `192.168.1.50` |
| **Port** | TCP port for Modbus. | `502` |
| **Slave ID** | Inverter Modbus unit ID. | `1` |
| **SBR Slave ID** | Unit ID of the SBR battery stack. Set to `0` if you have no battery. | `200` |
| **Battery max power (W)** | Upper bound used for charge/discharge number entities. SBR096: 6500, SBR128: 8500, SBR160: 10500, SBR192: 13000, SBR224: 15000, SBR256: 17000. | `5000` |
| **Inter-request delay (ms)** | Delay between Modbus reads. Use `5` ms for direct LAN, `20`+ ms for WiNet-S. | `5` |

After submitting, the integration creates a **device** for the inverter and
populates all sensors, switches, numbers and selects. Each inverter is its
own device, so entity IDs are scoped (e.g. `sensor.sungrow_inverter_total_dc_power`).

### Options flow (scan intervals)

From **Settings → Devices & services → Sungrow SHx Inverter → Configure**
you can tune the four polling buckets (defaults shown):

| Option | Purpose | Default |
|---|---|---|
| Realtime scan interval | PV/grid/battery power, EMS state. | `5 s` |
| Fast scan interval | Voltages, currents, frequencies. | `10 s` |
| Medium scan interval | Temperatures, string-level telemetry. | `60 s` |
| Slowest scan interval | Lifetime counters, serial, firmware. | `600 s` |

Lowering the realtime interval increases Modbus traffic — if you see timeouts,
raise the inter-request delay first.


# 4. Multi-inverter setups

Multi-inverter configurations no longer need the old regex-based YAML
generator. **Just run *Add Integration* once per inverter** — each config
entry becomes an independent device with its own host, slave, battery
settings and scoped entity IDs. Rename the devices (e.g. "Sungrow Garage",
"Sungrow Shed") before building dashboards so the entity slugs follow.


# 5. Documentation
- [Installation / Configuration](doc/installation.md)
- [Migration guide (pre-2026 YAML and v2.0 integration)](doc/migration_guide.md)
- [Changelog](doc/changelog.md)
- [Dashboard setup](doc/dashboard.md)
- [Usage instructions](doc/usage.md)
- [FAQ, troubleshooting, known issues](doc/faq.md)
- [Cleaning up orphaned entities](doc/cleanup_entities.md)


# 6. Supported hardware / Tested configurations

The primary test rig is a **Sungrow SH10.RT** inverter with a **PylonTech
Force H1 (14.4 kWh)** battery, updated frequently to the latest available
firmware and Home Assistant. Features are tested before release, but not
everything can be covered (e.g. backup capabilities, DO-related controls,
Sungrow-battery specifics).

The Modbus register mapping is based on Sungrow's official *Modbus
communication protocol specification*. These documents are available from
Sungrow support and are updated sporadically. If you have a newer version,
let us know in the
[GitHub discussions](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/discussions)!

```
TI_20251119_Communication_Protocol_of_Residential_Hybrid_Inverter_V1.1.11_EN.pdf
TI_20230117_Communication.Protocol.of.Residential.and.Commerical.PV.Grid-connected.Inverter_V1.1.53_EN.pdf
```


# 7. Support

My personal time is quite limited, but there are several nice people here who like to help.

If you need any kind of assistance, you have three options:

  - Use the [GitHub discussions](../../discussions).

  - Join the Discord server [![Discord Chat](https://img.shields.io/discord/1127341524770898062.svg)](https://discord.gg/ZvYBejFkm2).

  - Only if code-related (bugs / contributions): open a [GitHub issue](../../issues) or create a pull request.


# 8. Visual impressions

<figure>
  <img src="doc/images/energy_dashboard_summary.drawio.svg" width="600">
  <figcaption>Home Assistant's built-in Energy Dashboard</figcaption>
</figure>


<figure>
  <img src="doc/images/default_dashboard_info.drawio.svg" width="600">
  <figcaption>Default dashboard tab "Overview"</figcaption>
</figure>


<figure>
  <img src="doc/images/default_dashboard_details.drawio.svg" width="600">
  <figcaption>Default dashboard tab "Detail"</figcaption>
</figure>


<figure>
  <img src="doc/images/default_dashboard_ems_ctrl.drawio.svg" width="600">
  <figcaption>Default dashboard tab "EMS control"</figcaption>
</figure>


# 9. Legacy (YAML)

The pre-2.0 YAML package is **frozen** — no new features, only critical
fixes if any. If you are not ready to migrate, pin to the
[`legacy`](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/tree/legacy)
branch/tag, which ships the `modbus_sungrow*.yaml` files and the old
installation flow.

For the upgrade path from the YAML package to the HACS integration,
including the full entity-ID mapping and rollback instructions, see
[`doc/migration_guide.md`](doc/migration_guide.md).


# 10. Status and future work

This is the first stable release of the integration rewrite. Known
follow-up items:

- Dashboards under `dashboards/` still reference the legacy `sensor.sg_*`
  entity IDs and will be updated in a separate pass.
- Publishing the repo to the HACS default list (currently install via
  *Custom repositories*).

If you need more than what this integration provides, have a look at:
  - https://github.com/TCzerny/ha-modbus-manager
  - https://github.com/bohdan-s


# 11. Contributions

We are happy to share our experiences — feel encouraged to share yours with us, too!

If you have any questions, feature requests, found any bugs or have some hints how to update the documentation, a low-threshold way is to join the [![Discord Chat](https://img.shields.io/discord/1127341524770898062.svg)](https://discord.gg/ZvYBejFkm2) and just ask.


# 12. Related work
- **[HA Modbus Manager](https://github.com/TCzerny/ha-modbus-manager)**
- **[Sungrow Wallbox](https://github.com/Louisbertelsmann/Sungrow-Wallbox-Modbus-HomeAssistant)**
- **[Sungrow Logger 1000a](https://github.com/RafAustralia/Sungrow-Logger1000a-Modbus)**
- **[Chint DTSU666 Modbus](https://github.com/RafAustralia/Chint-DTSU666-20-modbus/)**
- **[EVCC](https://github.com/Hoellenwesen/home-assistant-configurations)**
- **Sungrow document collections [by bohdan-s](https://github.com/bohdan-s/Sungrow-Inverter) and [by Gnarfoz](https://github.com/Gnarfoz/Sungrow-Inverter)**


# 13. Acknowledgements

**Thanks to all the people who are actively contributing to this project! Special thanks to Gnarfoz, Louisbertelsmann, dylan09, elektrinis and many more!**
