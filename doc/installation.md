# Installation / Configuration

## Overview 

This does not come as an actual *integration* as per Home Assistance terminology. You can't set it up by clicking something in the Home Assistant web interface.

It is not an "installation" process per se, but more of a "configuration" process. For this, you need to add some information to the Home Assistant configuration files:

It is recommended to use the Visual Studio Code Server add-on for configuration. In the screenshot, the relevant files for the sungrow integration are highlighted, which you will need to modify:



![Home Assistant directory structure seen by VSCode](images/HA_config_vscode.drawio.svg)


## Users with multi-inverter setups: 

if you have more than one Sungrow inverter, you should download specialized yaml files for your use case. These are ```modbus_sungrow_multiple_inverters_x.yaml```, where x is the number of the used inverter (1..3). 

If you are adding another inverter to your existing modbus_sungrow installation, you should just use the inverter_2 files in addition the modbus_sungrow.yaml to keep your history of the first inverter. 

If you need more (which no one ever did), you can generate it yourself by using the python script in /scripts.

# 5 steps setup process

1. copy modbus_sungrow.yaml

    The file **modbus_sungrow.yaml** contains the Modbus register maps, template sensors and scenes to e.g., limit the power export or set a battery minimum SoC. 

    Copy the file to a subfolder named "integrations" (create it if it does not exist), which is located at the same level as your "configurations.yaml" (see screenshot above). 

    **Advanced users** familiar with git **may want** to clone the repository and reference the file via symbolic link (if you don't know what git is, just copy the file as described above :) ):
    ```bash
    bash commands: 

    > cd integrations
    > git clone https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant git_Sungrow-SHx-Inverter-Modbus-Home-Assistant
    
    # NOTE: including subdirectories within folder /integrations does not work...
    # Workaround: Create a symlink from integrations/modbus_sungrow.yaml to integrations/git_Sungrow-SHx-Inverter-Modbus-Home-Assistant/modbus_sungrow.yaml
    > ln -s git_Sungrow-SHx-Inverter-Modbus-Home-Assistant/modbus_sungrow.yaml modbus_sungrow.yaml 
    ```
    ensure that you are working on the branch "main" to get the latest stable version or branch "dev" for the latest development version.
    ```bash
     git checkout main
     git checkout dev
    ```

2. Include in configuration.yaml

    Open your configuration.yaml and add the following lines:
    ```yaml
    homeassistant:
    packages:
        # SUNGROW integration 
        modbus_sungrow: !include integrations/modbus_sungrow.yaml
    ```
    This will include the Sungrow inverter logic provided by this integration. 

    Note: in previous versions, the file was included via ```include_dir_named```, but this sometimes caused confusion with double-included files when having backup files with .yaml extensions (e.g., sungrow.bak.yaml).


3. Adjust secrets.yaml

    The YAML-based integration file needs 3 parameters as input. Copy the following lines to your secrets.yaml and adapt them:

    ```yaml
    sungrow_modbus_host_ip: 192.168.178.xxx # TODO update with the IP of your inverter. No default. Check your router.
    sungrow_modbus_port: 502 # TODO update with the Modbus port of your inverter. Default is '502'
    sungrow_modbus_device_address: 1 # TODO update with the unit id / slave address of your inverter. Default is '1'
    sungrow_modbus_battery_max_power: 5000 # TODO update with the maximum charge power of your battery in W. 
    # For >99% of all situations setting a lower value than supported does not have measureble disadvantages
    # Keep in mind that high currents put more aging-stress on the battery.
    # Max power of several sungrow batteries: SBR096: 6500W, SBR128: 8500W, SBR160: 10500W, SBR192: 13000W SBR224: 15000Wm SBR256: 17000W
    # Default is 5000 W
    ```

4. Restart Home Assistant

    check your configuration (Developer Tools --> hit "check configuration" and restart: it won't work without a restart!)
    After the restart, some new sensors should be available. E.g., check for "Total DC power"

5. Dashboards (Sungrow PV and Home Assistant Energy Dashboard)
    
    [Setup instructions here](installation.md)

