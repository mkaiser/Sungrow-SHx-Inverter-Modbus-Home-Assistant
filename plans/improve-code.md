# Improving the integration's code quality

What Home Assistant expects of an integration, where this one falls short,
and the order in which to close the gaps. Measured against Home Assistant
2026.10.2 and the `sofar` integration it ships, which is the reference
implementation (AGENTS.md).

## The yardstick

The **Integration Quality Scale**
(<https://developers.home-assistant.io/docs/core/integration-quality-scale/rules>)
is Home Assistant's checklist: Bronze (the basics), Silver (reliability),
Gold (user experience) and Platinum (strict typing, async dependencies). Each
core integration keeps a `quality_scale.yaml` marking every rule `done`,
`exempt` with a reason, or `todo`; `sofar`'s claims Platinum. Hassfest
enforces the file only in core, but it is a usable checklist here too.

The second yardstick is core's tooling: its ruff rule set and
`mypy --strict` for every integration on the strict-typing list.

## Already done

Config flow with reconfigure and options, unique id from the serial, a typed
`SungrowConfigEntry`, `has_entity_name`, entity categories, `PARALLEL_UPDATES`,
diagnostics, repairs, `ConfigEntryNotReady` at setup, hassfest and HACS in CI.

## Findings, in order of priority

### 1. The schemas are voluptuous; Home Assistant's are probatio

Home Assistant 2026.10 validates with `probatio`: none of the 2063 core
modules that build a schema imports voluptuous, and `homeassistant` no longer
requires it. It is installed only because `annotatedyaml` and
`hass-nabucasa` still pull it in. `config_flow.py`, `config_flow_schemas.py`
and `services.py` import it, so the integration depends on a package nobody
promises to install, and mypy flags 25 places where a voluptuous `Schema` is
handed to an API typed for a probatio one.

probatio exports every name the integration uses (`Schema`, `Required`,
`Optional`, `All`, `Any`, `Coerce`, `Range`), so the change is mechanical.

### 2. `mypy --strict` covers the library, not the integration

Platinum's `strict-typing`. Run as
`mypy --strict --explicit-package-bases custom_components/sungrow_modbus` (so
the integration is `custom_components.sungrow_modbus` and does not shadow the
library), there are 65 errors in 19 files; 25 go with item 1. The rest:

- annotations that disagree with the code: the survey's `step` callback is
  typed `Progress` (`(float, str)`) but is `(str, bool)`
  (`survey_document.py`); `RepairsFlowResult` returned as `FlowResult`
  (`repairs.py`); `DeviceInfo.via_device_id` given `str | None`
  (`coordinator.py`); `SungrowSubDeviceCoordinator` passed where the entity
  base expects `DataUpdateCoordinator[dict]` (`entity.py`);
- the `err` of an `except` reused as a loop variable (`__init__.py`, the
  firmware read at setup);
- `float(object)` / `int(object)` on a register value in `number.py`,
  `select.py`, `switch.py`, `time.py`;
- imports Home Assistant does not re-export (`recorder.get_instance`,
  `binary_sensor.BinarySensorDeviceClass`, `http.HomeAssistantView`);
- `SungrowConfigEntry` imported from the package rather than `coordinator`.

Without `--explicit-package-bases`, mypy reads the integration as the
library (same import name) and reports 143 errors, most of them that clash.

### 3. No coverage is measured

Silver's `test-coverage` (above 95 %) and Bronze's
`config-flow-test-coverage` (every flow path). `pytest-cov` is installed but
not run. The full suite (3966 tests, ~10 min with coverage) covers 94 % of
the integration. Below 95 %: `download.py` 64 %, `__init__.py` 89 %,
`config_flow.py` 91 %, `coordinator.py` 91 %, `control_test.py`,
`repairs.py` and `time.py` 92 %, `diagnostics.py` and `migration.py` 93 %,
`number.py` 94 %.

### 4. ruff runs a small part of core's rule set

`select` is E, F, W, I, UP, B, SIM, RUF, D. Violations across the repository
per family core also enables:

| Family | Hits | Note |
| --- | ---: | --- |
| BLE (blind except) | 4 | enforces AGENTS.md's "never catch `Exception` without a traceback" |
| ASYNC | 19 | 5 in the integration and library: `ASYNC109`, a `timeout` parameter on an async function |
| DTZ (naive datetimes) | 3 | |
| C4, RET, PERF, A | 9 | |
| PT (pytest style) | 36 | tests only |
| TRY | 97 | |
| SLF (private access) | 214 | mostly tests |
| T20 (print) | 215 | the survey and CLI scripts print by design; per-file ignore |
| PL, S | 673, 2708 | core enables subsets only; not worth taking wholesale |
| G, LOG, PIE, RSE | 0 | free to enable |

### 5. Gold rules not met

- **exception-translations**: `HomeAssistantError` is raised with English text
  (`number.py`, `select.py`); five uses of `translation_domain` in all.
- **icon-translations**: no `icons.json`.
- **stale-devices**: no `async_remove_config_entry_device`, so a wallbox or
  battery that went away stays in the device registry.
- **entity-disabled-by-default**: no entity is. This rule yields to the
  history constraint: a ported YAML entity stays enabled. Apply it only to
  entities the YAML package never had.

### 6. `config_flow.py` is 2197 lines with 24 steps

Readable only with care; a split by step group (connection, discovery,
topology, migration, options) would make each part testable on its own.

### 7. `getattr(entry, "runtime_data", None)`

Used in `config_flow.py` and `coordinator.py` where the typed entry would
say whether the data can be missing.

## Steps

1. Migrate voluptuous to probatio. `make check`.
2. Make `mypy --strict` pass over the integration, fixing the real
   mismatches first (survey `step`, `except` variable, `float(object)`),
   then add it to `make check` and CI.
3. Add `--cov` for the integration to CI and report; tests for uncovered
   config-flow paths; a floor once the number is known.
4. Enable G, LOG, PIE, RSE, BLE, DTZ, C4, RET, PERF, then ASYNC, one family
   per commit.
5. Write `custom_components/sungrow_modbus/quality_scale.yaml`, every rule
   marked with evidence; the `todo`s become this plan's remainder.
6. Exception translations through `scripts/generate/descriptions.py` (never
   by hand-editing `strings.json`), `icons.json`, stale-device removal.
7. Split `config_flow.py` (plan the import graph first).

Each step ends with `make check` green and a commit.

## Prompts that work for this kind of work

A prompt names one rule, one scope and its check. For example:

- "Read the quality-scale rules and write `quality_scale.yaml` as core does;
  cite the file:line that proves each `done`. No code changes."
- "Enable ruff's `BLE`; fix each hit with `_LOGGER.exception` or argue for a
  per-file ignore; `make check`."
- "List every config-flow branch with no test; write tests that raise the
  real pymodbus exception types."
- For any diff: `/code-review`, then `/simplify`, asking it to check
  AGENTS.md's hard constraints (legacy `entity_id` claims, `state_class`,
  no real serials, a failed read is not a refusal).

