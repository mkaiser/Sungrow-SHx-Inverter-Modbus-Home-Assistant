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

### The maintainer's inbox

`Todo.md` opens with an **inbox**: a section the maintainer writes into in
whatever form suits them -- a line, a paragraph, a pasted link, a half-formed
idea -- without having to shape it into an item.

- **Every session reads it first**, as part of reading `Todo.md`, before
  deciding what to work on. It is not optional and not skimmed: an entry there
  outranks the priority order below it.
- **An agent that takes an entry in either does it or files it** as a numbered
  item in the right section, with a plan under `plans/` where it needs one,
  and **removes it from the inbox in the same edit**, saying what it did with
  it. Nothing is left half-taken. An entry that cannot be acted on stays, with
  one line underneath saying what it waits on -- a decision, an answer,
  hardware -- or it moves to **Open decisions** or **Blockers** as an item.
- **Only the maintainer writes new entries there.** An agent's own note to a
  later session is a numbered item or a plan's status log, never the inbox.
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

A project adds the sections its work needs and says so in `AGENTS.md`. (This
one adds **Planned tests** -- hardware runs with a date, removed once run and
ingested -- and groups next steps and blockers by device.)

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
`Todo.md` links to it.** One file per piece of work,
`plans/<kebab-case-name>.md`, named after the work and not after a session.

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
- **Check `plans/` before writing a new one**, so two files do not describe
  the same work.
- **A handover is a plan for one device or one run**, not for a session: write
  what the next session needs, not what the last one did.
- **Not every file under `plans/` is a plan.** A generated file that lives
  there is listed among the project's generated files in `AGENTS.md`, and is
  never hand-edited.

## Closing a session

Before you stop -- whether the work is finished or only paused -- in this
order. Every line is a rule from above, where its reasoning is; this is the
checklist, not a second statement of them.

1. **Write up every plan you touched**: its status log entry.
2. **Put the knowledge where it is read.** A finding that lives only in the
   conversation is lost.
3. **Update `Todo.md`**, the maintainer's inbox included, and raise the next
   free item number if you minted one.
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
