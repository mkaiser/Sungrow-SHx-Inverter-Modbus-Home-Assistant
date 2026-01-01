An *easy-to-use YAML-based integration* for several Sungrow inverters for Home Assistant. 

[![Discord Chat](https://img.shields.io/discord/1127341524770898062.svg)](https://discord.gg/ZvYBejFkm2)

# 2026-01-01 "Version 2 of modbus_sungrow.yaml"

After five years of continuous development with maintained backwards compatibility, this integration reached its limits. With the help of @theunknown86 and several others, this yaml-based integration was rebased on a better and more flexible codebase. It is still remains yaml-based and not a "full" Home Assistant integration, but can now support different Sungrow models with their specific features ("quirks"). As long there is no "real integration" available, I will continue to maintain the new yaml file. 

**The migration to the new version requires a few manual steps, see [migration guide](doc/migration_guide.md).**

The old version will be archived in the separate branch "2025-legacy". The "dev"-branch which was tested now by several users is now the "main"-branch.


# Contents
- [1. Overview](#1-overview)
- [2. Documentation](#2-documentation)
    - [Changelog](doc/changelog.md)
    - [Installation / Configuration](doc/installation.md)
    - [Migration guide from 2025er version](doc/migration_guide.md)
    - [Dashboard Setup](doc/dashboard.md)
    - [Usage Instructions](doc/usage.md)
    - [FAQ, Troubleshooting, Known Issues](doc/faq.md)  
- [3. Support](#3-support)
- [4. Visual impressions](#4-visual-impressions)
- [5. Tested configurations](#5-tested-configurations)
- [6. Status and future work](#6-status-and-future-work)
- [7. Contributions](#7-contributions)
- [8. Related work](#8-related-work)


# 1. Overview

This integration lets you gather sensor data and control the EMS (Energy Management System) of a wide range of Sungrow inverters, including, but not limited to: SH3.6RS, SH4.6RS, SH5.0RS, SH5.0RT, SH6.0RS, SH8.0RT, SH8.0RT-V112, SH6.0RT, SH10RT, SH10RT-V112, SH5K-20, SH3K6, SH4K6, SH5K-V13, SH5K-30. A battery is not required, but several sensors will not be available without one.

If avaliable on your inverter, connect the inverter to the Home Assistant network using the inverters **internal LAN port**. The WiNet-S Ethernet port and the WiNet-S Wi-Fi also work, but sometimes slightly slower and with some restrictions imposed by Sungrow on which data is available.

<figure>
  <img src="doc/images/overview_modbus_connection.drawio.svg" width="600">
  <figcaption>SHxRT connections overview</figcaption>
</figure>


<figure>
  <img src="doc/images/Inverter_LAN_ports.drawio.svg" width="600">
  <figcaption>SHxRT LAN connection</figcaption>
</figure>


# 2. Documentation
- [Installation / Configuration](doc/installation.md)
- [Migration from versions before 2026](doc/migration_guide.md)
- [Changelog](doc/changelog.md)
- [Usage Instructions](doc/usage.md)
- [FAQ](doc/faq.md)

# 3. Support

My personal time is quite limited, but there are several nice people here who like to help. 

If you need any kind of assistance, you have three options:

  - Use the [GitHub discussions](../../discussions).

  - Join the Discord server [![Discord Chat](https://img.shields.io/discord/1127341524770898062.svg)](https://discord.gg/ZvYBejFkm2).

  - Only if code-related (bugs / contributions): Open a [GitHub issue](../../issue) or create a pull request.

# 4. Visual impressions

<figure>
  <img src="doc/images/energy_dashboard_summary.drawio.svg" width="600">
  <figcaption>Home Asisstant's built-in Energy Dashboard</figcaption>
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



# 5. Tested configurations
I have a **Sungrow SH10.RT** inverter and a **PylonTech Force H1 battery with 14.4 kWh**, updating frequently to the latest available firmware and **Home Assistant**. I try to thoroughly test features before releasing them, but I cannot test everything (e.g., backup capabilities, DO-related, sungrow-battery-specifics ...)

The Modbus register mapping is based on Sungrow's official *Modbus communication protocol specification*. These documents are available from Sungrow support. They are only updated sporadically. If you have a newer version, let me know in the [GitHub discussions](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/discussions)!

```
TI_20251119_Communication_Protocol_of_Residential_Hybrid_Inverter_V1.1.11_EN.pdf
TI_20230117_Communication.Protocol.of.Residential.and.Commerical.PV.Grid-connected.Inverter_V1.1.53_EN.pdf
```


# 6. Status and future work 
This is meant to be a simple, straight-forward YAML-based integration. If you need more than this, I recommend having a look at other projects: 
  - https://github.com/TCzerny/ha-modbus-manager
  - https://github.com/bohdan-s

# 7. Contributions
We are happy to share our experiences - feel encouraged to share yours with us, too! 

If you have any questions, feature requests, found any bugs or have some hints how to update the documentation, a low-threshold way is to join the [![Discord Chat](https://img.shields.io/discord/1127341524770898062.svg)](https://discord.gg/ZvYBejFkm2) and just ask.

# 8. Related work
- **Sungrow Wallbox**: Check https://github.com/Louisbertelsmann/Sungrow-Wallbox-Modbus-HomeAssistant
- **Sungrow Logger 1000a**: https://github.com/RafAustralia/Sungrow-Logger1000a-Modbus
- **Chint DTSU666 Modbus**: https://github.com/RafAustralia/Chint-DTSU666-20-modbus/
- **EVCC**: Check https://github.com/Hoellenwesen/home-assistant-configurations
- **Sungrow document collection**: https://github.com/bohdan-s/Sungrow-Inverter / https://github.com/Gnarfoz/Sungrow-Inverter/


# 9. Acknowledgements

**Thanks to all the people, who are actively contributing to this project! Special thanks to Gnarfoz, Louisbertelsmann, dylan09, elektrinis and many more!**