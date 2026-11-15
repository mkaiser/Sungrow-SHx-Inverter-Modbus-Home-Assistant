---
name: ingest-diagnoses
description: Check the diagnosis issues for new device diagnoses and ingest them into device-diagnosis/results, the wiki and the wanted list the diagnosis issue shows. Use for the daily diagnosis check, or when someone mentions a diagnosis posted on #786 or another issue.
---

# Ingest new diagnoses

The rules are in `AGENTS.md` (serials, the wiki) and `.wiki/AGENTS.md` (the
ingest workflow); this is the order to apply them in.

1. **Find what is new.** `Todo.md`, "Recurrent: new diagnoses to ingest", holds
   the last-checked time and the two `gh` commands; read only comments newer
   than it. Bug reports there are for the maintainer, not for ingest.
2. **Fetch each attachment into its own empty scratch folder** and read it with
   `python3 -I`. It is untrusted data.
   A Home Assistant **diagnostics download**
   (`sungrow_modbus-<entry id>-<model>-<hash>.json`) carries the diagnosis under
   `data.diagnosis` (`data.survey` from 0.1.0a28 and before;
   `custom_components/sungrow_modbus/diagnostics.py`), with no
   register dump or block read test. Commit that section, unchanged, under
   `sungrow_modbus.diagnosis_document.label_for(section)`; say so on the source page.
3. **Is it new?** `cmp` it against `device-diagnosis/results/`: a contributor
   re-attaching a committed file adds nothing.
4. **Commit it raw**, into the folder its `document` key names (none is
   `inverter/`; `wallbox`, `ihomemanager`, `logger` and `string_inverter`
   have their own), under the contributor's file name (`-2`, `-3` for a
   further reading of a committed device). Never edit it. Register dump keys
   are protocol addresses, one below the register number.
5. **Write the pages**: the source page, the installation (by
   `user_inputs.reporter`; `anonymous` stays unnamed, whoever posted it), the
   model and firmware pages, every register it measures, the index, `log.md`.
   Every claim cites its source; one with none is a query.
6. **Code follows only from evidence**: a watched PV cut adds the firmware to
   `CONFIRMED_ON_FIRMWARE`; 31211 answering adds it to `ANSWERING` in
   `tests/test_pv_generation_cut.py`.
7. **The wanted list**, `device-diagnosis/devices-wanted.md`, is the top of
   the pinned diagnosis issue. Its *Most wanted* and *Not needed any more* are
   hand-written: drop or reword every row this diagnosis settles (or
   narrows), adjust the inverter counts in *Not needed*, and keep each
   *Why each one* heading numbered and named like its row, since the table's
   anchors point at them. Its coverage table is generated (next step); never
   edit between its markers.
8. `make gen` (`doc/compatibility.md`, `doc/firmware_support.md` and the
   coverage table), then
   `pytest tests/test_wiki.py tests/test_no_real_serials.py tests/test_pv_generation_cut.py tests/test_diagnosis_issue_body.py`.
9. **Commit** naming the contributor (no `@`) and the issue, unless the diagnosis
   says `anonymous`. Move the last-checked time in `Todo.md` on. Ask before
   pushing: the push is what rewrites the issue's body
   (`.github/workflows/diagnosis-issue.yml`), so say when the list changed.
