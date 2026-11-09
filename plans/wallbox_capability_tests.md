# Wallbox capability tests in auto repeat

The wallbox capability test exists, but runs once, from a terminal, and only
asks one question (the output current's scale). This plan makes it a
collection: it runs in Home Assistant's *Extended test (auto repeat)* at gerd's
while a car charges, keeps every run, and asks every question a charging
session can answer. gerd allows every test while charging.

Device facts are on the wiki's [wallbox](../.wiki/wiki/entities/device-wallbox.md)
page; the procedure is `src/sungrow_modbus/wallbox/capability_test.py`.

## What exists

| Step | Writes | Needs | Option |
| --- | --- | --- | --- |
| output current 6, 8, 10 A | 21203 | a car charging, for leg C | `leave` |
| start/stop | 21212 | a car charging | `start_stop` |
| enable | 21211 | — | `enable` |
| phase | 21204 | nothing flowing | `phase` |

It refuses to write when 21203 reads 0 (idle, no car), restores every raw word
on a fresh session, and keeps the session alive with reads (the wallbox drops
a quiet session after 60 s and applies its fallback current).

Its document is separate from the inverter's and not in the `features`
section. Nothing in Home Assistant can start it.

## 1. Run it from Home Assistant, and keep every run

The inverter's machinery, reused rather than copied:

- **A runner** beside the inverter's (`custom_components/sungrow_modbus/diagnosis.py`),
  with a `WallboxPort` over the entry's own connection to the wallbox (the
  `wallbox_host` TLS unit 248, or unit 3 through the dongle). A port through
  the shared connection has no fresh session: `fresh=False`, and the run says
  leg B is not independent. Over the dongle only leg C counts, as on the inverter.
- **Polling held off** for the wallbox coordinator during a run, as
  `SungrowRuntimeData.async_paused()` does for the inverter; the run's own
  reads keep the session alive.
- **The snapshot** goes in the same store as the inverter's, flushed before the
  first write; a snapshot found at start-up is restored first.
- **A ledger** in the shape of `capability_test/ledger.py`: one per wallbox
  firmware (input 21226), strongest verdict per check, a decade finding outranks
  a later match, `still_missing` with why. Kept in the same diagnosis document,
  as a `wallbox_capability_test` block.
- **Auto repeat** (`continuous.py`) learns the wallbox's needs (section 3) and
  starts a wallbox run when one is due, in its own 30-minute slots. A wallbox
  run and an inverter run never overlap: one connection, one writer.
- **The counters and the summary sensor** count the wallbox's checks with the
  inverter's.

The terminal driver stays for owners without Home Assistant, and gains
`--merge-into` like the inverter's.

## 2. Checks to add

All behavioural checks read the car's draw as the highest phase current
(`Sample.draw_a`), as today.

