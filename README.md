## Experimental branch

# !! DO NOT USE, it breaks things !! 

This branch is meant to test things and for discussion. 

Use the discord 
[![Discord Chat](https://img.shields.io/discord/1127341524770898062.svg)](https://discord.gg/ZvYBejFkm2)
for discussing this experimental branch. 


# Development goals:
- complete restructuring, including consistent naming
- Support more than 1 inverter by duplicating "modbus_sungrow_sg1.yaml" and then search & replace "sg1" with "sg2" and "SG1 with "SG2"
- Secrets.yaml contain connection information to the inverters and additional information about the battery for individual sliders (e.g. limit the max charge/discharge power to fit your battery)
- Create a template for localisation
- naming:
  - unique_ids are now named uid_sg*, where * is the inverter number
  - Names are prefixed with SG* 
  - Automations are named more consistent (e.g., set_* and *_gui_update)


# Open issues
- How to keep the Energy Dashboard history after several sensors have been renamed??
  - sensor.Total_imported_energy --> sensor.sg1_total_imported_energy 
  - sensor.Total_exported_energy --> sensor.sg1_total_exported_energy
  - sensor.Total_PV_generation --> sensor.sg1_total_PV_generation
  - sensor.Total_battery_charge --> sensor.sg1_total_battery_charge
  - sensor.Total_battery_discharge --> sensor.sg1_total_battery_discharge

- Are there more possible side effects in just migrating?
  - Should this just be the way to go for new installations?

# Installation
- Create folder "packages" in your Home Assistant configuration folder 
- Copy modbus_sungrow_sg1.yaml to "packages"
- Copy the content of the provided secrets.yaml to your secrets.yaml. Adapt the values marked with "TODO". If you have a second, third, ..., inverter adapt accordingly.
- Add the following to your configuration.yaml:
```
homeassistant:
  packages:
    modbus_sungrow_sg1: !include packages/modbus_sungrow_sg1.yaml
    # optional:  modbus_sungrow_sg2: !include packages/modbus_sungrow_sg2.yaml
```


# Help needed
- Could anyone start on the translation?  
  - "Friendly name approach" as customization: https://www.home-assistant.io/docs/configuration/customizing-devices/ 
  - Some new stuff, I did not read much about, yet: https://developers.home-assistant.io/blog/2023/07/11/translating-services/ 
-  Create "modbus_sungrow_combined_sensors.yaml" for template sensors, e.g. total PV generation, total battery charge, total battery discharge, total imported energy, total exported energy
- Do we want to use simply a cloned version of the current "PV" Dashboard or does make an integrated for multiple inverters more sense?
# !! I am serious, DO NOT use it, yet! !! 
