### Home Assistant Sungrow SHx integration
Sungrow SH Integration for Home Assistant for SH3.6RS, SH4.6RS, SH5.0RS, SH5.0RT, SH6.0RS, SH8.0RT, SH6.0RT, SH10RT

Tested with a **Sungrow SH10.RT** Inverter and a **PylonTech Force H1 battery**, **Home Assistant 2022.06 (current version)**.

Community tested (thanks for reporting!)
- SH10RT (via home assistant community, brix29 Axel)
- SH5.0RT(home assistant community, ptC7H12 Paul)
- SH8.0RT (github, lindehoff)
- SH5K-30 (github, ajbatchelor)

**!!! Some users reported that Sungrow ships new inverters with the WiNetS Adapter. Some users reported, that Modbus TCP is working now, some reported it isn't....**

![image](https://user-images.githubusercontent.com/29856783/177328071-b7c3fc72-35c3-4178-9276-fffb0338d30b.png)

The Modbus register mapping is based on two documents, the Sungrow support sent me by eMail. I am not sure, if I am allowed to share the files, but maybe you can successfully search for them...

    Communication Protocol of Residential Hybrid InverterV1.0.22_20201117.pdf
    10.4 Communication Protocol_String Inverter_V1.1.36_EN.pdf

# Usage

## Overview 
I use the Visual Studio Code Server add-on for configuration. In the screenshot the relevant files for the sungrow integration are highlighted:
![image](https://user-images.githubusercontent.com/29856783/156320105-6eb9448d-301c-4c81-9d2a-ded83840a3aa.png)


##  Configuration in secrets.yaml
The yaml-based integration file needs 3 parameters as input. Copy the following lines in your secrets.yaml and adapt them:

    sungrow_modbus_host_ip: 192.168.178.20 # TODO update with the IP of your inverter. No default. Check your router.
    sungrow_modbus_port: 502 # TODO update with the Modbus port of your inverter. Default is '502'
    sungrow_modbus_slave: 1 #TODO update with the slave address of your inverter. Default is '1'

##  Modbus register mapping
The file **modbus_sungrow.yaml** contains the Modbus register maps. Copy the file  to a subfolder named "integrations", which is located at the same level of your "configurations.yaml". 

Include "modbus_sungrow.yaml" by adding follwing lines to your "configuration.yaml":

    homeassistant:
      packages: !include_dir_named integrations
    
Do not forget to check your configuration and restart.


##  Add a nice "Energy Dashboard" like shown above
1. Create a new dashboard (or use the standard one)
2. Click "Add new Card" and select "Entities"
3a. Add the sensor values you want to display. I (more or less randomly) divided them into momentary power, energy, battery and other.
3b. (Alternative to 3a): Copy *sungrow_dashboard.yaml* from the repo and copy it a new dashboard using the "raw configuration editor" (top right, the 3 dots). Ensure that the spacing keeps intact.



##  Configure the HomeAssistant energy dashboard 
![image](https://user-images.githubusercontent.com/29856783/148981502-823778d7-ebd3-4101-8060-48e0619cee4c.png)

Open the Energy settings ("Configuration" --> "Energy") and adapt the highlighted values as shown in the screenshot: 

![image](https://user-images.githubusercontent.com/29856783/148981897-23821ec4-c35e-4dd0-8ec1-02aefd0eac93.png)

Note, that only the energy values in kWh are shown in this dashboard and not the current power dissipation (in W).



# Status and future work 
I only included the most important registers, which seem to be common between a wide range of Sungrow inverter models . There are many more registers in the Sungrow documents, which I left out. 

The EMS features have not been really tested...

Please let me know, if the integration works also with other Sungrow SHx models. 
The manual also mentiones following Sungrow inverters, it may also work. Leave me a feedback on this models!

SH5K-20
SH3K6
SH4K6
SH5K-V13
SH5K-30
