---
name: revise-todo
description: Revise Todo.md - close what is done or what was decided against, keep it forward looking, reorder by priority, take in new issues and diagnoses. Use when the maintainer asks to revise, clean up or update the todo list, when it has grown long, or at the end of a session that changed what is next.
---

# Revise Todo.md

`Todo.md` is what a session reads to know what to do next, and it holds only
that. `AGENTS.md` outranks this skill; this is the order to apply it in.

## Before the first write

`Todo.md` has more than one writer, and a revision touches all of it.

1. `git status --short Todo.md` and `git diff Todo.md`. Uncommitted changes
   that are not yours belong to another agent: leave them standing, leave
   them out of your commit, and name them in the report.
2. Re-read the file from disk. Never write back a copy read earlier in the
   session.
3. Change it as targeted replacements. A whole-file rewrite loses the other
   writer's work.

## 1. Close what is done, or what was decided

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

## 2. Keep it forward looking

Keep what the next session needs in order to act: the decision an item waits
on, the measurement that chooses between two paths, the register, firmware
and house a test applies to. Drop narrative, superseded options, and anything
the code already does.

**Before deleting a hardware result, confirm the wiki holds it, cited.** If it
does not, ingest it first (`.wiki/AGENTS.md`) and link the page from the item.
`Todo.md` must never be the only record of a run.

Aim under ~600 lines. A section that outgrows that moves its detail to a wiki
page or a `plans/` page and keeps a link.

## 3. Reorder

Within each group, in this order:

1. what the first stable release needs;
2. work a session can start now;
3. work waiting on hardware, daylight or a contributor (that is **Blockers**,
   with what unblocks it);
4. what an open decision blocks.

**Future work** stays last. Numbers run on across the groups and are cited
elsewhere as "blocker 16": if you renumber, grep `Todo.md`, `plans/`,
`doc/` and `.claude/skills/` for the old numbers and fix every reference in
the same commit. Leaving the numbers alone is usually cheaper.

## 4. Take in what is new

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

## 5. What must not change

- The six sections and the grouping by device that the file's own header
  describes.
- No real serial, no IP address (`AGENTS.md`), in an item or in a quoted
  reading.
- No history: no "was", "used to", "since 0.x". That belongs in the commit
  message and in `.wiki/wiki/log.md`.
- Links relative and resolving; a named file exists.

## Done means

- `make quick`; `pytest tests/test_wiki.py tests/test_no_real_serials.py` as
  well if the wiki or a reading changed.
- One commit, `git commit -- Todo.md` plus anything you ingested or recorded a
  decision in. Do not push; ask (`AGENTS.md`).
- A report: what closed and the evidence for each, what came in and from
  where, what you could not decide and what would decide it, and any other
  agent's changes you left out of the commit.
