# Finding every device in the search, and diagnosing it from Home Assistant

Today *Add device* → *Search my network* finds inverters. This plan makes the
same search find the other Sungrow devices, and gives each a diagnosis a user
can run from Home Assistant and send in, so reports on them start coming.

Device facts are on the wiki: [wallbox](../.wiki/wiki/entities/device-wallbox.md),
[iHomeManager](../.wiki/wiki/entities/device-ihomemanager.md),
[Logger](../.wiki/wiki/entities/device-logger.md). Where the entry model is
described: [architecture](../doc/architecture.md) (the wallbox paragraph) and
`AGENTS.md` (the one exception to *one entry is one inverter*).

## Status log -- keep this current

**Every 5 minutes while working on this plan, update this section** (and tick
the steps below): what is done, what runs right now, what is blocked, and the
next step. Another session must be able to pick up from this file alone,
without the conversation. Name uncommitted files, failing tests and anything
left half-done. Newest entry first. Check `git status` before writing, other
agents work in this tree; commit only your own files, and never push without
asking (`AGENTS.md`).

| When | Status |
| --- | --- |
| 2026-11-09 23:45 | Step 16 docs done (uncommitted): `AGENTS.md`, `doc/architecture.md`, wiki `device-wallbox`, `device-ihomemanager`, `device-logger`, `log.md`, `device-diagnosis/devices-wanted.md` items 2 and 4, `Todo.md` wallbox item (only this session's change in it). `make quick` clean; `test_wiki`, `test_no_real_serials`, `test_quality_scale` pass. Full `pytest -n 6` still running. Next: its result, then commit Part 1 + 2 by named paths (ask before push). Steps 9, 10 and the Logger open question stay open. |
| 2026-11-09 23:30 | Part 2 steps 12-15 built (uncommitted). Library: `discovery.async_identify_unit_247_on(unit)` (public, on a unit the caller holds). Integration: sweep ports now `SWEEP_PORTS` = 502-505 + 516; unit 247 asked on 502-505 and over TLS on 516 where no wallbox answered (`_async_probe_unit_247`), offered as `unit247:<host>:<port>`, entry kinds `ihomemanager`/`logger` (`const.UNIT_247_KINDS`, `CONF_TLS`), unique id `<kind>-<host>-<port>`; `_async_setup_unit_247` identifies once (not ready if silent), device from `SungrowRuntimeData.device`, platforms button + sensor, runner `unit_247_builder`/`unit_247_summary` in `device_diagnosis.py`; `links.unit_247_params`; options/reconfigure abort `unit_247_entry`; `not_on_wallbox` message now covers all three; diagnostics download carries the last document; `download._filename` names both. Strings en/de regenerated. Tests: `tests/test_unit_247_entry.py` (9), search/wallbox tests 39 pass with it; ruff, mypy clean. The old 22:35 full run was stopped (stale); a fresh `pytest -n 6` is running. Next: its result, step 16 docs, then commit (ask before push). |
| 2026-11-09 23:05 | Step 8 built (uncommitted): `custom_components/sungrow_modbus/device_diagnosis.py` (`DeviceDiagnosisRunner`, the shared runner; `wallbox_builder`, `wallbox_summary`), wired in `_async_setup_wallbox`; the wallbox entry gets *Diagnosis: start/stop* and the progress, step and finished sensors (`button.py`, `sensor.py`); `diagnosis_entities.DiagnosisEntity` takes its device from `SungrowRuntimeData.diagnosis_device`; `download._filename` names wallbox documents. Tests: `tests/test_wallbox_entry.py` 9 pass; ruff and mypy clean. Hardware: the same read outside HA at gerd's (TLS, while the dev HA polled it): 3.6 s, 299 registers, 32 values, stand-in `anon-41346964423`, no real serial in it. Not yet run from the dev HA's button: needs an HA restart, and `develop.sh` does not relaunch after one (the user's terminal). The full pytest from `make check` (started 22:35) is still running. Next: its result, then Part 2 step 12. |
| 2026-11-09 22:50 | Step 6 done: the dev HA (started 22:41 on this tree) has entry `AC22E-01` (kind wallbox) loaded beside gerd's `SH8.0RT-V112` entry; polls every 10 s in ~0.1 s, all 21 entities have values (idle, no car). Step 7: mypy clean, full pytest from `make check` still running. Next: pytest result, commit part 1, then step 8. |
| 2026-11-09 | Plan written. Part 1 (wallbox) steps 1-5 are built and uncommitted; `make check` had not finished: lint, the generated-file check and the new tests passed, the full pytest and mypy were still running. Hardware: gerd's wallbox answers over the VPN at its own address (TLS 516, unit 248; model AC22E-01, serial reads, live block reads). Next: step 6, run the entry in the dev Home Assistant against it. |

## Decisions already made

- **A wallbox at its own address is an entry of its own** (kind `wallbox`),
  read only, identified by **its own serial**. This is the one exception to one
  entry per inverter.
- **A wallbox an inverter entry already carries is still offered.** It is a
  separate device from the one read through `wallbox_host`. No skipping.
- **Only directly addressed wallboxes are searched for** (TLS 516, unit 248).
  The dongle's unit 3 stays the inverter entry's business.
- **Nothing here writes to a device.** Diagnosis part A only reads.
- **No real serial or address is published**: stand-ins only
  (`serial_anonymized_hashed`), the tail of an address only with consent. A
  fixture uses `A123456789`-shaped stand-ins, `tests/test_no_real_serials.py`.

## Part 1: the wallbox

### Built (uncommitted)

1. The sweep also looks on port 516; an address that answers is probed over TLS
   at unit 248 for a model name and its own serial
   (`_async_probe_wallbox`, `custom_components/sungrow_modbus/config_flow.py`).
2. The picker lists it ("<model> (wallbox) at <host>") and picking it creates the
   entry (`_async_add_wallbox`); found again at another address the entry
   follows it (unique id = own serial).
3. Setup (`_async_setup_wallbox`, `__init__.py`): one `SungrowWallboxCoordinator`
   with no inverter, platforms sensor and binary sensor only. No diagnosis, no
   options (options and reconfigure abort with `wallbox_entry`), diagnosis
   actions refuse it (`not_on_wallbox`), diagnostics download is a short report.
4. Strings in English and German (`strings.json`, `german_texts.json`), docs
   (`AGENTS.md`, `doc/architecture.md`, wiki page and log), `Todo.md` item.
5. Tests: `tests/test_wallbox_entry.py` (7), one search test adjusted.

### To do

6. **Run it for real.** `make dev`, Add device → Search, range gerd's LAN, pick
   the wallbox; check the device page, entities, that it sits beside gerd's
   inverter entry rather than under it, and that a reload and a restart keep it.
   The wallbox's TLS port refuses connections opened quickly in succession
   (~10 s to recover) and drops a session quiet for 60 s: keep one session, do
   not reconnect per read. Stop gerd's own Home Assistant and evcc first if
   either holds the session.
7. **Finish `make check`** and fix what it finds (mypy `--strict` on the new
   `None` inverter paths in `coordinator.py` is the likely place).
8. **A diagnosis for the wallbox entry**, so a wallbox owner can report from
   Home Assistant. Reuse the library: `wallbox/document.py` and the dump bands
   `dump.WALLBOX_TLS_BANDS` that `device-diagnosis/scripts/python/wallbox_direct.py`
   uses (a read starts on a data point's first register). Build the runner as
   described in *The shared runner* below, publish with `serial_stand_in`, and
   add *Diagnosis: start* / *stop* buttons and the progress sensors to the
   wallbox entry (platforms: button, sensor, binary sensor).
9. **Capability test for the wallbox entry** is *not* in this plan: its options
   and runner live on the inverter entry (`plans/wallbox_capability_tests.md`).
   Decide later whether the standalone entry gets its own.
10. **Moving a `wallbox_host` entry onto a standalone one** (gerd's case) is
    open: it changes entity ids, so it must claim the legacy ids
    (`.wiki/wiki/concepts/legacy-id-adoption.md`). Decide before building.
11. Ingest what a real run shows (wiki wallbox pages, `log.md`).

## Part 2: the iHomeManager and the Logger

Both answer on **unit 247**, are told apart by the type code at input 8000
(0x072A iHomeManager; 0x0705, 0x0710, 0x0718 Logger3000/1000/4000), and are
documented but never measured here. They have no measured entities and stay
that way (`AGENTS.md`: the iHomeManager is never measured).

### What exists

- Library: `src/sungrow_modbus/ihomemanager/` and `logger/` (registers,
  `readings`, `section`, `document`, `label_for`, text masking in case a gap
  holds a serial). `discovery.async_identify_unit_247` and `_identify_ihomemanager`.
- Terminal: `device-diagnosis/scripts/python/ihomemanager_direct.py` (ports
  502/503/504/505, or TLS on 516 where no wallbox answers).
- Missing: any path from Home Assistant.

### To do

12. **Search.** After the inverter and wallbox passes, ask unit 247 on each
    swept port (502, 503, 504, 505 and TLS 516) with the existing identify code,
    and offer "iHomeManager at <host>" / "Logger1000 at <host>" in the picker.
    Only a type code the library knows counts: an echoing gateway is never
    offered. Each port takes **one** TCP connection on an iHomeManager, so a port
    another client holds looks closed; the picker text says so. Add the extra
    ports to the sweep without making a /24 slower than it is (concurrency).
13. **Entries.** Kinds `ihomemanager` and `logger`: diagnosis-only, no measured
    entities. Identity: neither has a documented serial, so the entry id is the
    host and port, and the device a registry entry built from the type code. A
    device page needs at least one entity: the diagnosis's button and sensors
    provide it (the same reason `DIAGNOSTIC_PLATFORMS` exists).
14. **Diagnosis** with the shared runner, below.
15. **Tests** with simulated registers (no hardware here for either device); a
    simulator cannot produce a finding (`AGENTS.md`), so none is ingested from
    one.
16. **Docs and wiki**: `doc/architecture.md`, the two wiki pages, `log.md`,
    `doc/development.md` if a script changes; ask for a real unit in
    `device-diagnosis/devices-wanted.md`'s table (never from a named person).

## The shared runner

`custom_components/sungrow_modbus/diagnosis.py`'s `DiagnosisRunner` is built
around the inverter (`diagnosis_document.async_build`, the capability test,
`inverter_coordinator`). Do not bend it. Write a small runner for devices that
only read:

- holds polling off for the entry (`async_paused`), dumps the device's bands
  with `dump.async_dump` and `word_reader`, builds `section` then `document`
  from the device's library package, and keeps the document where the existing
  download view and the *Diagnosis result* sensor read it;
- the same state shape (`running`, `step`, `fraction`, `error`, `document`) so
  the existing sensors and buttons work unchanged;
- a read that answers nothing is a link failure, not a document
  (`register_dump.answered`), as in `ihomemanager_direct.py`;
- ask the reporter's name and comment once, as the diagnostics flow does, and
  publish an address only with consent.

## Order and checkpoints

1. Part 1 steps 6-7 (verify what is built), then commit it: ask before pushing.
2. Part 1 step 8 (wallbox diagnosis; this builds the shared runner).
3. Part 2 steps 12-16 on the shared runner.

After each: `make check` green, the status log above updated, `Todo.md`'s
wallbox item kept in step (check `git status --short Todo.md` first, it has
more than one writer).

## Open questions

- A Logger answers unit 247 and also fronts inverters at forwarding addresses
  or ports of their own: should the search say "these inverters are behind this
  Logger"? Not decided.
- Whether the standalone wallbox entry needs a capability test of its own (step 9).
- Whether a Logger on TLS 516 can collide with a wallbox on 516 in one sweep
  (the library already says: ask the wallbox first, 247 where none answers).
