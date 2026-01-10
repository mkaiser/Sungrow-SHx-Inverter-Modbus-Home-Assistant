
# Migration guide from modbus_sungrow.yaml versions before 2026

## Single Inverter setup
 0) Backup your modbus_sungrow.yaml file (keep in mind to rename the file ending from .yaml to yaml.bak to avoid a double inclusion by the deprecated (!)```!include_dir_named``` directive in configuration.yaml)

 1) Adapt ```secrets.yaml```:
    - Rename ```sungrow_modbus_slave``` to ```sungrow_modbus_device_address```
    - Add ```sungrow_modbus_battery_max_power: 5000``` (use the max supported power of your battery, see [comments in secrets.yaml](../secrets.yaml) for details)
    - Add ```sungrow_modbus_wait_milliseconds``` (choose 5 ms for LAN, 20 or higher for WiNet-S

 2) Swap your modbus_sungrow.yaml file with the [current version](../modbus_sungrow.yaml)

 3) Restart Home Assistant: ```Developer tools --> Check Configuration --> Restart```

 4) Check the Log for errors: ```Settings --> System --> Log``` (or hotkey ```c``` followed by ```log```)

 5) If everything is fine, update the [default dashboard provided in the git](../dashboards/DefaultDashboard/dashboard.yaml):
    - Open the file
    - Copy all content
    - In Home Assistant: ```Settings --> Dashboards --> Select your dashboard --> 3-dots menu (top right) --> Edit Dashboard --> 3-dots menu (top right) --> Raw configuration editor```
    - Replace all content with the copied content from the file and save

 6) Remove orphaned / unavailable sensors
 
    [see this how-to guide to cleanup](cleanup_entities.md)


 7) Update the new "Energy Dashboard" (introduced in HA 25.12)

    ```Home Assisant --> Energy --> Edit Dashboard (top right):```

     **Electricity grid**

       ```Grid consumption``` --> ```Total imported energy```

       ```Return to grid``` --> ```Total exported energy```

       ```Grid power``` --> ```Meter active power```

     **Solar Panels**

       ```Solar production energy``` --> ```Total PV generation```

       ```Solar production power``` --> ```Total DC power```

     **Home battery storage**

       ```Energy charged into the battery``` --> ```Total battery charge```

       ```Energy discharged from the battery``` --> ```Total battery discharge```

       ```Battery power``` --> ```Battery discharging power signed```

   8) If you see unavailable entities in Home Assistant after upgrading the integration due to renaming, you can follow the steps in [cleanup_entities.md](cleanup_entities.md) to remove them from your installation.
   Please note that depending on your inverter and the way to connect it to Home Assistant (Lan, WiNet-S Wifi or WiNet-S LAN) some entities might not be available in your installation.
         

## Multiple Inverters

Option A: if you have a running installation with one inverter based on modbus_sungrow.yaml and want to add a second one, use [modbus_sungrow_multiple_inverters_2.yaml](../modbus_sungrow_multiple_inverters_2.yaml) (or *_3 for a third one)

Option B: if you are setting up multiple inverters for the first time in HA, use [modbus_sungrow_multiple_inverters_1.yaml](../modbus_sungrow_multiple_inverters_1.yaml) and
[modbus_sungrow_multiple_inverters_2.yaml](../modbus_sungrow_multiple_inverters_2.yaml) or
 (or *_3 for a third one)

