# Cross-reference: evcc's wallbox phase switch, re-read 2026-11-26

evcc-io/evcc read again at commit `49b5a8d10` (2026-11-26), for its Sungrow wallbox
driver only, after a report that evcc switches an AC22E-01 between one and three
phases. The earlier reading is `cross-reference-evcc.md` (commit `bcea759cd9`).
evcc writes **protocol** addresses; every number below is a register number, one
above, as in the rest of this repository.

## The report

A maintainer's colleague runs an AC22E-01 from evcc's own `sungrow` charger, with
evcc's 1p/3p switch in use. **No inverter manages that wallbox**: evcc alone talks to
it. Reported, not measured here; no reading, firmware or wiring was sent.

## What was read, and under what licence

| File | Licence |
| --- | --- |
| `templates/definition/charger/sungrow.yaml` | MIT |
| `charger/sungrow.go` | **All rights reserved**, by its own header: read for which register means what, never copied |
| `charger/helper.go` (`whenDisabled`) | MIT |
| `util/modbus/` | MIT |

## What the driver does

- **The template** lists the AC011E-01 and the AC22E-01, with the capabilities
  `mA`, `1p3p`, `meter` and `dim`, unit **248** by default, over `rs485` or `tcpip`.
- **evcc's Modbus layer has no TLS** (nothing in `util/modbus/` names TLS or port 516),
  so evcc cannot use the wallbox's own LAN port, Modbus inside TLS on 516. It reaches a
  wallbox over RS485, a gateway onto RS485, or a port that speaks plain Modbus TCP.
- **Setting the phases** writes holding **21204**: 0 three phase, 1 one phase. If evcc
  believes the charge is enabled, it first stops it (holding 21212 = 1), writes 21204,
  then starts again: holding 21211 = 1 (available), 21212 = 0 (start), and the last
  current to holding 21203. A charge evcc believes disabled is switched without a stop.
- **Reading the phases** is input **21270**: 0 three phase, anything else one phase.
- **The rest is unchanged** since `bcea759cd9`: the same 16 registers, a status read
  every 30 s against the 60 s idle timeout, and the Modbus timeout settings unified.

## Against this repository

- Every register above was already in the wallbox map with the same meaning.
- `src/sungrow_modbus/wallbox/capability_test.py` already switches the phase with a car
  charging in evcc's order (stop, switch, start), for a wallbox declared standalone.
- On gerd's **managed** AC22E-01, 21204 written 1 on 2026-11-13 did not take: the actual
  mode stayed three phase and the setpoint went back to 0
  (`raw/gerd-wallbox-capability-test-2026-11-13.md`).
- So the report does not contradict that: it is a wallbox nobody else drives, the case
  the standalone test exists for, and the first one reported switching. Nobody here has
  watched a standalone wallbox switch.