| Check | What it writes | What it judges | Settles |
| --- | --- | --- | --- |
| **Current follow, full range** | 21203 stepped 6 A → the owner's cap in 2 A steps, then back down | draw within 1.5 A of the offer at each step; time to follow, up and down | the scale (as today), and how fast a car follows a step, which a PV-surplus controller needs |
| **Below the pilot minimum** | 21203 at 5.0 A, then 0 | refused (0x04), or accepted and the car pauses (status 3 → 4/5), and resumes when 6 A is back | what the wallbox does with an offer under 6 A: the floor for the future number entity |
| **Above the rating** | 21203 at the rating + 1 A, only if the owner's cap is at least the rating | refused, or clamped (21322 and the draw stay at the rating) | the number entity's maximum; never above the owner's cap |
| **Available current vs setting** | nothing new: every step above records 21203, 21322 and the draw together | 21322 was 16.1 A beside a 15.1 A setting: is it setting + 1 A, a separate limit, or the car's request? | which register a controller should read back |
| **Start/stop, timed** | 21212 1 → 0, as today | time to stop and time to resume, from the status and the draw | the delay an automation must allow |
| **Enable while charging** | 21211 0 → 1, as today | status 8 within 60 s, charging again after | the same, for the enable |
| **Phase switch while charging** | 21212 stop → 21204 switch → 21212 start, then the same back | the stop is seen first (status not 3, draw under 1 A) before 21204 is written; 21270 follows; the car resumes on one phase (draw on phase A only) | 1p/3p switching, the stop–switch–start order evcc uses; the contactor is never switched under load |
| **Fallback after silence** | nothing: every read stops for 75 s (Home Assistant's polling held off, evcc off) | the draw and 21322 after the session drops; the setting after a new session | the fallback current, and whether a lost Home Assistant leaves a car charging at full current |
| **Write through the dongle** | 21203 one step at unit 3 through the WiNet-S, while charging | the draw follows (leg C only: the dongle's readback is stale) | whether owners without a LAN cable to the wallbox can control it |
| **Mileage per kWh** | 21232 its own word again (no-op) | taken, not refused | the write path to the display setting |

### Plausibility, read only, every poll while charging

The wallbox's share of the sensor plausibility checks the inverter gets
(main plan, item A):

- power 21308 ≈ Σ phase V × I (21302-21307), within 5 %;
- session energy 21310 rises by ≈ ∫ power dt between polls; lifetime 21300
  rises by the same; neither ever falls;
- control pilot 21312 near 6 V while charging, 9 V connected and not, 12 V
  unplugged;
- the inverter sees it: when the current steps, the inverter's load (or grid
  import) moves by the wallbox's power step within 10 %. Settles that the
  inverter's house load includes the wallbox, which the energy dashboard needs;
- **21313 tracked against everything above**: 527 during one session and 0
  at its end. Logged with the session's elapsed minutes, energy and setting,
  to see what it counts.

## 3. What auto repeat waits for

| Check | Needs |
| --- | --- |
| current follow, below minimum, above rating, start/stop, enable, phase, dongle write | status 3 (charging) and draw ≥ 5 A |
| fallback after silence | charging, and the inverter's own run not in flight |
| plausibility | charging, then once more after the session ends |
| mileage no-op, enable when idle | any state |

A check whose need was met and still did not settle runs again in the next
slot that meets it, up to three times; then it is reported as not settled.

## 4. Safety

- **The owner's cap** is an option on the entry (`wallbox_max_amps`), default
  10 A, never above 21263's rating. The below-minimum and above-rating checks
  need the cap set explicitly.
- **The snapshot holds** 21203, 21204, 21211, 21212 and 21232, flushed before
  the first write. The restore writes the raw words back, newest first, and a
  phase switch is undone with the same stop–switch–start order.
- **No phase switch under load.** The stop must be seen before 21204 is
  written; if it is not seen within 60 s, the switch is skipped and the
  start word restored.
- **Fallback test**: the run stops reading only if 21203's snapshot is already
  restored and the cap is ≤ the setting the house had, so whatever the
  fallback is, it is not a run's leftover.
- **gerd's consent** covers every test while charging. The other owners'
  wallboxes run only the read-only plausibility until they say otherwise.

## 5. Order of work

1. The HA runner, port and snapshot store; one manual run at gerd's with a car
   charging, the existing three steps only. Settles the scale (Todo, Wallbox 3.1).
2. The ledger, the document block and auto repeat's wallbox needs.
3. The new checks, in the table's order; each with tests against a fake port
   that raises the real exception types.
4. The plausibility checks, with the inverter's.
5. A day of auto repeat at gerd's, ingested: wiki pages for the wallbox,
   `doc/wallbox_registers.md`, and `log.md`.
6. Then the entities (Todo, Wallbox 3.2): a charging current number with the
   measured floor and ceiling, an enable switch, a phase select if the switch
   was confirmed.

## Verification

- `make check`; tests in `tests/test_wallbox_capability_test.py` for each new
  check, the restore after each, and the stop-before-switch guard.
- The simulator for the plumbing (no finding).
- gerd's first run is watched live, before auto repeat is left alone with it.
