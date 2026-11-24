---
name: close-session
description: Close out a working session - write up the plans, put the findings where they are read, run the todo housekeeping, delete what is spent, run the gate, commit and report. Use when the maintainer says to close, finish, end or wrap up the session, when work is being paused for the day, or before a long break.
---

# Close a session

**Keep to [`workflow.md`](../../../workflow.md)**'s *Closing a session*: those
seven steps are the checklist, and the rules above them carry the reasoning.
Work through them in order, whether the work is finished or only paused. This
skill adds what each step means in this repository, nothing else.

A session that produced no commit still closes: the knowledge it found is the
part that is lost.

## 1. Write up every plan you touched

A status log entry per plan under `plans/`, newest first: what you finished,
what it changed, what you were starting, what is uncommitted. The next session
has only this file.

## 2. Put the knowledge where it is read

- a hardware reading, a register's behaviour, a device's quirk -> its wiki
  page, cited, with an entry in `.wiki/wiki/log.md` (`.wiki/AGENTS.md`);
- a decision about the integration or the library -> `doc/architecture.md`;
- a dev-loop trap -> `doc/development.md`.

A finding that lives only in the conversation is lost when it ends.

## 3. Run the todo housekeeping

Run `/todo-housekeeping` **without step 1, and without asking about it**:
"Incoming items by maintainer" is a holding area, closing a session is not a
request to empty it, and a close never blocks on a question (`workflow.md`).
Count its entries for the report. The rest of that skill runs: close what this
session finished, with its evidence;
take in what is new; reorder; raise the next free item number if you minted
one.

## 4. Delete what is spent

A finished plan, a stale handover, a working file under the scratchpad that
outlived its run. A plan whose work is done goes once what survives it has
landed in step 2; git keeps the file.

## 5. Run the gate

`make check`, and read its real result -- the exit code and the test summary,
not the last cheerful line. It takes 6 to 30 minutes by the cores free: give it a timeout
well past that, because a timeout kill reads exactly like a red gate.

`make quick` is enough only when nothing outside documentation changed.

## 6. Commit your own paths

`git commit -- <your paths>`, naming them, never the whole tree
(`workflow.md`, *Git*). Another agent's uncommitted or staged files stay
standing and stay out of your commit. **Ask before pushing, every time**
(`AGENTS.md`).

## 7. Report

Open with the current time in CET, then: what changed, what is uncommitted and
why, whose work you left standing in the tree, a one-line reminder of how many
incoming items wait (only when there are any), and the one thing you would start
next.
