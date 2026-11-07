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
  `doc/entity_names.md`, `doc/text_translation_review.md`. If one is stale,
  run `make gen`; if its content is wrong, fix the generator or its input.
  Never hand-edit (`make gen-check` fails).
- **Raw sources**, which are immutable: `device-diagnosis/results/`,
  `doc/legacy_entity_map.json`, `.wiki/raw/`.
- **The YAML package's documents**: `legacy/` and everything under it. Its
  truth is `legacy/modbus_sungrow.yaml`, which is not being changed.
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
| `doc/architecture.md` | | | |
| `doc/development.md` / `.yaml` | | | |
| `README.md` | | | |
| `doc/integration_help.md` | | | |
| `doc/integration_options.md` | | | |
| `doc/installing_a_preview.md` | | | |
| `doc/energy_dashboard.md` | | | |
| `doc/integration_migration.md` | | | |
| `doc/maintainer_setup.md` | | | |
| `doc/wallbox_registers.md` | | | |
| `device-diagnosis/README.md`, `reference.md` | | | |
| wiki concept pages | | | |
| `quality_scale.yaml` | | | |
| `Todo.md` | | | |
| `.claude/skills/` | | | |
| docstrings | | | |
| `tests/test_docs.py` | | | |

## Code that looks wrong

## Could not check

## Log
