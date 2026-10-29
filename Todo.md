Todo.md contains only what is still to do (forward looking).
Anything done is removed here; history goes into git and `.wiki/wiki/log.md`.

Structure:

1. **Next steps** -- work that can start now, in order of priority.
2. **Open decisions** -- questions for the maintainer; nothing is built on
   them until they are answered.
3. **Blockers** -- work that waits on something outside this repository
   (hardware, daylight, a contributor). A next step that turns out blocked
   moves here, with what unblocks it.
4. **Future work** -- wanted, not scheduled; includes recurrent checks.


# Next steps

Nothing that can start now; everything open is a decision or blocked.


# Open decisions

## Naming

- Deferred up to now. Create a table (YAML | HACS) with sensor names,
  automations etc. Is there a good way for localization support, e.g.
  English / German?

## One survey issue

- Update the "wanted device surveys" list. I want to publish it on the GitHub
  page somewhere prominent and create ONE issue for all surveys. Therefore it
  would be good to have a curated overview which devices would be beneficial
  for the project (and omit duplicates). Is it possible to create an issue
  that references / embeds a .md file of this repository?

## SBR battery capability

- Grant `Capability.SUNGROW_BATTERY` when an SBR pack is found? No probe
  grants it, so the datasheet rung of `battery_ceiling` never fires
  (`number.py`, `control_test._battery_ceiling`, `config_flow.py`) and the
  bounds fall back to BMS current x voltage. Granting it **changes write
  bounds** on real houses, so it waits for a yes.


## Wallbox identifier in git history

- Holding 21250-21259 on gerd's wallbox is twenty constant ASCII digits,
  shaped like an identifier. It is now masked (`WALLBOX_MASKED`, and the
  committed wallbox document), but earlier commits of
  `device-survey/wallbox/ac22e01-gerd-anon-41346964423-wallbox-tls.json`
  carry it and are public. Rewrite history, ask gerd, or accept it?


# Blockers

1. **A charging car at gerd's.** Settles what input 21313 does over a session
   (does it go to 0 when charging stops?) and whether 21308/21310 are signed.
   Two dongle runs about five minutes apart, 90 s of quiet before each, while
   the car charges. `doc/wallbox_registers.md` has both questions. The
   same session would show what input 21267, input 21365, holding 21312 and
   start mode 3 at input 21314 do, which a reading with no car cannot.
2. **Daylight on a P022/P023 inverter.** Confirms the PV cut (holding 31211,
   #738) so the `Cut PV generation` switch can ship: a control test with
   `--cut-pv` in daylight, then its firmware into `CONFIRMED_ON_FIRMWARE`.
   [plans/cut-pv-generation.md](plans/cut-pv-generation.md).
3. **A push to the preview mirror.** `doc/preview-mirror/sync.yml` was
   changed here (the README's option name and its install link); the copy
   running in the mirror must be made byte-identical, which is a push to
   another repository and the maintainer's to make.
4. **A second wallbox's survey.** Settles whether `A25A` (words
   `[16690, 13633]`, in `test_survey_document_label.py`,
   `test_gui_survey_document.py` and `test_survey_api.py`, allowlisted in
   `test_no_real_serials.py` as the model prefix) is a prefix every wallbox
   shares or part of gerd's unit's serial; nothing in the repository says
   which. The same survey settles whether 21211-21214 identify the unit.
5. **firetribe, once more (#784).** A cable control test while the
   inverter is running (it was `Starting`) gives the first SH6.0RT-V112
   readbacks and its 13074 write scale. Their WiNet-S 0x04s are contention,
   reproduced at gerd's.


# Future work

## EVCC connection

- Hand inverter and wallbox readings to evcc, e.g. over MQTT, so evcc
  need not open a Modbus session of its own. To find out: does evcc have
  a standard configuration for that?

## iHomeManager

Never measured; survey one (port 502 or 503, unit 247). The register map is
in `doc/cross_reference_modbus_manager.md`; Sungrow's protocol PDF:
https://github.com/TCzerny/ha-modbus-manager/blob/main/docs/Communication%20Protocol%20of%20iHomeManager_V1.0.2.pdf

## Recurrent: llmwiki upstream check (every 6 weeks, next: 2026-12-10)

The wiki follows `@llmwiki/core` **0.1.2** (microsoft/llmwiki at `e09126f`).
Check upstream for changes to the index, log or frontmatter format
(`packages/core/src/init.ts`, `lint.ts`, `index-ops.ts`, `log.ts`) and to its
lint rules. If something changed, update `tests/test_wiki.py` and
`.wiki/AGENTS.md` together, and bump the version named in both and in
`.wiki/wiki/log.md`. Then move the date above six weeks on.
