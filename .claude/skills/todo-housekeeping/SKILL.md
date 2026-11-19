---
name: todo-housekeeping
description: Revise Todo.md - take the maintainer's incoming items in with them, close what is done or what was decided against, keep it forward looking, reorder by priority, take in new issues and diagnoses. Use when the maintainer asks to revise, clean up or update the todo list, when it has grown long, and as the todo step of closing a session.
---

# Revise Todo.md

**Keep to [`workflow.md`](../../../workflow.md)**: it says what belongs in
`Todo.md`, what belongs in a plan under `plans/`, how items are numbered, how
the maintainer's incoming items are handled, and how to write a file more than
one agent writes. Read it first and follow it as it stands; `AGENTS.md`
outranks both. This skill adds only the order to apply it in, and what this
project checks along the way.

Before the first write, do what `workflow.md`'s *Several agents write here at
the same time* says: `git status --short Todo.md`, `git diff Todo.md`, re-read
from disk, change only your part. Another agent's uncommitted changes stay
standing, stay out of your commit, and are named in the report.

## 1. Take the incoming items in, with the maintainer

**Incoming items by maintainer** is the first section and the first step
whenever this skill was asked for by name. Reached any other way -- closing a
session, a tidy-up nobody asked for -- **ask first** whether to address them,
and skip the step unless they say so. The section is a holding area; nothing
in it is due.

Taking it in is a conversation, not a filing job. Work through the entries one
at a time:

- small enough to just do: do it, remove it, say what became of it;
- anything else: say what you read the entry to mean, what you would make of
  it -- a numbered item in which section, a plan under `plans/`, an open
  decision, or nothing -- and what it would need. The maintainer settles it.
  Write the item or the plan only once they have, and remove the entry in that
  same edit.
- settled as not worth doing: record the decision where step 2 says, then
  remove the entry.

Never file an entry you had to guess at, and never invent an item from one.
What is left unsettled stays as the maintainer wrote it. Report what became of
every entry.

If the session is not interactive, do none of it: leave the whole section
standing and put what you would propose for each entry in the report.

## 2. Close what is done, or what was decided

An item leaves the file for one of two reasons, each needing evidence. Judge
by looking, never by how the sentence reads.

**Done** - the work exists:

- `git log --oneline --since=<the last revision of Todo.md>` and the diff of
  what those commits touched;
- the code, test or generated file the item names, read;
- `.wiki/wiki/log.md`, and the page a measurement landed on;
- the issue it cites (`gh issue view <n>`).

**Decided** - it was settled that this is not built, or is built another way.
A decision closes an item for good, so write the decision down where the next
session finds it *before* taking the item out:

- a decision about the integration or the library -> `doc/architecture.md`,
  with its reason;
- a decision about a device, a register or firmware -> its wiki page, cited,
  with an entry in `.wiki/wiki/log.md`;
- a decision an item carries on its own ("not worth a run", "yields to the
  history constraint") -> keep that sentence with whatever item still depends
  on it, or, if nothing does, put it in the commit message that removes it.

An item removed with its decision recorded nowhere is proposed again at the
next revision. Preventing that is what this step is for. An answered entry
under **Open decisions** is closed the same way: the answer goes to the
document above, not back into `Todo.md`.

What you cannot decide stays, with one line saying what would decide it.
Removing an item is not the same as doing it.

## 3. Keep it forward looking

Keep what the next session needs in order to act: the decision an item waits
on, the measurement that chooses between two paths, the register, firmware
and house a test applies to. Drop narrative, superseded options, and anything
the code already does. An entry that has grown past a sentence or two is a
plan that has not been written yet.

**Before deleting a hardware result, confirm the wiki holds it, cited.** If it
does not, ingest it first (`.wiki/AGENTS.md`) and link the page from the item.
`Todo.md` must never be the only record of a run.

Aim under ~600 lines. A section that outgrows that moves its detail to a wiki
page or a `plans/` page and keeps a link.

## 4. Reorder

Within each group, in this order:

1. what the first stable release needs;
2. work a session can start now;
3. work waiting on hardware, daylight or a contributor (that is **Blockers**,
   with what unblocks it);
4. what an open decision blocks.

**Future work** stays last. Reordering and removing never touch an item's
`T###` number (`workflow.md`); a new item takes the next free number from
`Todo.md`'s first lines and raises it in the same edit.

## 5. Take in what is new

```bash
git log -1 --format=%cI -- Todo.md          # the cutoff: the last revision
gh issue list -s all --search "updated:>=<that time>" -L 50
```

An issue becomes an item only if it is work on the integration or the library:
a defect, a wanted feature, a device that needs support. Carry its `#number`.
A support question about the YAML package, or one answered in its thread,
stays an issue.

Then run `/ingest-diagnoses` for new diagnoses. It carries its own
last-checked time, in `Todo.md`'s "Recurrent: new diagnoses to ingest";
do not sweep the diagnosis thread here, and do not copy its issue number.

Check the **Recurrent** entries' dates while you are there, and the **Status**
tables of `plans/*.md` for work that finished without reaching `Todo.md`.

## 6. What must not change

- The sections and the grouping by device that the file's own header
  describes, **Incoming items by maintainer** first among them.
- No real serial, no other owner's address (`AGENTS.md`), in an item or in a
  quoted reading.
- No history (`workflow.md`, *Documents*): no "was", "used to", "since 0.x".
- Links relative and resolving; a named file exists.

## Done means

- `make quick`; `pytest tests/test_wiki.py tests/test_no_real_serials.py` as
  well if the wiki or a reading changed.
- One commit, `git commit -- Todo.md` plus anything you ingested or recorded a
  decision in. Ask before pushing (`workflow.md`).
- A report: what became of each incoming item, what closed and the evidence
  for each, what came in and from where, what you could not decide and what would
  decide it, and any other agent's changes you left out of the commit.
