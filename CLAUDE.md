@AGENTS.md

## Todo.md has more than one writer

Other agents work in this repository at the same time and write `Todo.md`
too, often without committing straight away. Before **every** write to it:

1. `git status --short Todo.md` and `git diff Todo.md`: is there a change you
   did not make?
2. Re-read the file, or the part you are changing, from disk; never write it
   back from a copy read earlier.
3. Edit only your own part, as a targeted replacement, never a rewrite of the
   whole file.
4. Commit only your own change. If another agent's edits are uncommitted in
   it, leave them unstaged (stage your hunk alone, or wait until they have
   committed) and say so.
