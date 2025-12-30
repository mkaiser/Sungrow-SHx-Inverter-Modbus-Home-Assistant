## Controlling the EMS (Energy Management System)

The recommended way to control the inverter's Energy Management System is by using the **pre-configured scenes** included in the `modbus_sungrow.yaml` file. These scenes provide a quick and reliable way to switch between different operating modes without manually adjusting individual parameters.

### Available Scenes

You can activate these scenes through Home Assistant's UI (Developer Tools → Services → `scene.turn_on`) or integrate them into automations:

- **Sungrow Self-Consumption Mode** — Prioritize using solar production to power your home and charge the battery with surplus energy.

- **Sungrow Set Zero Export Power** — Minimize or prevent exporting energy to the grid by adjusting export limits.

- **Sungrow Set Max Export Power** — Export at the inverter's maximum rated output capacity.

- **Sungrow Set Battery Bypass Mode** — Bypass the battery; solar production directly powers the load or exports to the grid.

- **Sungrow Set Battery Forced Discharge** — Force the battery to discharge, delivering power to the home or grid.

- **Sungrow Set Battery Forced Charge** — Force the battery to charge from solar production or the grid.

- **Sungrow Set Self-Consumption Limited Discharge** — Discharge the battery only to power your home; prevent exporting battery energy to the grid.

### Manual EMS Control (Advanced)

If you prefer manual control, you can adjust individual EMS parameters via the pre-configured dashboard (third tab from left):

- **EMS Mode** — Select between Self-consumption, Forced, or other modes.
- **Battery Forced Charge/Discharge Command** — Toggle battery charging or discharging.
- **Battery Min/Max SoC** — Define the safe operating range for battery state of charge.
- **Max Charge/Discharge Power** — Limit the speed of battery charging or discharging.
- **Export Power Limit** — Cap the power exported to the grid.
