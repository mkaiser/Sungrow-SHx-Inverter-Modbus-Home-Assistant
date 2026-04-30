# Instructions

1. Create a new dashboard, e.g. called "PV":
- Home Assistant --> Settings --> Dashboards --> "Add Dashboard" --> "New Dashboard from Scratch"
  - Title: PV
  - Click "Create"

--> A new dashboard with the name "PV" is created

2. Open the dashboard and paste the content of the provided dashboard file:
- Open the newly created dashboard "PV" (left side of HA)
- Click the pencil icon in the top right corner to "Edit Dashboard"
- Click the "three dots" menu and select "Raw configuration editor"
- Delete the pre-generated sample code
- Copy and paste the content of **dashboard.yaml** (single inverter) or **dashboard_multiple_inverters.yaml** (multi-inverter)
- Ensure that spacing is preserved
- Press "Save", close the editor, and press "Done"

---

## Multi-inverter dashboard

This dashboard is intended for **host/client setups** where:

- inverter 1 is the host inverter (with EMS access, and optionally battery and power meter)
- inverter 2 is a client inverter used primarily for additional PV production

### The dashboard contains:

- a read-only view for inverter 1, including battery, meter, grid/load, PV, and energy values  
- a read-only view for inverter 2, focused on inverter state, PV production, AC output, and backup values  
- an EMS control view with start/stop/status controls for both inverters, while battery and EMS controls are only shown for inverter 1  

The inverter 2 view intentionally omits load power, import/export power, daily import/export energy, and battery values, as these may be unavailable or meaningless on client inverters without direct meter or battery access.

**Note:** Not all multi-inverter setups use host/client mode. Retrofit setups may require a different dashboard layout.