An *easy-to-use YAML-based integration* for several Sungrow inverters for Home Assistant. 

# Contents
- [1. Overview](#1-overview)
- [2. Documentation](#2-documentation)
    - [Installation/ Configuration](doc/installation.md)
    - [Dashboard Setup](doc/dashboard.md)
    - [Usage Instructions](doc/usage.md)
    - [FAQ, Troubleshooting, Known Issues](doc/help.md)
    - [Roadmap](doc/issues_roadmap.md)
- [3. Visual impressions](#3-visual-impressions)
- [4. Tested configurations](#4-tested-configurations)
- [5. Status and future work](#5-status-and-future-work)
- [6. Most important of all](#6-Most-important-of-all)


# 1. Overview

This integration lets you gather sensor data and control the EMS (Energy Management System) of a wide range of Sungrow inverters, including, but not limited to: SH3.6RS, SH4.6RS, SH5.0RS, SH5.0RT, SH6.0RS, SH8.0RT, SH8.0RT-V112, SH6.0RT, SH10RT, SH10RT-V112, SH5K-20, SH3K6, SH4K6, SH5K-V13, SH5K-30. A battery is not required, but several sensors will not be available without one.

Ensure, that you connected the inverter to the Home Assistant network using the native LAN port. The WiNet Ethernet port is not only partially working!

![Overview](doc/images/overview_modbus_connection.drawio.svg)

## 2. Documentation

The documentation covers following topics. If you need more help, please use the [github discussion](discussions). Only open an issue, if it code related, or you found a bug.

[Installation/ Configuration](doc/installation.md)

[Dashboard Setup](doc/dashboard.md)

[Usage Instructions](doc/usage.md)

[FAQ, Troubleshooting, Known Issues](doc/help.md)

## 3. Visual impressions

![Home Asisstants built-in Energy Dashboard](doc/images/HA_Energy_Dashboard.png)

![Overview ](doc/images/Dashboard_Overview.png)

![Detailed Info](doc/images/Dashboard_Detail.png)

![Basic EMS Control ](doc/images/Dashboard_EMS.png)

## 4. Tested configurations
I have a **Sungrow SH10.RT** Inverter and a **PylonTech Force H1 battery with 14.4 kWh** updating frequently to the latest **Home Assistant** (> 2023.3). I try to thoroughly test features before releasing them, but I cannot test everything (e.g., backup capabilities, DO-related, ...)

The Modbus register mapping is based on two documents the Sungrow support sent me by email. I am not sure if I am allowed to share the files, but you can search for them using their names. Let me know in the [github discussions](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/discussions), if there are newer versions available.

```
Communication.Protocol.of.Residential.Hybrid.Inverter_V1.0.23_EN
10.4 Communication Protocol_String Inverter_V1.1.36_EN.pdf
```

Please let me know if the integration also works with other Sungrow models. 

Community-confirmed supported inverters (thank you for reporting!)
- SH10RT (via home assistant community, brix29 Axel)
- SH10RT-V112 (github, dzarth, ViktorReinhold)
- SH5.0RT(home assistant community, ptC7H12 Paul)
- SH8.0RT (github, lindehoff)
- SH5K-30 (github, ajbatchelor)

partially working
- SH5.RS (home assistant community, Danirb80) via WiNetS: register running_state is not available. Created workarounds using template sensors

## 5. Status and future work 
1. See #38 for some kind of a roadmap
2. I included the registers, which are common between a wide range of Sungrow inverter models. There are many more registers in the Sungrow documents, which I left out, but I am happy to include them, if you need them. --> [github discussions](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/discussions)
3. If you made a nice visualization - let us know! --> [github discussions](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/discussions)
4. This is meant to be a simple, straightforward YAML-based integration. If you need more than this, I recommend having a look at the SunGather project: https://github.com/bohdan-s

## 6. Most important of all
We am happy to share our experiences - feel encouraged to share yours with us, too! Participate, if you have any questions :)

**Special thanks to all the people, who are actively contributing to this project and helping others in the issues and discussions!**
