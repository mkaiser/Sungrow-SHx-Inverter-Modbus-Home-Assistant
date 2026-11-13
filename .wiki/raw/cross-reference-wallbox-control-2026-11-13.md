# Sungrow AC wallboxes: what other projects say about control, read 2026-11-13

Read after gerd's wallbox stayed disabled following the capability test of 2026-11-13
(`gerd-wallbox-capability-test-2026-11-13.md`). Facts only, in this project's words; no code or
definition copied. Licences: evcc's `charger/sungrow.go` reserves all rights; Louisbertelsmann's
repository has no licence (used with permission, for which register means what); Eisbaeeer/sungrow
and the ioBroker thread have none, so they are leads to measure; KevinD987/sungrow-ac011e is MIT;
TCzerny/ha-modbus-manager was read for what it defines.

Every source below writes **wire (protocol) addresses**; Louisbertelsmann says so explicitly
(`address: 21202 # reg 21203`). Register numbers here are this project's, one above the wire.

## Sources read

- evcc: `charger/sungrow.go` and `templates/definition/charger/sungrow.yaml` (master), and discussions
  #7104, #15079, #20739, #24225, #30193.
- ioBroker forum, topic 73087, "Sungrow Wallbox AC011E-01 erfolgreich mit Modbus eingebunden",
  pages 1-5 (some posts read only as summaries).
- KevinD987/sungrow-ac011e: README, `docs/registers.md`, `src/sungrow_ac011e/registers.py`.
- Louisbertelsmann/Sungrow-Wallbox-Modbus-HomeAssistant: `modbus_wallbox.yaml` (2025-11-06).
- TCzerny/ha-modbus-manager: `device_templates/sungrow_ac011e_wallbox.yaml` (1.1.5), issue #127.

## The register map against this project's

| Register (here) | This project | evcc | Louisbertelsmann / TCzerny | KevinD987 | ioBroker thread | Agree? |
| --- | --- | --- | --- | --- | --- | --- |
| holding 21203 | output current, 0.1 A | SetOutI; code writes A × 10 (comment says 0.01 A) | 0.1 A | 0.1 A, raw 60-160 on an 11 kW unit; **a write of 50 left it at 0** | 0.1 A, 6-63 A | yes |
| holding 21204 | phase setpoint, 0 three, 1 single | same | same | same | same | yes |
| holding 21211 | charger enable, 0/1 | Availability, 0 unavailable, 1 available | 0 disabled, 1 enabled | 0 gives status 8, 1 back to idle, "fully reversible" | Charger_Enable | yes |
| holding 21212 | start/stop, 0 start, 1 stop | RemoteControl, 0 start, 1 stop | "Remote control", 0 start, 1 stop | 0 start, 1 stop, tested with a car | START_STOP, 0 start, 1 stop | yes |
| holding 21232 | mileage, 0.1 km/kWh | — | same | — | Energy per km | yes |
| holding 21233 | minimum current | — | — | config min current, read 6 | — | yes |
| holding 21263 | working mode, named elsewhere; reads 0 | — | **holding**, 0 network, 2 plug and play, 6 EMS | — | — | yes |
| input 21263 | **rated current, 0.1 A** (reads 320) | **work mode** (0 network, 2 PnP, 6 EMS), input | nominal voltage is 21262 | work mode, input, no enum | Work_MODE, input | **no**: known conflict, ours measured 320 across mode changes |
| input 21268 | remote control status (doc only) | RemCtrlStatus, 0 disable, 1 enable | — | remote_control_status, read 1 | Charger_Status, 0 disable, 1 enable | yes |
| input 21270 | actual phase mode | PhaseSwitchStatus | same | actual phase mode | — | yes |
| input 21272 / 21273 | min / max charging power, W | — | same | 21273 nominal power | — | yes |
| input 21300 | lifetime energy, U32, low word first | U32 | U32, word swap | **U16**, 21301 a constant | U32, word swap | yes, but KevinD987 differs |
| input 21302-21307 | phase V / A, 0.1 | same | same | same | same | yes |
| input 21308 / 21310 | power W / session Wh, U32 low first | same | same | same | same | yes |
| input 21312 | control pilot, 0.01 V | — | — | same, 12.4 / 9.4 / 6.3 V = A / B / C | — | yes |
| input 21314 | start mode, 0 stopped, 1 EMS, 2 card | 1 EMS, 2 card | same as ours | no mapping | 1 EMS, 2 card | yes; nobody names **3**, read here while charging |
| input 21315 | power request | 0 enable, 1 close | — | power request | — | yes |
| input 21316 | power control allowed | PowerFlag, 0 not allowed, 1 allowed | — | same | Power_Regulation | yes |
| input 21317 | charging status 1-9 | same, 8 "Unavailable" | same, 8 "Disabled" | same; 1-4, 6, 8 measured | same | yes |
| input 21322 | available current | — | — | — | — | ours alone |

## What they say about control

- **evcc enables in this order**: availability (holding 21211) = 1, then start (21212) = 0, then the
  current (21203). Its comment: without availability, the start/stop register is not usable. It
  disables with 21212 = 1 alone and **never writes 21211 = 0**. It writes single registers only
  (function 06), keeps the session alive with a status read every 30 s, and has no case for
  status 7, 8 or 9.
- **KevinD987**: a start (21212 = 0) makes the wallbox set 21203 to 0 itself; unless the current
  is written after it, the wallbox stays in status 4 (suspended by the charge point).
- **ioBroker thread, Eisbaeeer (post 85, 2025-05-19)**: a wallbox under the inverter's energy
  management (slave mode) ignores writes to its own registers ("bringt nix"); they are for the
  standalone mode. Control then goes through the inverter's holding block at wire 33540-33549:
  33540 charging mode (160 fast charge, 161 PV surplus, 162 quantity and time, 163 user defined),
  33544 user-defined current (0.1 A, mode 163 only), 33549 surplus from the grid (85 no, 170 yes).
  Same post: the wallbox must be enabled.
- **ioBroker thread, Maddm (post 80)**: a start took 21212 written 0 → 1, 10 s, → 0; the register
  went back to 0 by itself after 90 s.
- **evcc #7104** (2024): evcc's disable left a wallbox disabled, and with it no connected car was
  seen. Fixed by re-enabling it through the iSolarCloud app's local access. Its maintainer: there
  can be only one master.
- **evcc #15079, #20739, #30193**: for control by evcc the wallbox's working mode must be EMS (set in
  its own web UI, then restarted), and it must not also be controlled by the inverter or
  iSolarCloud; several owners removed the wallbox from the iSolarCloud plant or cut its cloud link.
  #30193 (2026-05): after Sungrow firmware of 2026-05-17 (MCB LE-01.1E1.001.901.23), sessions
  stopped after minutes while the cloud link was up.
- No source reports holding 21211 or input 21268 reading 8.
