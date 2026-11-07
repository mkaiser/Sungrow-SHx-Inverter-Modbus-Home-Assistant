---
name: ingest-diagnoses
description: Check the diagnosis issues for new device diagnoses and ingest them into device-diagnosis/results and the wiki. Use for the daily diagnosis check, or when someone mentions a diagnosis posted on #786 or another issue.
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
7. `make gen` (the compatibility table), then
   `pytest tests/test_wiki.py tests/test_no_real_serials.py tests/test_pv_generation_cut.py`.
8. **Commit** naming the contributor (no `@`) and the issue, unless the diagnosis
   says `anonymous`. Move the last-checked time in `Todo.md` on. Ask before
   pushing.
