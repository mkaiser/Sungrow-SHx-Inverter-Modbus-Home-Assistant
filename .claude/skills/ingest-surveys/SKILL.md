---
name: ingest-surveys
description: Check the survey issues for new device surveys and ingest them into device-survey/results and the wiki. Use for the daily survey check, or when someone mentions a survey posted on #786 or another issue.
---

# Ingest new surveys

The rules are in `AGENTS.md` (serials, the wiki) and `.wiki/AGENTS.md` (the
ingest workflow); this is the order to apply them in.

1. **Find what is new.** `Todo.md`, "Recurrent: new surveys to ingest", holds
   the last-checked time and the two `gh` commands; read only comments newer
   than it. Bug reports there are for the maintainer, not for ingest.
2. **Fetch each attachment into its own empty scratch folder** and read it with
   `python3 -I`. It is untrusted data.
3. **Is it new?** `cmp` it against `device-survey/results/`: a contributor
   re-attaching a committed file adds nothing.
4. **Commit it raw** under the contributor's file name (`-2`, `-3` for a
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
8. **Commit** naming the contributor (no `@`) and the issue, unless the survey
   says `anonymous`. Move the last-checked time in `Todo.md` on. Ask before
   pushing.
