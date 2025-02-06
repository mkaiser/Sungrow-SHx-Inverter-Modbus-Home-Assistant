An *easy-to-use YAML-based integration* for several Sungrow inverters for Home Assistant. 

[![Discord Chat](https://img.shields.io/discord/1127341524770898062.svg)](https://discord.gg/ZvYBejFkm2)

# Contents
- [1. Overview](#1-overview)
- [2. Documentation](#2-documentation)
    - [Installation / Configuration](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/wiki/FAQ:-How-to-install)
    - [Dashboard Setup](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/wiki/How-to-configure-the-dashboards)
    - [Usage Instructions](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/wiki/FAQ:-How-to-use)
    - [FAQ, Troubleshooting, Known Issues](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/wiki/FAQ:-Problems-with-the-connection)
    - [Roadmap](doc/issues_roadmap.md)
- [3. Support](#3-support)
- [4. Visual impressions](#4-visual-impressions)
- [5. Tested configurations](#5-tested-configurations)
- [6. Status and future work](#6-status-and-future-work)
- [7. Contributions](#7-contributions)
- [8. Related work](#8-related-work)


# 1. Overview

This integration lets you gather sensor data and control the EMS (Energy Management System) of a wide range of Sungrow inverters, including, but not limited to: SH3.6RS, SH4.6RS, SH5.0RS, SH5.0RT, SH6.0RS, SH8.0RT, SH8.0RT-V112, SH6.0RT, SH10RT, SH10RT-V112, SH5K-20, SH3K6, SH4K6, SH5K-V13, SH5K-30. A battery is not required, but several sensors will not be available without one.

If avaliable on your inverter, connect the inverter to the Home Assistant network using the inverter's **internal LAN port**. The WiNet-S Ethernet port and the WiNet-S Wi-Fi also work, but sometimes slightly slower and with some restrictions imposed by Sungrow on which data is available.

![SHxRT connections overview](doc/images/overview_modbus_connection.drawio.svg)

![SHxRT LAN connection](doc/images/Inverter_LAN_ports.drawio.svg)

## 2. Documentation

The documentation covers following topics:

[Installation / Configuration](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/wiki/FAQ:-How-to-install)

[Dashboard Setup](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/wiki/How-to-configure-the-dashboards)

[Usage Instructions](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/wiki/FAQ:-How-to-use)

[Wiki: FAQ, Troubleshooting, Known Issues](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/wiki/)

## 3. Support

My personal time is quite limited, but there are several nice people here who like to help. 

If you need any kind of assistance, you have three options:

a) Use the [GitHub discussions](../../discussions).

b) Join the Discord server [![Discord Chat](https://img.shields.io/discord/1127341524770898062.svg)](https://discord.gg/ZvYBejFkm2).

c) Only if code-related (bugs / contributions): Open a [GitHub issue](../../issue) or create a pull request.

## 4. Visual impressions

Home Asisstant's built-in Energy Dashboard

<img src="doc/images/HA_Energy_Dashboard.png" width="600">


Default dashboard tab "Overview"

<img src="doc/images/Dashboard_Overview.png" width="600">


Default dashboard tab "Detail"

<img src="doc/images/Dashboard_Detail.png" width="600">


Default dashboard tab "EMS"

<img src="doc/images/Dashboard_EMS.png" width="600">


## 5. Tested configurations
I have a **Sungrow SH10.RT** inverter and a **PylonTech Force H1 battery with 14.4 kWh**, updating frequently to the latest **Home Assistant**. I try to thoroughly test features before releasing them, but I cannot test everything (e.g., backup capabilities, DO-related, ...)

The Modbus register mapping is based on Sungrow's official *Modbus communication protocol specification*. These documents are available from Sungrow support. They are only updated sporadically. If you have a newer version, let me know in the [GitHub discussions](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/discussions)!

```
TI_20240924_Communication Protocol of Residential Hybrid Inverter-V1.1.5
TI_20230117_Communication.Protocol.of.Residential.and.Commerical.PV.Grid-connected.Inverter_V1.1.53_EN.pdf
```

Please let me know if the integration also works with other Sungrow models!

Community-confirmed supported inverters (thank you for reporting!):
- SH10RT (Home Assistant community, brix29 Axel)
- SH10RT-V112 (GitHub, dzarth, ViktorReinhold)
- SH5.0RT (Home Assistant community, ptC7H12 Paul)
- SH8.0RT (GitHub, lindehoff)
- SH5K-30 (GitHub, ajbatchelor)

Partially working:
- SH5.0RS (Home Assistant community, Danirb80) via WiNet-S: register running_state is not available. Created workarounds using template sensors.
- SH6.0RS (GitHub, icefest) largely working, occasionally needing to restart the WiNet-S dongle.

## 6. Status and future work 
1. See [#38](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/38) for some kind of a roadmap
2. I included the registers, which are common between a wide range of Sungrow inverter models. There are many more registers in the Sungrow documents, which I left out, but I am happy to include them, if you need them. --> [GitHub discussions](../../discussions)
3. If you made a nice visualization - let us know! --> [GitHub discussions](../../discussions)
4. This is meant to be a simple, straight-forward YAML-based integration. If you need more than this, I recommend having a look at the SunGather project: https://github.com/bohdan-s

## 7. Contributions
We are happy to share our experiences - feel encouraged to share yours with us, too! 

If you have any questions, feature requests, found any bugs or have some hints how to update the documentation, a low-threshold way is to join the [![Discord Chat](https://img.shields.io/discord/1127341524770898062.svg)](https://discord.gg/ZvYBejFkm2) and just ask.

**Thanks to all the people, who are actively contributing to this project! Special thanks to @Louisbertelsmann, dylan09 and elektrinis for their efforts**

## 8. Related work
- **Sungrow Wallbox**: Check https://github.com/Louisbertelsmann/Sungrow-Wallbox-Modbus-HomeAssistant
- **Sungrow Logger 1000a**: https://github.com/RafAustralia/Sungrow-Logger1000a-Modbus
- **Chint DTSU666 Modbus**: https://github.com/RafAustralia/Chint-DTSU666-20-modbus/
- **EVCC**: Check https://github.com/Hoellenwesen/home-assistant-configurations
- **Sungrow document collection**: https://github.com/bohdan-s/Sungrow-Inverter / https://github.com/Gnarfoz/Sungrow-Inverter/