## Status

| Step | State | Notes |
| --- | --- | --- |
| 1. probatio | done | `make check` green; mypy errors 65 → 41 |
| 2. strict typing | done | `mypy` covers library and integration, 0 errors |
| 3. coverage | done | CI runs `--cov`; floor 93 % |
| 4. ruff families | done | A, ASYNC, BLE, C4, DTZ, G, LOG, PIE, RET, RSE enabled |
| 5. `quality_scale.yaml` | done | held to the code by `tests/test_quality_scale.py` |
| 6. Gold rules | done | exception and icon translations, stale devices |
| 7. split `config_flow.py` | proposed | waits on a decision; see the last entry |

### Log

**15:55 — steps 1 and 2.** probatio replaces voluptuous; `make check` green.
`mypy --strict` now runs over library and integration in one invocation
(`files`, `mypy_path = "src"`, `explicit_package_bases`), with
`implicit_reexport` for `homeassistant.*` as core allows. Findings and fixes:

- The survey's per-read callback was annotated `Progress` (`(float, str)`);
  it is `(str)`. New alias `Step` in `survey_document.py`.
- The setup's firmware read reused the `except` variable `err` as a loop
  variable. Renamed.
- `_async_connect` now returns the serial it has already checked, so the
  legacy-id claim and the corrections clean-up take a `str`, not
  `str | None`.
