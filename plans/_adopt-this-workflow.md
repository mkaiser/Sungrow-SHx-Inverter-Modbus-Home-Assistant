# Adopt this workflow

A prompt for one session in **another project**. Copy everything from
*The prompt* to the end of this file and paste it into a fresh Claude session
there; it carries the workflow and both skills with it, so nothing else needs
to be fetched.

Written for an agent that has never seen this repository. Keep it that way:
nothing below may name a device, a module, a build system or this project.

---

## The prompt

You are setting up a way of working in this project. Everything you need is in
this message: a workflow document, and two skills that carry it out.

**What to do, in order.**

1. **Read all of it first.** The three documents below are one system; the
   skills defer to the workflow for their reasoning and to this project's
   `AGENTS.md` (or `CLAUDE.md`) for its specifics.
2. **Look at the project before writing anything.** How is work tracked today
   — a todo file, issues, nothing? Is there an `AGENTS.md` or `CLAUDE.md`? Is
   there a test or lint command that serves as a gate? Does more than one
   agent or person commit into this tree?
3. **Ask me the open questions** in one round, not one at a time. You will
   need at least: what the gate command is, which files are generated and by
   what, whether this project wants the item-number scheme, and which extra
   sections its `Todo.md` needs. Do not guess any of these — the workflow is
   written to be filled in, and a wrong guess hard-codes itself.
4. **Then create the files:**
   - `workflow.md` at the repository root, exactly as given below. Do not
     adapt it: its whole point is that it is the same in every project.
   - `Todo.md` at the root, with the sections the workflow names plus the ones
     we agreed in step 3, and the next free item number on its first lines.
     If the project already has a todo list, convert it rather than replace
     it, and show me the mapping before you write.
   - `.claude/skills/todo-housekeeping/SKILL.md` and
     `.claude/skills/close-session/SKILL.md`, from the two skills below, with
     every `<angle-bracket placeholder>` replaced by this project's real
     answer from step 3. A placeholder left standing is a bug.
   - A short section in `AGENTS.md` (create it if absent) naming: the gate
     command, the generated files and their generators, where a decision about
     the code is written down, where a measured or external fact is written
     down, and the project's extra `Todo.md` sections. The workflow and the
     skills both point at `AGENTS.md` for exactly these.
5. **Do not invent project rules.** If something in the workflow has no
   sensible home here — say, there is nowhere that measured facts go — tell me
   rather than inventing a file for it.
6. **Report** what you created, what you converted, and every question still
   open.

**Two things to understand before you start.**

- The workflow is deliberately project-independent, and `AGENTS.md` outranks
  it. That split is what lets the same file live in many repositories: the
  rule is here, the project's own detail is there.
- The skills are not automation. They are the order to apply the workflow in,
  and the evidence each step needs. Both of them stop and ask the maintainer
  at the points where guessing would do damage.

---

## File 1 of 3 — `workflow.md`

Create this at the repository root, verbatim.

--- BEGIN workflow.md ---

# Workflow: how work is written down, and how agents share one tree

Project-independent working rules: what goes in `Todo.md`, what goes in a plan
under `plans/`, how items are numbered, and how several agents commit into one
repository without taking each other's work.

This file is meant to be copied into other projects as it stands. It names no
devices, no modules and no build system; where a rule needs a project's own
detail -- which files are generated, what the gate is called, which sections
`Todo.md` uses -- that detail lives in the project's `AGENTS.md`, which
outranks this file.

## Git

- **Never `git push` without asking the maintainer first, every time.** An
  earlier "commit and push" covers that one change, not the next one.
  Committing when asked is fine; pushing is a separate question.
- **Commit only the files you changed**, by naming them:
  `git commit -- <your paths>`. A plain `git commit` takes everything staged,
  another agent's staged files included. Never `git add -A` or `git add .`
  across the tree.
- **Run the project's gate before committing** (`AGENTS.md` names it), and
  read its real result: the last command's cheerful line is not the gate's
  verdict. Read the exit code and the test summary.
- **Say what you did not commit.** Another agent's uncommitted or staged files
  stay out of your commit, and your report names them.
- **A commit message carries the *why*.** It is the only record of a decision
  that changed no file.

## Several agents write here at the same time

Their changes can sit uncommitted, or staged, beside yours.

