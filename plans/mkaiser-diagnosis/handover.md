# Handover: the maintainer's SH10RT, after 2026-11-17

What a fresh session needs that the repository does not already record.
`Todo.md`, `AGENTS.md` and `.wiki/wiki/log.md` carry the rest and are current.

Paste the block below, or read it and carry on.

```text
Continue yesterday's hardware session at the maintainer's SH10RT (2026-11-17).
Todo.md and .wiki/wiki/log.md are current; read them. Four facts they don't record:

1. UNPUSHED: commit 9957927 ("Raise the bound checks' revision..."). Gate-verified
   (make check exit 0, 8668 passed). CI is green on the commit before it (22ac4c9).
   Ask before pushing, per AGENTS.md.

2. The real-hardware dev HA is on :8125 against config-real/ (login dev/dev), started
   detached with:
     SUNGROW_DEV_CONFIG=config-real SUNGROW_DEV_PORT=8125 scripts/dev/develop.sh
   Running since ~11:38 on 2026-11-17 with *Extended test (auto repeat)* ON.
   - It runs PRE-FIX code, so its diagnosis summary sensor shows STALE counts.
     The plausibility store is the truth, under config-real/.storage/.
   - Do NOT restart it before reading the overnight result: auto repeat never
     survives a restart and needs a press of *Diagnosis: start* to re-arm.
   - homeassistant.restart KILLS it (nothing supervises a foreground make dev).

3. Owner changes made yesterday, deliberate, keep them: battery_max_soc = 90 %,
   and the entry option battery_max_power = 5000 W.

4. Entities are prefixed hwr_sh10rt_ (e.g. sensor.hwr_sh10rt_diagnosis_test_summary).
   Mint an API token with the HA auth flow as user dev/dev.

First task: read the overnight result and write any new findings into Todo.md and the
wiki per AGENTS.md and .wiki/AGENTS.md. Specifically:
  - Did "lifetime counters never fall" and "running states" complete? Both needed
    1440 one-minute observations and were ~900 at 15:08.
  - Did any run start overnight? It should not have, in low-SoC Standby.
  - Three write-side checks remain: export power limit, charge ceiling, and
    upper bound of battery_min_soc. The first two need sun and a charged battery;
    the third only needs a run with spare budget.

Then ask me what to work on. Candidates, none blocked on weather: Todo items 10
(ad-hoc watcher helper), 11 (the other scenes on hardware), 12 (the visible
"0/23 established" wording — my call), 13 (clearing is all-or-nothing).
```

## Where the day ended

The ledger stood at **37 of 54 established**, 8 runs, auto repeat on. Both start
thresholds settled for the first time anywhere, the forced startup mode had its
first run, and *Diagnosis: stop* mid part B was watched on hardware. Everything
measured is in the wiki; everything still to do is in `Todo.md`.

The readings checks kept observing afterwards -- 932 observations by 14:40 UTC --
and turned up **their first failure anywhere**, which is ours, not the
inverter's: `daily counters reset at midnight` judges the fall by Home
Assistant's midnight, and this instance keeps UTC while the inverter keeps
German local time (`Todo.md` item 14). It is the house's one failing row, and it
will not clear by itself.

## Things that cost time, so they are written down

- **`CronCreate` jobs are session-only.** The 30-minute write-up loop does not
  survive a session ending; re-arm with `/loop 30m <prompt>`.
- **`ruff format` reformats Python inside Markdown.** Fence an extract as
  ```` ```text ````, not ```` ```python ````, or `make quick` fails pointing at a
  `.md` file. Also in `doc/development.md`.
- **Read `make check`'s real result.** `All checks passed!` is *ruff's* line, not
  the gate's. Read the exit code and pytest's own summary; a misread sent a broken
  commit to the branch on 2026-11-17.
- **A verdict change needs its `CHECK_REVISIONS` number raised in the same
  commit**, or the fix never reaches ledgers that already recorded the old verdict
  (`Todo.md` item 13).
- **`continuous.py` is shared** by the inverter and wallbox runners. Changing it
  while exercising one of them is how a wallbox regression reached a push.
- A dev instance runs in **UTC** unless `time_zone` is set, so its displayed times
  are offset.

## One decision waiting for the maintainer

`Todo.md` item 12: a fresh entry now shows *"0/23 established · waiting for: …"*
where it showed *"no runs kept"*, because watching the readings no longer waits on
auto repeat. Intended, but visible to every user and not yet seen on a real device
page.
