## Controlling the EMS (Energy Management System)
You can set EMS parameters in the third (from left) tab of the pre-configured dashboard. 

Example to force-charge the battery:
1. Change the "EMS mode" from "Self-consumption mode" to "Forced mode"
2. Select "Force charge" as the input of the "Battery forced charge discharge cmd"
3. Limit the energy loaded by setting "max SoC" (percentage of battery)
4. You can control the charge / discharge power by 3 parameters:
- Limit the forced charge / discharge power using "Set forced charge discharge power".
- Limit the maximum battery charge power using "set max battery charge power". This value also limits the "force charge discharge power".
- Limit the maximum battery discharge power using "set max battery discharge power". This value also limits the "force charge discharge power".

Please note that changes on the input sliders may take up to 60 seconds until they affect the "battery status" entities. Hopefully this can be fixed, see [#86](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/86).