Before every write to a file more than one agent writes -- `Todo.md` above all:

1. `git status --short <file>` and `git diff <file>`, to see changes that are
   not yours;
2. re-read the file from disk; never write back a copy read earlier in the
   session;
3. change only your part, as a targeted replacement. A whole-file rewrite
   loses the other writer's work.

If another agent's edits to it are uncommitted, leave them out of your commit,
or wait until they are committed, and say so.

## Todo.md

`Todo.md` is what a session reads to know what to do next, and it holds only
that. It is **forward looking**: anything done is removed from it, and its
history lives in git and in the project's log.

### Incoming items by maintainer

`Todo.md` opens with **Incoming items by maintainer**: a section the
maintainer writes into in whatever form suits them -- a line, a paragraph, a
pasted link, a half-formed idea -- without having to shape it into an item.

- **It is a holding area, not a queue.** An entry there is not work that is
  due: it carries no priority and never displaces the order below it. A
  session deciding what to work on reads the sections below, not this one.
- **It is taken in only when the maintainer asks for it**, as the first step
  of the project's todo housekeeping (`AGENTS.md` names it), and it is taken
  in *with* them: the agent says what it reads each entry to mean and what it
  would make of it, the maintainer settles it, and only what they agreed is
  written into the file. An agent that had to guess asks instead of filing.
- **Closing a session, ask whether to address them.** Asking is the whole
  obligation; their answer decides. Unasked, the section is left alone.
- **An entry goes only in the edit that disposes of it**, with one line saying
  what became of it. Nothing is half-taken: what is not settled stays as the
  maintainer wrote it.
- **Only the maintainer writes new entries there.** An agent's own note to a
  later session is a numbered item or a plan's status log, never this section.
- It is the one part of `Todo.md` with no sentence limit and no item number.
  Shaping it is the reader's job, not the writer's.

### Structure

1. **Next steps** -- work that can start now, in order of priority.
2. **Open decisions** -- questions for the maintainer; nothing is built on
   them until they are answered.
3. **Blockers** -- work that waits on something outside this repository. A
   next step that turns out blocked moves here, with what unblocks it.
4. **Release** -- what the next release needs, and what follows it.
5. **Future work** -- wanted, not scheduled; includes recurrent checks.

A project adds the sections its own work needs, and groups the longer ones by
whatever its work divides into. Both are recorded in `AGENTS.md`.

### How long an entry may be

An entry is **one sentence** saying what is to be done, then:

