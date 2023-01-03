# Home Assistant Sungrow SHx integration
Sungrow SH Integration for Home Assistant for SH3.6RS, SH4.6RS, SH5.0RS, SH5.0RT, SH6.0RS, SH8.0RT, SH6.0RT, SH10RT
SH5K-20, SH3K6, SH4K6, SH5K-V13, SH5K-30

Tested with my **Sungrow SH10.RT** Inverter and a **PylonTech Force H1 battery**, **Home Assistant 2022.12 (current version)**.

Please let me know, if the integration works also with other Sungrow SHx models. 

Community confirmed supported inverters (thanks for reporting!)
- SH10RT (via home assistant community, brix29 Axel)
- SH10RT-V112 (github, dzarth, ViktorReinhold)
- SH5.0RT(home assistant community, ptC7H12 Paul)
- SH8.0RT (github, lindehoff)
- SH5K-30 (github, ajbatchelor)

**NOTE: Multiple issues have been reported from users with single phase inverters (sungrows nomenclature is SH3.RS - single phase, vs. SH10.RT - three phase). These inverters seem to only support a subset of the modbus registers.  Also there are issues with the WiNetS Adapter. Some users can use Modbus using WiNetS as ETH Port. For some users that won't work. If possible: ALWAYS use the native LAN port of your inerter (if existing!)**


The Modbus register mapping is based on two documents, the Sungrow support sent me by eMail. I am not sure, if I am allowed to share the files, but maybe you can successfully search for them...

    Communication.Protocol.of.Residential.Hybrid.Inverter_V1.0.23_EN
    10.4 Communication Protocol_String Inverter_V1.1.36_EN.pdf


## Dashboards

Display the status of the inverter:

![image](https://user-images.githubusercontent.com/29856783/191961543-fbf9fa73-018f-4724-87cb-4e5d8261b43b.png)

Control the EMS (Energy Management System):

![image](https://user-images.githubusercontent.com/29856783/191961272-c030dd4d-3d62-434a-8306-3838e8c6fe37.png)

# Usage / Configuration

## Overview 

This does not come as a integration, you can set up by clicking something in the HomeAssistant GUI. 

There is not "installation", more a "configuration". For this you need to add some information to the home assistant configuration files:

Use the Visual Studio Code Server add-on for configuration. In the screenshot the relevant files for the sungrow integration are highlighted, which you need to modify:
![image](https://user-images.githubusercontent.com/29856783/156320105-6eb9448d-301c-4c81-9d2a-ded83840a3aa.png)


##  Configuration in secrets.yaml
The yaml-based integration file needs 3 parameters as input. Copy the following lines in your secrets.yaml and adapt them:

    sungrow_modbus_host_ip: 192.168.178.20 # TODO update with the IP of your inverter. No default. Check your router.
    sungrow_modbus_port: 502 # TODO update with the Modbus port of your inverter. Default is '502'
    sungrow_modbus_slave: 1 #TODO update with the slave address of your inverter. Default is '1'

##  Modbus register mapping
The file **modbus_sungrow.yaml** contains the Modbus register maps and automations to set values. Copy the file to a subfolder named "integrations" (maybe create it first), which is located at the same level of your "configurations.yaml" (see screenshot). 

Include "modbus_sungrow.yaml" by adding follwing lines to your "configuration.yaml":

    homeassistant:
      packages: !include_dir_named integrations
    
Do not forget to check your configuration (Developer Tools --> hit "check configuration" and restart (it won't work without a restart!)

After the restart, some new sensors should be available. E.g., check for "Total DC power"


##  Add a nice "Energy Dashboard" like shown above
1. Create a new dashboard
2. Click "Add new Card" and select "Entities"
3. Copy the content of *PV_Info.yaml* from the repo and paste it in the new dashboard using the "raw configuration editor" (top right, the 3 dots). Ensure that the spacing keeps intact.
4. Repeat steps 1-3 with *PV_Control.yaml* for a dashboard allowing to set EMS (Energy Management System) parameters.



##  Configure the HomeAssistant energy dashboard 
![image](https://user-images.githubusercontent.com/29856783/148981502-823778d7-ebd3-4101-8060-48e0619cee4c.png)

Open the Energy settings ("Configuration" --> "Energy") and adapt the highlighted values as shown in the screenshot: 

![image](https://user-images.githubusercontent.com/29856783/148981897-23821ec4-c35e-4dd0-8ec1-02aefd0eac93.png)

Note, that only the energy values in kWh are shown in this dashboard and not the current power dissipation (in W).



# Status and future work 
I only included the most important registers, which seem to be common between a wide range of Sungrow inverter models . There are many more registers in the Sungrow documents, which I left out. 