- `SungrowEntity.native_value_source` returns the library's
  `RegisterValue`, not `object`.
- `NumberEntity` bounds fall back to `super()` (HA's default) instead of a
  description's `None`.
- A sub-device's `DeviceInfo` sets `via_device_id` only when there is one.
- `RepairsFlowResult` for the repair flow; `SungrowDeviceEntity` is
  `CoordinatorEntity[SungrowSubDeviceCoordinator]`.
- `runtime_data.survey` stays `Any`: typing it `SurveyRunner | None` adds a
  `None` check at four call sites for a state that cannot occur after setup.

Risk to watch: `requirements_dev.txt` pins `homeassistant>=2026.9`, not
`==`, so a new Home Assistant release can turn `mypy` red on its own.

**Step 4.** ruff now also selects A, ASYNC, BLE, C4, DTZ, G, LOG, PIE, RET
and RSE. The integration had no hits in any of them. Findings elsewhere:

- `sungrow_survey.py` paused between devices with `time.sleep(10)` inside a
  coroutine. That froze the event loop for the pause whose purpose is to let
  the previous session close, so asyncio could not run the close. Now
  `await asyncio.sleep(10)`.
- `probe.py` caught bare `Exception` in three places; narrowed to
  `(OSError, TimeoutError)`, `ValueError` (`hosts_in`, whose
  `NetworkTooLarge` is a `ValueError`) and `(OSError, ValueError)`.
- Naive `datetime.now()` in two survey scripts: `.astimezone()` added, which
  keeps local time, so file stamps and `read_on` do not change.
- Ignored with reasons: `ASYNC109` (the discovery API's `timeout` goes to
  `wait_for` by design), `ASYNC240` in tests and the survey scripts,
  `A001` on `review_names.py`'s deliberate `print` capture, `BLE001` on
  `ha_onboard.py`'s one-line failure message.
- Not enabled: PERF (its one hit reads worse as a comprehension), TRY, SLF,
  PT, PL, S, T20 (the hit counts in the findings table; none is a defect
  class core enables wholesale).

**16:05 — step 5, and keeping it checked.** `quality_scale.yaml` marks all
54 rules: 33 done, 4 exempt, 17 todo. Writing it turned three documentation
claims I first marked done into todo: troubleshooting (the README links only
the YAML package's help), installation parameters (host, port and unit id
are not explained) and known limitations (the WiNet-S limits are in the wiki,
not on a user page). The Bronze rules not met are `config-flow-test-coverage`
and `docs-actions`.

How it stays true:

- `tests/test_quality_scale.py` takes the rule list from the installed Home
  Assistant (the union over its 374 integrations' files), so a new rule
  fails the test; requires a reason on every exemption; and decides eleven
  rules from the code in both directions -- a `done` that stops holding fails,
  and so does a `todo` the code already meets.
- `validate.yml` also runs weekly (Mondays 04:17 UTC). CI installs the
  newest Home Assistant, so a new rule or typing change shows within a week.
- `make quick` (version, generated files, ruff, mypy; ~10 s) and
  `make hooks`, which installs it as a git pre-commit hook. Opt-in; the
  ten-minute test suite stays in `make check` and CI.

**16:13 — step 6.** Three Gold rules move to done:

- **exception-translations.** Every `HomeAssistantError` and every subclass
  a person sees (`ConfigEntryNotReady`, `ConfigEntryError`, `UpdateFailed`)
  now carries a translation key; 14 new keys in `strings.json`, same English
  text. Six identical "could not write" raises share `entity.write_failed`.
  The quality-scale test's AST check covers all of these classes, the way
  `sofar` translates its `UpdateFailed` and `ConfigEntryError`.
- **icon-translations.** `icons.json` for the four actions and the survey's
  button and sensor entities; a test keeps it to keys that exist. The
  register entities keep their device-class icons: giving several hundred
  entities icons is a design task, not a rule.
- **stale-devices.** `async_remove_config_entry_device` lets an owner delete
  a battery or wallbox that this setup did not find; the inverter and
  anything found refuse. Never automatic, because a pack that misses one
  setup can answer at the next and its device carries the history.

The quality-scale test flagged `exception-translations` as soon as the code
met it, which is the behaviour it is there for.

**Step 7, proposed.** `config_flow.py` (2197 lines) holds two flows and
helpers. Home Assistant needs only the `ConfigFlow` subclass in
`config_flow.py`; the rest can move:

| New module | What moves | Lines now |
| --- | --- | --- |
| `config_flow.py` | `SungrowConfigFlow`: user, setup modes, reconfigure, move, manual, name, create | ~900 |
| `config_flow_search.py` | search, searching, sweep, pick, nothing found, identify, default network (the search steps as a mixin, since they share the flow's state) | ~450 |
| `options_flow.py` | `SungrowOptionsFlow` and its section builders, polling tiers, survey measurement | ~800 |

Cost: tests patch `config_flow.async_sweep` (15 places),
`async_hostname` (10), `async_get_temporary_unit` (7), `network` (5) and
`ONLY_SURVEY_MODE` (1); each moves with its user. Worth doing as its own
change, with the full config-flow tests before and after.

**16:30 — step 3, and the final run.** The full suite passes: 3981 passed,
2 skipped. Coverage over library and integration together is 92 %, now the
floor in CI (`[tool.coverage]` in `pyproject.toml`, `--cov` in
`validate.yml`). Least covered: `download.py` 64 %, the library's
`discovery.py` 77 %, `wallbox/discovery.py` 82 %, and
`inverter/export_scale.py` 83 % -- the last is register 13074's write-scale
probe, which writes to a house, and is the first place to add tests.

## What remains

- Bronze: `config-flow-test-coverage` (config_flow.py 91 %), `docs-actions`.
- Silver: `test-coverage` to 95 %, `docs-installation-parameters`.
- Gold: discovery (a zeroconf matcher for the WiNet-S), dynamic devices,
  entities disabled by default (new entities only), and the user docs
  (examples, use cases, supported functions, known limitations,
  troubleshooting).
- Step 7, the `config_flow.py` split, as proposed above.

**17:12 — tests where they matter most.**

- `inverter/export_scale.py` (register 13074's write-scale probe, which
  writes to a house): 83 % → 97 %. Six tests for the restore paths, against
  firmware nobody has measured: a register that moves and is put back under
  the factor it showed; one that will not go back and is reported changed;
  a put-back whose check read fails; a lifted feed-in mode restored on the
  second try, and one that will not go back. All behaved as written.
- Promoting a diagnostics entry (`tests/test_config_flow_promote.py`): no
  YAML package, its ids taken over, refused while it runs, slot unknown
  stored as `None`. This path decides where history continues and had no
  test past the checkbox.
- The options page's transport evidence
  (`tests/test_options_evidence.py`): 6100 answered, refused, busy and lost
  each say what they should.

Finding: the config flow classified the 6100 read twice, and the copies had
drifted -- the setup probe let a `TimeoutError` or `OSError` escape, which
the manual step does not catch, so a timed-out 6100 read would end the flow
with an unknown error instead of "could not be measured". Both now use
`_async_direct`. The library's control test keeps its own copy: the
integration can use only what the pinned PyPI release has.

**17:17 — documentation, the download view, and a claim corrected.**

- New user page `doc/integration_help.md`: the four actions with an example
  automation, the known limitations (sessions, what a WiNet-S does not
  forward, what is not supported), and troubleshooting. Step 4 of
  `doc/installing_a_preview.md` explains host, port and device address in
  the form's own words. Six documentation rules move to done; only
  `docs-use-cases` stays.
- `tests/test_survey_download.py`: the signed link serves the document under
  its survey name, an unsigned request without a login gets 401, no survey
  is a 404 that says so, another integration's entry is not served.
  `download.py` 64 % → 95 %.
- Correction: `quality_scale.yaml` said a WiNet-S announces itself over
  mDNS. That is not measured -- Todo.md's open question 13 -- so discovery
  is a todo that waits on hardware, not on code.

Open decisions for the maintainer, not built:

- **dynamic-devices**: a battery or wallbox is looked for at setup only.
  Looking again while running costs sessions on an inverter that grants
  few; how often, if at all, is a choice.
- **entity-disabled-by-default**: which entities the YAML package never had
  should start disabled. Ported ones must stay enabled.

Step 7 reconsidered: the proposal above listed `entity_ids`, `slot_unknown`
and `other_inverter` as duplicated between the two flows. They are not:
the names match, but the config flow's create the entry and the options
flow's carry the page's pending options and write them. That leaves the
split as moving code between files, which costs an import cycle between
`config_flow.py` and `options_flow.py` and a second patch target for the
alpha gate (`ONLY_SURVEY_MODE` is read by both flows and patched in one
module by `tests/conftest.py`). Not done: worth it only if the maintainer
finds the file hard to work in.

**17:45 — final run.** 4010 passed, 2 skipped; `make quick` clean.
Coverage 92 % → 93.1 % (floor raised to 93): `config_flow.py` 91 → 94 %,
`download.py` 64 → 95 %, `inverter/export_scale.py` 83 → 99 %.

**17:40 — the config flow's remaining paths.**

- `tests/test_config_flow_manual.py`: the address form's four refusals
  (nothing answered, no serial, an unknown model code, no code at all), the
  testimony page's route wording for 6100 answered, refused and unanswered,
  and reconfigure refusing an inverter without a serial.
- `test_config_flow_search.py`: a disabled adapter is not offered; a /16 is
  offered as the /24 around the address.
- `test_options_evidence.py`: a fitted module named beside a cable route;
  the house-load line for unread, positive and negative readings.

No defects found in these paths; they behave as their docstrings say.

**17:44 — the control test's restart.** `async_ensure_running` is what a
shutdown hook and the repair flow call to make sure an inverter is never
left stopped; its failure paths had no test. Now covered: a start still
stopped after `RESTART_RESEND_AFTER` is sent once more (and only once); an
inverter that never reports running ends the run in exit 5 with
`stopped_at` kept for the repair flow; a link that stays down after a stop
reads as "not running", never as running; a refused start command is still
watched for. A restore write tells a refusal (`REFUSED`) from a timeout or
reset (`DROPPED`), and a dry run writes nothing. All behave as written.

**17:58 — final run.** 4040 passed, 2 skipped; `make quick` clean.
Coverage 93.1 % → 93.5 %; `config_flow.py` 94 → 96 %, the library's
`control_test.py` 87 → 88 %. `docs-use-cases` is done (`doc/integration_help.md`,
"What people use it for"), so every documentation rule is.

Not pursued: the last 1.5 % to Silver's 95 %. Most of it is the optional mDNS
browser (needs the `zeroconf` extra, and whether a WiNet-S advertises is
unmeasured) and the identification of devices nobody has surveyed; tests
there would raise the number without protecting a house.

Remaining quality-scale todos: `config-flow-test-coverage` (alpha-gate
fallbacks and progress text), `test-coverage` (95 %), `discovery` and
`discovery-update-info` (hardware), `dynamic-devices` and
`entity-disabled-by-default` (maintainer decisions).
