### Home Assistant Sungrow SHx integration
Sungrow SH Integration for Home Assistant for SH3.6RS, SH4.6RS, SH5.0RS,
SH5.0RT, SH6.0RS, SH8.0RT, SH6.0RT, SH10RT

Tested with a **Sungrow SH10.RT** Inverter and a **PylonTech Force H1 battery**,
**Home Assistant 2021.11**.

![](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/blob/main/HASS_Sungrow_Dashboard.png)

The Modbus register mapping is based on two documents, the Sungrow support sent
me by eMail. I am not sure, if I am allowed to share the files, but maybe you
can successfully search for them...

    Communication Protocol of Residential Hybrid InverterV1.0.22_20201117.pdf
    10.4 Communication Protocol_String Inverter_V1.1.36_EN.pdf

# Usage

##  Configuration in modbus_sungrow.yaml
The yaml-based integration file needs 2 parameters as input. Adapt the following
lines in your modbus_sungrow.yaml them:

    host: 192.168.178.20 # TODO update with the IP of your inverter. No default. Check your router.
    port: 502 # TODO update with the Modbus port of your inverter. Default is '502'

##  Modbus register mapping
The file **modbus_sungrow.yaml** contains the Modbus register maps. Copy the
file  to a subfolder named "integrations", which is located at the same level of
your "configurations.yaml".

Include "modbus_sungrow.yaml" by adding follwing lines to your "configuration.yaml":

    homeassistant:
      packages: !include_dir_named integrations


Do not forget to check your configuration and restart.


# Status and future work
I only included the most important registers, which seem to be common between a
wide range of Sungrow inverter models . There are many more registers in the
Sungrow documents, which I left out.

Please let me know, if the integration works also with other Sungrow SHx models.
The manual also mentions the following Sungrow inverters, it may also work.
Leave me a feedback on this models!

SH5K-20
SH3K6
SH4K6
SH5K-V13
SH5K-30
