# Installation / Configuration

## Overview 

This does not come as an integration, you can set up by clicking something in the HomeAssistant GUI. 

It is not and "installation" process, but more a "configuration". For this, you need to add some information to the home assistant configuration files:

Use the Visual Studio Code Server add-on for configuration. In the screenshot, the relevant files for the sungrow integration are highlighted, which you need to modify:
![image](images/HA_config_vscode.png)


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