- a link to its plan under `plans/`, where there is one;
- its **requirements / dependencies**: what must exist, be decided or be
  reachable before it can start, named as links (another item's number, an
  issue, a document, hardware, somebody's answer).

Everything else -- the reasoning, the measurements, the options weighed, the
steps, the status log -- goes in the plan, not here. An entry that grows a
second paragraph is a plan that has not been written yet.

## plans/

**When a next step or future work is planned, the plan goes in `plans/` and
`Todo.md` links to it.** One file per piece of work, named after the work and
not after a session.

A plan carries:

- what is to be built or measured, and why;
- the decisions already made, each with who made it and when;
- the steps, in order, each one checkable;
- a **status log**, newest entry first, so another session can pick the work
  up from the file alone: what is done, what is running, what is blocked, what
  is next, which files are uncommitted.

**Update the status log after every subtask**, not at the end of the session:
two or three lines -- what you just finished, what it changed, what you are
starting next, and anything uncommitted or half-done. A session can end
without warning, and the next one has only this file. A step finished and not
written down is a step the next session repeats.

Rules:

- **A plan is deleted when its work is done.** What survives it goes where it
  is read: a decision about the code to the architecture document, a measured
  fact to wherever the project keeps measured facts, an open question back to
  `Todo.md`. Git keeps the file.
- **A finished plan is not a changelog.** History goes to git and the
  project's log; a plan states what is still true.
- **A plan's filename starts with the item numbers it serves**, then the
  work's name: `T017-daily-counter-reset.md`. `plans/` then sorts by item, and
  a plan is found from `Todo.md` without opening it. Several items to one plan
  join their numbers with `-`, a contiguous run written first-last:
  `T003-T004-...`, `T047-T053-...`. Numbers are never reused, so a name goes
  stale only when a further item joins the plan.
- **A leading `_` marks a file under `plans/` that is not a plan**: `_` alone
  for a prompt meant to be reused across sessions, `_gen_` for a generated
  file -- which is listed among the project's generated files in `AGENTS.md`,
  and is never hand-edited. Both sort clear of the numbered plans.
- **Check `plans/` before writing a new one**, so two files do not describe
  the same work.
- **A handover is a plan for one piece of work or one run**, not for a
  session: write what the next session needs, not what the last one did.

## Closing a session

Before you stop -- whether the work is finished or only paused -- in this
order. Every line is a rule from above, where its reasoning is; this is the
checklist, not a second statement of them.

1. **Write up every plan you touched**: its status log entry.
2. **Put the knowledge where it is read.** A finding that lives only in the
   conversation is lost.
3. **Run the project's todo housekeeping** (`AGENTS.md` names it): close what
   this session finished, take in what is new, reorder, and raise the next
   free item number if you minted one. **Ask whether to take the incoming
   items in**, and take them in only if the maintainer says so.
4. **Delete what is spent**: a finished plan, a working file, a stale handover.
5. **Run the gate** and read its real result.
6. **Commit your own paths.** Ask before pushing.
7. **Report**: what changed, what is uncommitted and why, whose work you left
   standing in the tree, and the one thing you would start next.

## Item numbers

Numbers in `Todo.md` go stale when the items around them are removed, so a
reference such as "blocker 16" stops meaning what it meant. Items therefore
carry an **internal issue number that is assigned once and never changes**.

- The form is **`T###`**: `T001`, `T042`. It is the repository's own number
  and is never written as `#42`, which means an issue in the tracker.
- **Numbers are minted incrementally and never reused.** `Todo.md`'s first
  line records the next free number; taking a number raises it in the same
  edit.
- **Every item gets one**, in every section. The section an item sits in may
  change; its number does not.
- **Never renumber, and leave a gap standing.** A removed item's number is
  retired with it.
- A plan file names the number it serves, under its title. A commit, a
  document or another item refers to the work by its number.

## Documents

- **Edit the source, not the output.** A generated file is rewritten by its
  generator; `AGENTS.md` lists which files those are and what regenerates
  them, and the gate fails on a hand edit.
- **A document states what is true now.** History goes to git and to the one
  file the project keeps history in -- not into comments, not into a document
  that describes how something works today.
- **Every document is for a reader**: name who it is for, and write to what
  that reader needs to know.

--- END workflow.md ---

---

## File 2 of 3 — `.claude/skills/todo-housekeeping/SKILL.md`

Replace every `<placeholder>` before writing.

--- BEGIN todo-housekeeping/SKILL.md ---

---
name: todo-housekeeping
description: Revise Todo.md - take the maintainer's incoming items in with them, close what is done or what was decided against, keep it forward looking, reorder by priority, take in new work. Use when the maintainer asks to revise, clean up or update the todo list, when it has grown long, and as the todo step of closing a session.
---

# Revise Todo.md

**Keep to `workflow.md`**: it says what belongs in `Todo.md`, what belongs in
a plan under `plans/`, how items are numbered, how the maintainer's incoming
items are handled, and how to write a file more than one agent writes. Read it
first and follow it as it stands; `AGENTS.md` outranks both. This skill adds
only the order to apply it in, and what this project checks along the way.

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
  same edit;
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
- <the project's log of measured or external facts, and the page a finding
  landed on>;
- the issue it cites (`gh issue view <n>`, where the project uses a tracker).

**Decided** - it was settled that this is not built, or is built another way.
A decision closes an item for good, so write the decision down where the next
session finds it *before* taking the item out:

- a decision about the code -> <the project's architecture or decisions
  document>, with its reason;
- a decision about an external fact -> <where the project keeps those>, cited;
- a decision an item carries on its own -> keep that sentence with whatever
  item still depends on it, or, if nothing does, put it in the commit message
  that removes it.

An item removed with its decision recorded nowhere is proposed again at the
next revision. Preventing that is what this step is for. An answered entry
under **Open decisions** is closed the same way: the answer goes to the
document above, not back into `Todo.md`.

What you cannot decide stays, with one line saying what would decide it.
Removing an item is not the same as doing it.

## 3. Keep it forward looking

Keep what the next session needs in order to act: the decision an item waits
on, the measurement that chooses between two paths, the conditions a piece of
work applies to. Drop narrative, superseded options, and anything the code
already does. An entry that has grown past a sentence or two is a plan that
has not been written yet.

**Before deleting a result that was expensive to obtain, confirm the project's
own record holds it, cited.** If it does not, record it first and link it from
the item. `Todo.md` must never be the only record of a run.

Aim under ~600 lines. A section that outgrows that moves its detail to a
`plans/` page or the project's own records, and keeps a link.

## 4. Reorder

Within each group, in this order:

1. what the next release needs;
2. work a session can start now;
3. work waiting on something outside the repository (that is **Blockers**,
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

An issue becomes an item only if it is work on this project: a defect, a
wanted feature, something that needs support. Carry its `#number`. A question
answered in its own thread stays an issue.

Check any **Recurrent** entries' dates while you are there, and the status
logs of `plans/*.md` for work that finished without reaching `Todo.md`.

## 6. What must not change

- The sections and the grouping that the file's own header describes,
  **Incoming items by maintainer** first among them.
- <Anything the project forbids in a tracked file -- secrets, personal data,
  other people's identifiers. Name them here.>
- No history (`workflow.md`, *Documents*): no "was", "used to", "since 0.x".
- Links relative and resolving; a named file exists.

## Done means

- <the project's fast gate>; plus any test that covers what you touched.
- One commit, `git commit -- Todo.md` plus anything you recorded a decision
  in. Ask before pushing (`workflow.md`).
- A report: what became of each incoming item, what closed and the evidence
  for each, what came in and from where, what you could not decide and what
  would decide it, and any other agent's changes you left out of the commit.

--- END todo-housekeeping/SKILL.md ---

---

## File 3 of 3 — `.claude/skills/close-session/SKILL.md`

Replace every `<placeholder>` before writing.

--- BEGIN close-session/SKILL.md ---

---
name: close-session
description: Close out a working session - write up the plans, put the findings where they are read, run the todo housekeeping, delete what is spent, run the gate, commit and report. Use when the maintainer says to close, finish, end or wrap up the session, when work is being paused for the day, or before a long break.
---

# Close a session

**Keep to `workflow.md`**'s *Closing a session*: those seven steps are the
checklist, and the rules above them carry the reasoning. Work through them in
order, whether the work is finished or only paused. This skill adds what each
step means in this repository, nothing else.

A session that produced no commit still closes: the knowledge it found is the
part that is lost.

## 1. Write up every plan you touched

A status log entry per plan under `plans/`, newest first: what you finished,
what it changed, what you were starting, what is uncommitted. The next session
has only this file.

## 2. Put the knowledge where it is read

- a measured or external fact -> <where the project keeps those>, cited;
- a decision about the code -> <the project's architecture or decisions
  document>;
- a trap in the development loop -> <the project's development document>.

A finding that lives only in the conversation is lost when it ends.

## 3. Run the todo housekeeping

Run `/todo-housekeeping`. **Ask first whether to take the incoming items in**
-- "Incoming items by maintainer" is a holding area, and closing a session is
not by itself a request to empty it (`workflow.md`). Everything else in that
skill runs either way: close what this session finished, with its evidence;
take in what is new; reorder; raise the next free item number if you minted
one.

## 4. Delete what is spent

A finished plan, a stale handover, a working file that outlived its run. A
plan whose work is done goes once what survives it has landed in step 2; git
keeps the file.

## 5. Run the gate

`<the project's full gate>`, and read its real result -- the exit code and the
test summary, not the last cheerful line. It takes about <how long>: give it a
timeout well past that, because a timeout kill reads exactly like a red gate.

`<the project's fast gate>` is enough only when nothing outside documentation
changed.

## 6. Commit your own paths

`git commit -- <your paths>`, never `git add -A`. Another agent's uncommitted
or staged files stay standing and stay out of your commit. **Ask before
pushing, every time** (`AGENTS.md`).

## 7. Report

Open with the current time <in the maintainer's timezone>, then: what changed,
what is uncommitted and why, whose work you left standing in the tree, what
became of the incoming items if you took them in, and the one thing you would
start next.

--- END close-session/SKILL.md ---
