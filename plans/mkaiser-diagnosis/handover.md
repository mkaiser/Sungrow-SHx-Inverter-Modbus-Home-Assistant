# The maintainer's SH10RT: what a session there needs

What the repository does not record elsewhere about running the diagnosis on
the maintainer's own inverter (SH10RT, P020). `Todo.md`, `AGENTS.md` and
`.wiki/wiki/log.md` carry everything else and are current.

## The real-hardware dev instance

```text
SUNGROW_DEV_CONFIG=config-real SUNGROW_DEV_PORT=8125 scripts/dev/develop.sh
```

- Login `dev`/`dev`; mint an API token through the HA auth flow as that user.
- Entities are prefixed `hwr_sh10rt_`, e.g.
  `sensor.hwr_sh10rt_diagnosis_test_summary`.
- The plausibility store under `config-real/.storage/` is the truth. A summary
  sensor only reports when a run or a restart makes it; read the store.
- *Extended test (auto repeat)* **never survives a restart** and needs a press
  of *Diagnosis: start* to re-arm. `homeassistant.restart` kills the instance:
  nothing supervises a foreground `make dev`.
- A dev instance runs in **UTC** unless `time_zone` is set, so its displayed
  times are offset from the inverter's German local time.
- `:8125` may not reach the host browser; a walkthrough belongs on `:8123`
  (`doc/development.yaml`).

## The house

- The ledger stood at **39 of 54 established** after 2026-11-17.
- Owner settings to leave alone: `battery_max_soc` = 90 %, entry option
  `battery_max_power` = 5000 W. Both deliberate.
- Three write-side checks are still unrun here: export power limit and charge
  ceiling (need sun and a charged battery), and the upper bound of
  `battery_min_soc` (needs only a run with spare budget).

## Things that cost a session time

- **`CronCreate` jobs are session-only.** A 30-minute write-up loop does not
  survive a session ending; re-arm it with `/loop 30m <prompt>`.
- **`ruff format` reformats Python inside Markdown.** Fence an extract as
  `text`, not `python`, or `make quick` fails pointing at a `.md` file.
- **Read `make check`'s real result.** `All checks passed!` is *ruff's* line,
  not the gate's: read the exit code and pytest's own summary.
- **A verdict change raises `CHECK_REVISIONS` in the same commit**, or the fix
  never reaches ledgers that recorded the old verdict.
- **`continuous.py` is shared** by the inverter and wallbox runners: changing
  it while exercising one of them is how a wallbox regression reached a push.
