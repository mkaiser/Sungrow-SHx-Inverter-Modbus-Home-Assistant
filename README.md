# Home Assistant Sungrow SHx integration
An *easy-to-use YAML-based integration* for Sungrow inverters for Home Assistant. A wide range of models is supported, including, but not limited to: SH3.6RS, SH4.6RS, SH5.0RS, SH5.0RT, SH6.0RS, SH8.0RT, SH8.0RT-V112, SH6.0RT, SH10RT, SH10RT-V112, SH5K-20, SH3K6, SH4K6, SH5K-V13, SH5K-30. 

It was tested with my **Sungrow SH10.RT** Inverter and a **PylonTech Force H1 battery**, **Home Assistant 2023.1**.


**Very important note - topmost known issue:** 
**Using the native LAN port of the inverter is highly recommended - the WiNet Ethernet port is not fully working!**
Recent sungrow invertes come with WiNet S, a Dongle for WLAN access / LAN interconnection. Although the dongle has an Ethernet port, modbus is not working properly with this port. Some modbus registers are working, and some not. It seems like Sungrow is actively working on that, so maybe in the near future they will release firmware upgrades to improve the modbus via WiNet S support. 

NOTE: Users with single-phase inverters have reported multiple issues (sungrows nomenclature is SH3.RS - single phase, vs. SH10.RT - three phase). These inverters only support a subset of the modbus registers (although the users reported using the inverter's built-in LAN port.)


The Modbus register mapping is based on two documents the Sungrow support sent me by email. I am not sure if I am allowed to share the files, but you can search for them using their names. 

    Communication.Protocol.of.Residential.Hybrid.Inverter_V1.0.23_EN
    10.4 Communication Protocol_String Inverter_V1.1.36_EN.pdf

Please let me know if the integration also works with other Sungrow SHx models. 

Community confirmed supported inverters (thank you for reporting!)
- SH10RT (via home assistant community, brix29 Axel)
- SH10RT-V112 (github, dzarth, ViktorReinhold)
- SH5.0RT(home assistant community, ptC7H12 Paul)
- SH8.0RT (github, lindehoff)
- SH5K-30 (github, ajbatchelor)

partially working
- SH5.RS (home assistant community, Danirb80) via WiNetS: register running_state is not available. We are working on workarounds...


## Dashboards

dashboard.yaml provides a premade setup for quick integration and as a basis for more customization.  
1) Quick Overview 
![image](https://user-images.githubusercontent.com/29856783/215203711-024bf3d6-ed33-4877-b39b-aa5c296703cc.png)


2) Detailed Info
![image](https://user-images.githubusercontent.com/29856783/215203959-6213981b-3ca0-41e8-a10d-5235284a1002.png)


3) Basic EMS Control 
![image](https://user-images.githubusercontent.com/29856783/215204039-4c36782c-df91-4673-921a-bf50f86f1b50.png)


# Usage / Configuration

## Overview 

This does not come as an integration, you can set up by clicking something in the HomeAssistant GUI. 

It is not and "installation" process, but more a "configuration". For this, you need to add some information to the home assistant configuration files:

Use the Visual Studio Code Server add-on for configuration. In the screenshot, the relevant files for the sungrow integration are highlighted, which you need to modify:
![image](https://user-images.githubusercontent.com/29856783/156320105-6eb9448d-301c-4c81-9d2a-ded83840a3aa.png)


##  Configuration in secrets.yaml
The yaml-based integration file needs 3 parameters as input. Copy the following lines in your secrets.yaml and adapt them:

    sungrow_modbus_host_ip: 192.168.178.20 # TODO update with the IP of your inverter. No default. Check your router.
    sungrow_modbus_port: 502 # TODO update with the Modbus port of your inverter. Default is '502'
    sungrow_modbus_slave: 1 #TODO update with the slave address of your inverter. Default is '1'

##  Modbus register mapping
The file **modbus_sungrow.yaml** contains the Modbus register maps, template sensors and automations to set values like the battery minimum SoC. Copy the file to a subfolder named "integrations" (maybe create it first), which is located at the same level as your "configurations.yaml" (see screenshot). 

Include "modbus_sungrow.yaml" by adding the follwing lines to your "configuration.yaml":

    homeassistant:
      packages: !include_dir_named integrations
    
Do not forget to check your configuration (Developer Tools --> hit "check configuration" and restart: it won't work without a restart!)

After the restart, some new sensors should be available. E.g., check for "Total DC power"


##  Add a nice Dashboard like the one shown above

Navigate to folder "dashboards/_DefaultDashboard_mkaiser" and follow the instructions in the README

Browse the "dashboards" folder for other contributed dashboards :)

##  Configure the HomeAssistant energy dashboard 
![image](https://user-images.githubusercontent.com/29856783/148981502-823778d7-ebd3-4101-8060-48e0619cee4c.png)

Open the Energy settings ("Configuration" --> "Energy") and adapt the highlighted values as shown in the screenshot: 

![image](https://user-images.githubusercontent.com/29856783/148981897-23821ec4-c35e-4dd0-8ec1-02aefd0eac93.png)

Note, that only the energy values in kWh are shown in this dashboard and not the current power dissipation (in W).


## Controlling the  EMS (Energy Management System)
You can set EMS parameters in the third (from left) tab of the preconfigured dashboard. 

Example to force-charge the battery:
1. Change the "EMS mode" from "Self-consumption mode" to "Forced mode"
2. Select "Force charge" as the input of the "Battery forced charge discharge cmd"
3. Limit the energy loaded by setting "max Soc" (percentage of battery)
4. You can control the charge discharge power by 3 paramters:
- Limit the forced charge discharge power using "Set forced charge discharge power".
- Limit the maximum battery charge power using "set max battery charge power". This value also limits the "force charge discharge power".
- Limit the maximum battery discharge power using "set max battery discharge power", and this value also limits the "force charge discharge power".

Please note that changes on the input sliders may take up to 60 seconds until they affect the "battery status" entities in the GUI. 


# Status and future work 
1. I included the registers, which are common between a wide range of Sungrow inverter models . There are many more registers in the Sungrow documents, which I deliberately left out.
2. Some stuff is not working (e.g. getting the battery capacity). I appreciate some help here :)
3. See #38 for planned stuff
4. If you made a nice visualization - let us know! 
5. This is meant to be a simple, straightforward YAML-based integration. If you need more than this, I recommend having a look at the SunGather project: https://github.com/bohdan-s

I am happy to share my experience with you - feel encouraged to share yours with us, too! Open issues if you have any questions :)

