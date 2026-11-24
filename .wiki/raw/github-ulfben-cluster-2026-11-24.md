# ulfben's plant is a master/slave cluster: what they posted

Read from GitHub on 2026-11-24. Addresses left out.

- Issue #43 ("SH10RT Master & Slave"), comment of 2024-08-10: a guide to adding a second inverter to the YAML package
  with the poster's own secrets layout: a "master inverter" at device address 1 and a "slave inverter" on port 502 at
  "device address for the slave" **2**.
- Issue #475 (opened by ulfben, 2025-02-23): the dashboard values "in my case ... only reflect the values from the Master
  inverter, effectively halving the true totals since the Slave inverter's contributions aren't included"; the
  second inverter's unset value was 2147483647; the summed sensors "are accurate for my plant".
- Discussion #546, 2026-10-23: "I'm also running SH10RT-V112 inverters and their 25kwh battery"; 2026-11-02: "Inverters:
  95.13 -> 95.14"; 2026-11-07: "Let me know when it's ready and I'll disable evcc and run your tests."
