# The maintainer's SH10RT: the control test's import limit check, 2026-11-07

The control test's engine (`sungrow_control_test.py --import-limit --allow-dark --no-restart`,
commit `9133a16`) on the maintainer's SH10RT (`anon-37323352958`,
SAPPHIRE-H_B001.V000.P020, third-party battery), over its own LAN port, unit 1, at about 11:18
local time. The house's Home Assistant was stopped. The owner gave leave for the run.

## The PV isolator, before the run

To get a house with no PV in daylight, the owner opened the inverter's DC isolator. With 0 W
of PV the inverter reported **Standby** (13000 = 0x0008): the battery idle at 0 W and the house's
3.3 kW all from the grid. A first run of the control test refused to start ("The inverter
reports 'Standby' rather than running") and wrote nothing. A few minutes later the inverter was
**Running** again (13000 = 0x0040) with PV still at 0 W, the battery discharging 3299 W into a
3626 W load. The second run started then.

## The run

Conditions: PV 0 W, SoC 52.2 %, direct connection. One connection drop, re-opened.

The import limit check, as the report gives it:

| Check | Observable | Commanded | Before | During | After | Drift | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| site import limit | grid import power | 1580 W | 2192 W ±1 | 1549 W ±13 | 2206 W ±9 | 14 W | the inverter did as it was told |

- Sizing: under the forced charge of 1250 W the house imported 2209 W (median of one window).
  The cap was set halfway down to the import without the charge: 1580 W, word 158.
- During the cap, import sat at 1549 W, 2 % under the cap.
- The words probed afterwards, with the charge stopped:
  - 0: refused, `ServerDeviceFailureError`, exception 0x04 for function code 0x06;
  - 5001: refused, the same;
  - 5000: taken.

The other behavioural rows in the same run: forced discharge at 1250 W, did as it was told;
forced charge, could not tell (the house was 895 W different afterwards). Readback: eight
controls matched; 13074 kept its old value because feed-in limitation was off.

Restore: "Every setting this run touched was put back and read back at its original value."
Read raw afterwards: 32998 = 2000, 13050 = 0, 13051 = 0xCC, 13052 = 0, 13000 = 0x0040.
