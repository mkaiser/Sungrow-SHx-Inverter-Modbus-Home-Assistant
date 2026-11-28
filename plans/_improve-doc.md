# Making the documentation match the code

A prompt for one session, or one per step. Paste the **Prompt** section;
the rest is what the session fills in as it works.

## Prompt

Bring every hand-written document in this repository into line with the
code. **The code is the source of truth**: where a document and the code
disagree, the document changes, unless the exceptions below apply.

Read `AGENTS.md` first; its rules outrank this prompt. Then read
`doc/architecture.md` and `doc/development.md`, because most other pages
lean on them.

### What is in scope

| Document | Its source of truth |
| --- | --- |
| `README.md` | the integration as a user installs it: `manifest.json`, `config_flow.py`, `strings.json`, the platforms |
| `doc/architecture.md` | `src/sungrow_modbus/` and `custom_components/sungrow_modbus/`: modules, layers, coordinators and their tiers, which files are source and which generated |
| `doc/development.md`, `doc/development.yaml` | `Makefile`, `scripts/`, `pyproject.toml`, `.devcontainer/`, `.github/workflows/` |
| `doc/maintainer_setup.md` | `.github/workflows/`, `scripts/release/`, `hacs.json`, `doc/preview-mirror/sync.yml`, `.claude/skills/release/SKILL.md` |
| `doc/integration_help.md`, `doc/integration_options.md`, `doc/installing_a_preview.md`, `doc/energy_dashboard.md` | `config_flow.py`, `config_flow_schemas.py`, `strings.json` (the words a user sees on screen), `services.yaml`, `services.py`, the entity descriptions |
| `doc/integration_migration.md` | `migration.py`, `tests/test_recorder_migration.py` |
| `doc/wallbox_registers.md` | `src/sungrow_modbus/wallbox/`, `wallbox_descriptions.py` |
| `device-diagnosis/README.md`, `device-diagnosis/reference.md` | `device-diagnosis/scripts/` and the pinned wheel in its PEP 723 header |
| `custom_components/sungrow_modbus/quality_scale.yaml` | the code it cites; `tests/test_quality_scale.py` already checks part of it |
| `Todo.md` | only its claims about what exists ("done", "added", file names); its plans are not code |
| `.claude/skills/*/SKILL.md` | the scripts and documents each one points at |
| docstrings and module comments in the library and the integration | the function or module they sit on |
| wiki pages that describe the code (`.wiki/wiki/concepts/` such as `legacy-id-adoption`, `legacy-slot`, `capability-test-restore`, `protocol-addresses`) | the code they name |

### What is out of scope

- **Generated documents**: `doc/compatibility.md`, `doc/firmware_support.md`,
  `doc/entity_names.md`, `plans/_gen_text_translation_review.md`. If one is stale,
  run `make gen`; if its content is wrong, fix the generator or its input.
  Never hand-edit (`make gen-check` fails).
- **Raw sources**, which are immutable: `device-diagnosis/results/`,
  `.wiki/raw/`.
- **The YAML package's documents** live on `main` (`archive/2026-legacy` after the
  release), not on this branch.
- **Device facts** in the wiki (what a register does, what a WiNet-S
  refuses): their source is hardware, not code.
- `plans/`.

### When the code is not the truth

The code wins over prose, but not over hardware or over the hard
constraints. Do **not** change the document, and list the case under
"Code that looks wrong" instead, when:

- the document states a hardware-verified fact (the AGENTS.md table, a wiki
  page with a cited diagnosis or capability test) and the code contradicts it;
- the code would break a hard constraint the document states (legacy
  `entity_id` claims, `state_class`, the restore, 13074's probed scale, no
  real serials);
- a test asserts what the document says and the code does something else.

Fix no code in this task. Report these; the maintainer decides.

### How to work

Per document, in this order: `architecture.md`, `development.md`,
`README.md`, the user pages, `maintainer_setup.md`, the diagnosis documents,
the wiki concept pages, `Todo.md`, the skills, docstrings last.

1. **List the checkable claims.** Every file path, module, class, function,
   `make` target, script, command line, option name, config-flow step,
   form label, default value, polling interval, entity name or id, service
   and its fields, count ("four coordinators", "six layers"), and every
   statement of behaviour ("refuses", "retries once", "admins only").
