---
name: run-diagnosis
description: Guide a contributor through the device diagnosis (the "survey") from this repository's dev container - find their Sungrow devices, ask the diagnosis's questions, run it, ingest what it found, then open a PR or hand over the file for issue #786. Use when someone wants to run, or asks how to run, the diagnosis or survey from VS Code, the devcontainer or a terminal here.
---

# Run a diagnosis for a contributor

The person in front of you owns the inverter, and probably not the
repository. They are giving their time and their house: say what each step
does before it runs, and ask, never assume, anything that is published or
written. The diagnosis itself is `device-diagnosis/README.md` (what it does,
the exit codes) and `device-diagnosis/reference.md` (the document); this is
the order to drive it in from here.

**You cannot answer the script's prompts**, since Bash has no terminal. So you
ask every question yourself, with AskUserQuestion, and pass each answer as its
flag (`sungrow_diagnosis.py --help`, group *answers*). A flag given is a
question not asked; one left out makes the script wait on a prompt nobody
sees.

## 1. Before anything runs

- `python3 -c "import sungrow_modbus"` must work (the dev container installs
  the tree's library). If not, use the launcher instead:
  `device-diagnosis/scripts/diagnosis.sh <host> <flags>` (uv, the PyPI pin).
- **Quiet the pollers.** A Sungrow takes very few Modbus sessions. Ask them to
  pause Home Assistant's Sungrow integration or YAML package, evcc, any
  Modbus proxy client, and `make dev` here if it has an entry for this
  inverter (`pgrep -af hass`). If they cannot, the answer to *pollers* is
  `yes`, and the run carries on.
- Tell them the reading takes 5 to 40 minutes per device and writes nothing.

## 2. Find their devices

The container cannot find them by itself: multicast (mDNS) does not cross the
Docker bridge, and the script's default network is the container's own
`172.17.x`. So ask (AskUserQuestion): *I know the address* (take it), or
*Search my network* (ask for the range, e.g. `192.168.178.0/24`: the first three
parts of their PC's or router's address, then `.0/24`).

To search, sweep each port, in the background, one after another (about a minute
each on a /24; through a VPN add `--concurrency 32 --timeout 3`):

```bash
python3 device-diagnosis/scripts/python/probe.py sweep <range> --port 502   # inverters, WiNet-S
python3 device-diagnosis/scripts/python/probe.py sweep <range> --port 503   # Logger, iHomeManager
python3 device-diagnosis/scripts/python/probe.py sweep <range> --port 516   # TLS: wallbox, WiNet-S, Logger1000
```

Then `probe.py units <host> [--port 503]` on each host that answered 502 or 503
says what it is and at which unit. A host only on 516 is a wallbox at its own
address, a Logger or an iHomeManager over TLS, or a WiNet-S's TLS port; the
diagnosis tells them apart when given the host.

Show them the list: address, port, model, and two addresses reporting the same
serial (one inverter by cable and by dongle: both readings are wanted, as
separate runs). Ask which to diagnose. **Never print a real serial or a full
address into anything tracked**; on screen it is their own data.

## 3. Ask the questions, per device

Each answer is published in the document except the host, so say that. One
AskUserQuestion call takes four questions; use two calls, then the capability
test on its own.

| Question | Flag | Notes |
| --- | --- | --- |
| Anything else polling it right now? | `--pollers no\|yes` | from step 1 |
| How the inverter is connected | `--transport` | `direct_lan` (its own LAN port), `winet_lan`, `winet_wlan`, `winet` (medium unknown), `logger`, `unsure`. **No default.** "Not sure" is a good answer; never guess one for them |
| A Modbus proxy in the path (modbus-proxy, evcc's, an HA add-on)? | `--proxy yes\|no\|unknown` | |
| A non-Sungrow inverter on the same meter? | `--other-inverter`, `--other-inverter-detail` | the detail is make and size, only after a yes |
| May the document carry the last two octets of the address? | `--address two_octets\|hidden` | show the octets themselves (`178.105`), not a description. Default is hidden |
| Who to credit (a GitHub name, or anonymous) | `--reporter` | `anonymous` stays unnamed everywhere |
| Anything else worth recording | `--comment` | free text; no serials. `''` for none |
| The battery's brand, only if it is **not** a Sungrow pack | `--battery` | `''` when it is a Sungrow, or there is none: the registers settle those |
| Unit id | `--unit` | only when `units` found the inverter somewhere other than 1, or they changed it |

A wallbox, Logger or iHomeManager at its own address is asked only the address,
reporter and comment.

**The capability test** writes to their inverter. Ask it last, alone, with
read-only as the first option and nothing marked recommended. Quote what it does
from `CAPABILITY_TEST_QUESTION` in `sungrow_diagnosis.py`: a forced charge and
discharge, feed-in limitation on, PV cut for about half a minute, a
forced-charging window, the discharge windows moved, grid import capped, and a
**stop and start of the inverter** (3 to 4 minutes without PV in daylight,
over 6 at night, and anything on the backup output loses power). Everything is
saved first and put back. In a terminal one yes covers all of it; someone who
wants only part of it gets a read-only run now, and afterwards
`sungrow_capability_test.py <host> --merge-into <document> --yes` with only the
flags they chose (its `--help`; start with `--dry-run`). Anything short of a
clear yes is `--capability-test no`. The leave is for this run only.

## 4. Run it

One device per run, so each gets its own answers:

```bash
python3 device-diagnosis/scripts/python/sungrow_diagnosis.py <host> --port <port> \
  --pollers no --transport unsure --proxy no --other-inverter no \
  --address hidden --reporter <name> --comment '' --battery '' \
  --capability-test no < /dev/null
```

Run it in the background and wait for the notification, never a polling loop.
Tell them where it stands at each phase in the output (find, questions,
transport, block test, reading, capability test, summary). It looks stuck more
than once over a slow link; dropped connections are normal.

- **Never stop a run during the capability test**: the restore runs at the end
  and is never skipped. If they ask to stop, explain that, and let it finish.
- The last line is the exit code (README, *What the last line means*). On
  **5**, tell them at once: their house is left changed. Run the `--restore`
  line the run printed (safe to repeat) and confirm it exits 0.
- 3 or 4: say what it means and offer a second run; the file is still worth
  having.

The run writes into `device-diagnosis/` (gitignored by name): the document
`<label>.json` to send, `sungrow-scan-<stamp>.log` to keep (it holds the
**real** serial and address: never commit, attach or quote it), and a
`…-wallbox-tls.json` for a wallbox at its own address.

Before you call it publishable, check the document holds no real serial: take
the serial from the transcript and `grep -c` it in the document, without
printing it. Expect 0.

## 5. Ingest, and decide whether it is news

Read the document with `python3 -I` and tell them, plainly, what their device
is and what the `features` table says. Then follow `ingest-diagnoses` steps 3
to 7 **into a scratch branch**, not their working tree's current branch.
If `git status --short` shows changes of theirs, ask them to commit or stash
first; then `git fetch origin` and
`git switch -c diagnosis/<label> origin/proper-ha-integration`.

It is **news** when any of these hold, and say which:

- a model, firmware, transport or battery not in `results/` or
  `doc/compatibility.md`;
- a row of `device-diagnosis/devices-wanted.md`'s *Most wanted* it answers;
- a capability test result the wiki has not got for this firmware (13074's
  write scale, the PV cut, a window obeyed or refused);
- a register answering, refusing or decoding differently from its wiki page.

It is **not** news when it matches a device under *Not needed any more* with
nothing above; say so honestly, and that attaching it to #786 is still
welcome but settles nothing new.

Ingest is the wiki workflow (`.wiki/AGENTS.md`): the raw document into the
folder its `document` key names, the source page, installation (by
`user_inputs.reporter`), model, firmware and register pages, `index.md`,
`log.md`; every claim cited. Code changes only where `ingest-diagnoses` step 6
says. Do not touch `Todo.md` (its last-checked time is the maintainer's).
Then `make gen` and
`pytest tests/test_wiki.py tests/test_no_real_serials.py tests/test_pv_generation_cut.py`.

## 6. PR, or the file

Ask (AskUserQuestion): **Open a pull request** with the document and the pages,
or **just give me the file** for the issue. Recommend the PR only if it is news.

**The file:** give the absolute path of each `.json` to send, and
<https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/786>.
In VS Code: right-click the file in the Explorer, *Download…*, then drag it into a
comment there. Remind them: not the `.log`. Delete the scratch branch if
nothing was committed.

**The PR:**

1. `git commit -- <only the paths you added or changed>`; the message names
   the contributor (no `@`) and #786, unless `anonymous`, and ends with the
   attribution lines.
2. `gh auth status`. If `origin` is not theirs, `gh repo fork --remote` (it
   renames the original to `upstream`).
3. **Ask before pushing**, then `git push -u origin diagnosis/<label>` and
   `gh pr create --repo mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant
   --base proper-ha-integration`, the body listing the news found, the files
   and `Refs #786`.
4. Give them the PR link, and switch back to the branch they started on.