2. **Check each one against the code**, by reading it, not by memory or by
   another document. Use `grep`, read the function, run the command
   (`make help`, a script's `--help`). For what a user sees, the words are
   in `strings.json` and `translations/en.json`; quote those, not a
   paraphrase.
3. **Correct what is wrong**, in the document's own voice. Remove what the
   code no longer has. Add what the code has that a reader of that page
   needs and does not find (a new module in the architecture diagram, a
   new script in "Every script", a new option on the options page). Do not
   pad a page with things its reader does not need.
4. **Note the claims you could not check** (needs hardware, needs a running
   HA) rather than guess.

A known example to start from: `doc/architecture.md`'s runtime diagram
calls the library's inverter package `inverter/` (it is `hybrid_inverter/`),
lists `capability_test` as a module (it is a package), and leaves out
`string_inverter/`, `ihomemanager/` and `logger/`; the integration box lacks
`button`, `diagnosis_entities` and `string_inverter_descriptions`. The same
file's prose, further down, already has the right names.

### Rules for the text

- **Forward-looking only.** A document states what is true now. No "was",
  "used to", "now also", "since 0.x". History goes in `.wiki/wiki/log.md`
  (for wiki pages) or the commit message, nowhere else.
- Keep each page's style: short sentences, concrete names, no marketing.
- Links: relative markdown links that resolve; file references point at
  files that exist.
- No real serial, no IP address (AGENTS.md). Stand-ins only.
- Wiki pages keep a citation on every claim, and a change to one adds an
  entry to `.wiki/wiki/log.md` in the same commit (`.wiki/AGENTS.md`).
- Mermaid diagrams must still render; check the syntax after an edit.
- German text (`doc/integration_migration.md` has some) changes with its
  English.

### Make it stay true

Prose drifts again unless a test holds it. Where a check is mechanical and
cheap, add it to the test suite, the way `tests/test_wiki.py`'s
`test_repository_paths_exist` already holds the wiki to the tree:

- every repository path in backticks or a link in `doc/*.md`, `README.md`,
  `AGENTS.md`, `device-diagnosis/*.md` and the skills exists;
- every `make <target>` named in a document is a target in the `Makefile`;
- every script under `scripts/` appears in `doc/development.md`'s "Every
  script", and every script listed there exists;
- every service in `services.yaml` appears in `doc/integration_help.md`;
- every option in the options flow appears in `doc/integration_options.md`.

One test file (`tests/test_docs.py`), fast, no network. Propose anything
less mechanical (counts, behaviour) in the report instead of testing it.

### Done means

- `make check` green (`make quick` between steps).
- One commit per document or group of related documents, message saying
  which claims changed. Do not push; ask (AGENTS.md).
- The **Status** table and **Log** below filled in: per document, how many
  claims were checked, how many were wrong, what was changed.
- A **Code that looks wrong** list, and a **Could not check** list, each
  entry with file:line and the document's sentence.

## Status

| Document | Claims checked | Wrong | State |
| --- | ---: | ---: | --- |
| `doc/architecture.md` | 112 | 17 | done (part A): socket claim, `button` PARALLEL_UPDATES, seven platforms and the other kinds' lists, `_built_from`'s three exceptions, SG platforms, `DeviceDiagnosisRunner` serves two kinds, wallbox units 2/4/248, the six capability test permissions, *Any alarm*, both diagrams (iHomeManager polling, `ev_charger`, the wallbox's managed test, `cards`, `model`, `network_names`, button descriptions), the retired mode question and `wallbox_host` stated as what holds |
| `doc/development.md` / `.yaml` | 158 | 19 | done (part A): *Layout*, *Every script* (`simulator.py`, `hassfest.sh`), port 8125 and `make dev-real`, dump 2197 addresses and 78 band reads, *controls held by test* row, the screenshot venv repair; YAML: permissions default granted, HACS testbed upgrade-only, first config step, `release.yml` runs `make ci`, 13074 per the AGENTS.md table, sdist contents, no home subnet in examples |
| `README.md` | 41 | 6 | done (part B): 180 YAML read entities (166 sensors, 14 binary), not 135; the writes list and which are firmware-gated; SBR or SBH pack, per-module entities exist; a Logger gets a diagnosis entry; the simulator setup's *I know the address* step and field labels |
| `doc/integration_help.md` | 46 | 5 | done (part B): actions take an inverter only; `forced_startup` field; refusals (test holding the controls, SG, unanswered questions, cluster partner); *Battery max charging power*; SBH out of *Not supported yet* |
| `doc/integration_options.md` | 52 | 16 | done (part B): the six `KNOWN_MISSING_OPTIONS` labels documented and the allow-list removed from `tests/test_docs.py`; *Battery* section; raw dump moved to the diagnosis section; testimony defaults empty, three of them required for an extended test; sweep 2197 addresses in eighteen bands; no diagnosis-only caveat; no Entity IDs on an SG; iHomeManager/Logger entries have no options; the wallbox test writes the managing inverter by default, the standalone test never the enable and never under 6 A |
| `doc/installing_a_preview.md` | 36 | 4 | done (part B): first screen *Where is the inverter?* (no *Perform the device diagnosis*, its screenshot removed); no testimony at setup; the name asked only for several inverters; Read-only is an SG's only mode |
| `doc/energy_dashboard.md` | 27 | 2 | done (part B): battery pack SBR or SBH with its own *Total pack charge/discharge energy*; a managed wallbox is set through the inverter. `doc/evcc.md`: 31 entity ids, option values and bounds checked, none wrong |
| `doc/integration_migration.md` | 47 | 5 | done (part B): no *Set up my inverter* step; English and German ship; the `last_reset` paragraph forward-looking; lock holds 1.5 s; archiving is for a device-scoped target, raw codes dropped on the way there. The legacy-id and slot claims agree with `migration.py` (one open item below) |
| `doc/maintainer_setup.md` | 46 | 7 | done (part A): `release.yml` runs `make ci`, the wheel gate covers the diagnosis scripts, `diagnosis.ps1`, four results folders, T052, no home subnet, the catalog guide |
| `doc/wallbox_registers.md` | 42 | 5 | done (part B): five polled components (app settings holding 21297 x16), four every 30th poll; the capability test writes 21203, 21204, 21212 with leave, never 21211; holding 21298, 21299, 21313 decoded |
| `device-diagnosis/README.md`, `reference.md` | 108 | 13 | done (part B): README: setup's first screen, timed windows and import limit in the test's list, six switches, documents for iHomeManager/Logger/SG, managed wallbox test runs on the pin, stand-in addresses. reference: schema 29, address tail defaults to yes, stand-in address examples, `check_pinned_library.py` covers every script, new iHomeManager and Logger section |
| wiki concept pages | 124 | 5 | done (part C): `network_names.mac_vendor_prefix` is the document's `mac_vendor_prefix` field; dated "since" phrasing on code behaviour (capability-test three times, legacy-id-adoption once) made forward-looking; legacy-slot's options-flow claim reported, not changed |
| `quality_scale.yaml` | 34 | 2 | done (part C): the CI coverage floor is 93.9 % (`pyproject.toml`), not 93.5 %; the README section is *What this is*, not *What it does* |
| `Todo.md` | 41 | 0 | done (part C): every path and plan link exists, the built/released claims hold (`daily_cycle.py`, 40 iHomeManager sensors, 0.1.0a57/58); T100's entry is now the maintainer's open decisions |
| `.claude/skills/` | 63 | 2 | done (part C): run-diagnosis's search range and octets example were a real home subnet and another owner's octets, now the scripts' stand-ins; scripts, flags, `make` targets, files and `workflow.md`'s seven steps hold |
| docstrings | 30 | 7 | done (part C, targeted): `SungrowWallbox` names units 2 and 4; the sweep's count in `const.py`, `dump.py` and two test docstrings, the dump test's "off unless somebody asks", the wallbox test's registers and its "below the minimum" in `const.py`, `continuous.py`'s "pause under 6 A", the `services.yaml` comment |
| `tests/test_docs.py` | — | — | added (part A): paths in backticks and links exist (README, AGENTS, `doc/*.md`, `device-diagnosis/*.md`, skills); `make` targets exist (those and `development.yaml`); *Every script* and `scripts/` agree both ways; every action in `integration_help.md`; every options-flow label in `integration_options.md`. Part B documented the six labels and removed the allow-list |

## Code that looks wrong

- Part A (architecture, development, maintainer_setup): none found. Where a
  document disagreed with a hardware fact, the document was aligned with the
  AGENTS.md table (`development.yaml`'s 13074 paragraph), not the code.

Part B (README, user pages, migration, wallbox registers, diagnosis
documents):

- `custom_components/sungrow_modbus/strings.json:2050` (and `translations/en.json`,
  `de.json`, `scripts/generate/tables/german_texts.json:158`), `const.py:359`,
  `src/sungrow_modbus/dump.py:18`, `tests/test_diagnosis_register_dump.py:6`,
  `:123`: the sweep "sweeps 2181 addresses across sixteen bands";
  `DUMP_BANDS` has 2197 in eighteen (`tests/test_dump_bands.py:41`).
  `doc/integration_options.md` says 2197 and eighteen. **Part C: comments
  and test docstrings done** (they name `DUMP_BANDS`); the user text is
  open, see the last entry below.
- `strings.json:1968`: the options' `add_devices` description ends in a
  `{devices_mode}` placeholder no code fills, and the abort
  `devices_mode_not_offered` (`:2152`) is raised nowhere. The page dropped
  "Not offered while the preview is diagnosis-only". **Open** (part C
  grepped: nothing fills or raises either), see the last entry below.
- `strings.json:2159`: `run_capability_test`'s description says "The restart
  and export-limit permissions ... are off by default"; all six default on
  (`const.py:147`). `:2183` and `:2193`: start and stop say "admin rights
  are required", where the audience is a per-entry option (`services.py`).
  `doc/integration_help.md`: "both default to administrators". **Open**,
  see the last entry below.
- `strings.json:2122` (`wallbox_max_amps`: "an offer below the 6 A minimum"
  waits for the cap) and `continuous.py:86` ("a pause under 6 A"): the
  wallbox test never offers under 6 A (`wallbox/capability_test.py:22`,
  `:1015`). `const.py:197` lists 21211 and 21232 among what the wallbox test
  writes; it writes 21203, 21204 and 21212. `doc/integration_options.md`
  and `doc/wallbox_registers.md` follow the library. **Part C: `const.py`
  (and its `CONF_WALLBOX_MAX_AMPS` comment, which listed "below the minimum"
  too) and `continuous.py` done**; `wallbox_max_amps`'s user text open.
- `scripts/dev/screenshot.py:141` waits for "Perform the device diagnosis",
  which the setup flow no longer shows, so `HA-settings-configure-integration.png`
  cannot be retaken; no document shows it any more.
- Hard constraint, legacy ids (area 5's report, `config_flow.py:2478`):
  `doc/integration_migration.md` *More than one inverter* step 3 and
  *Changing your mind* promise that switching **Entity IDs** takes the
  entry's own slot. An entry with no `CONF_LEGACY_SLOT` key, which
  `migration.stored_legacy_slot` reads as the unsuffixed slot, has its slot
  measured and written by the options flow instead, so it can be refused
  (`None`) or given another slot. The document was not changed.
- `services.yaml:33`: the comment says an ordinary entry has no diagnosis
  entities; `__init__.py`'s `DIAGNOSTIC_PLATFORMS` comment says it has them.
  **Part C: done.**
- Area 7's `sungrow_diagnosis.py:1185` summary claim: no document repeats it.
  `device-diagnosis/README.md` says the transcript carries the real serial
  and addresses and is never published, and that the last line exists
  because a pasted transcript loses `$?`; that line holds the exit code only.

Part C (wiki concept pages, `quality_scale.yaml`, `Todo.md`, skills,
docstrings, then the fixes above):

- `.wiki/wiki/concepts/legacy-slot.md:33` "Only the options flow measures
  again, for a slot stored as `None`" and `:27` "An absent key is the
  unsuffixed slot": `SungrowOptionsFlow._async_slot`
  (`config_flow.py:2470`) measures an absent key too. The same hard-constraint
  finding as area 5's above; the page was not changed.
- **The user-visible texts of the fixes above are not changed.** The sweep
  description (`strings.json:2050`), `add_devices`'s `{devices_mode}`
  (`:1968`) and the `devices_mode_not_offered` abort (`:2152`),
  `run_capability_test`'s "off by default" (`:2159`), start's and stop's
  "admin rights are required" (`:2183`, `:2193`) and `wallbox_max_amps`'s
  "an offer below the 6 A minimum" (`:2122`). Their English exists only in
  `strings.json`: `scripts/generate/descriptions.py`'s `render_strings`
  regenerates the `entity` block and keeps every other text as it finds it,
  so there is no source under `scripts/generate/` to change. The session
  was told never to edit `strings.json` by hand, and its permission check
  refused the edit, so the German (`german_texts.json:111`, `:158`, `:191`,
  `:209`, `:217`, `:221`, `:317`) stays in step, unchanged. Proposed wording
  is in `plans/_code-review.md`, *From the documents pass*; the maintainer
  decides whether those keys are edited in `strings.json` (as every earlier
  text change was) and `make gen` run.

## Could not check

Part A:

- `doc/architecture.md:13` "a Sungrow accepts very few Modbus sessions at
  once" and `:60` "running the YAML package and the integration at the same
  time produces `Connection lost`": hardware (the wiki's contention page).
- `doc/architecture.md:318` "[most of the test suite] runs in about a second":
  not timed; the library tests are not separated from the integration's.
- `doc/development.md:272`, `:292`, `:301` (two tunnels with one key, a dev
  instance in UTC, `homeassistant.restart` ending `make dev`): need the
  running environment or a tunnel.
- `doc/development.md:499` "A scratch instance on :8125": the steps need a
  running scratch instance. :8125 is also `make dev-real`'s port and
  `ha_watch.py`'s default (code review, area 9).
- `doc/development.yaml:260` (`docker_desktop`, host networking) and `:422`
  (`never_left_stopped`, restart timings): Docker's documentation and
  hardware.
- `doc/maintainer_setup.md:185` (HACS's `version_to_download()`) and `:196`
  ("can keep showing the previous commit for over an hour"): need HACS's
  source or a running 2026.11 Marketplace.

Part B:

- `README.md:25-34`, `doc/installing_a_preview.md:20-49`: the Marketplace's
  *Add from link*, the GitHub connection it asks for and the commit hash as
  the version need a running 2026.11 instance.
- `doc/integration_help.md:73-88` (the WiNet-S's forwarding, 90 s of quiet),
  `:89-125` (min SoC buying grid power, Plug&Play, surplus charging) and
  `doc/wallbox_registers.md`'s measured rows: hardware, the wiki's pages.
- `doc/integration_migration.md:40-49` (seven scenes and three automations,
  five of them setting a dropdown): the YAML package is not on this branch.
  `:297` (cost sensors unavailable until a restart) and `:322-326`
  (*Developer tools → Statistics* buttons): Home Assistant's behaviour.
- `doc/integration_options.md:84` and `device-diagnosis/README.md:160`
  (3 to 4 minutes in daylight, over 6 at night): hardware timings.
- `device-diagnosis/README.md:92` "reads for 5 to 40 minutes": not timed.
- `doc/energy_dashboard.md:9` "more than fifty energy sensors": depends on
  the hardware's capabilities; not counted on a set-up entry.

Part C:

- `quality_scale.yaml` `config-flow-test-coverage` "config_flow.py is
  covered 97 %": not measured in this pass (needs a coverage run of the
  whole flow suite). The device facts on the concept pages (what a register
  does, the measured timings) are out of scope.
- `.claude/skills/run-diagnosis/SKILL.md:82` "A wallbox, Logger or
  iHomeManager at its own address is asked only the address, reporter and
  comment": needs a run against such a device; not traced through
  `sungrow_diagnosis.py`'s question flow.

## Log

- 2026-11-28, part A: `doc/architecture.md`, `doc/development.md`,
  `doc/development.yaml`, `doc/maintainer_setup.md` checked against the code,
  the `Makefile`, `scripts/`, `.devcontainer/` and the workflows; every
  code-review finding addressed to this pass was verified and fixed.
  `tests/test_docs.py` added; the only allow-list is `KNOWN_MISSING_OPTIONS`
  for part B. Proposed rather than tested, as not mechanical: the platform
  counts and `PARALLEL_UPDATES` statements in `architecture.md` could be held
  to `PLATFORMS` and each platform module; the `development.md` dump counts
  to `dump.DUMP_BANDS` and `dump.block_count()`.
- 2026-11-28, part B: `README.md`, `doc/integration_help.md`,
  `doc/integration_options.md`, `doc/installing_a_preview.md`,
  `doc/energy_dashboard.md`, `doc/evcc.md` (entity claims only),
  `doc/integration_migration.md`, `doc/wallbox_registers.md`,
  `device-diagnosis/README.md` and `device-diagnosis/reference.md` checked
  against `strings.json`, the config and options flows, `services.py`, the
  descriptions, `migration.py`, the wallbox library and the diagnosis
  scripts with the pinned 0.1.0a58 wheel. `KNOWN_MISSING_OPTIONS` is gone
  from `tests/test_docs.py`. The setup flow's retired *Perform the device
  diagnosis* screen was the most repeated stale claim (three pages and a
  screenshot). Proposed rather than tested: the README's YAML entity count
  could be held to `legacy_entities.py` and `migration.legacy_entity_ids()`,
  and `reference.md`'s schema number to `diagnosis_document.SCHEMA`.
- 2026-11-28, part C: the wiki concept pages that name code, checked against
  it (one log entry in `.wiki/wiki/log.md`); `quality_scale.yaml`;
  `Todo.md`'s existence claims and T100's entry; the five skills; a targeted
  docstring pass for the counts, module names and defaults the earlier
  parts found stale. Then, under the code review's rules, part B's
  wrong-prose items in comments and test docstrings (recorded in
  `plans/_code-review.md`, *From the documents pass*). The user-visible
  texts are open: their English source is `strings.json` itself, which this
  session was not to edit by hand. Proposed rather than tested: a test that
  holds the sweep description in both languages to `dump.DUMP_BANDS`, once
  the text is fixed; and `quality_scale.yaml`'s coverage figures to
  `pyproject.toml`'s `fail_under`.
