# Erasing gerd's wallbox serial from the public history

A real device serial is in the public history of this repository, against
CLAUDE.md's hard constraint. This is the plan for removing it. Nothing here
has been done yet: every step that changes a remote is the maintainer's to
run.

## What leaked, and where

**The wallbox serial of gerd's AC22E-01**, as six 16-bit register words at
input 21200-21205. A live read on 2026-10-13 matched all six word for word.
`tests/test_no_real_serials.py` did not catch it because it matches the
*string* shape of a serial, and these are integers.

| Where | What |
| --- | --- |
| `tests/test_wallbox_readings.py` | `test_no_reading_can_come_from_a_masked_register`, the "unmasked" dict |
| `tests/test_fingerprint_label.py` | `test_a_wallbox_dump_is_masked_at_the_wallbox_serial`, labelled "the words this wallbox actually answered" |

Searched and **not** affected:

- No other file in any commit ever held the full six words (`git log --all
  -G` on the last four words), and no commit holds the serial as ASCII or
  as hex.
- **PyPI**: every `sungrow-modbus` sdist ships only `src/`,
  `tests/test_device.py` and `tests/conftest.py`; checked at all twelve
  tags, and the 0.1.0a12 sdist downloaded and grepped. No PyPI file needs
  yanking.
- **`main`**: does not contain the commit.
- **The preview mirror**: copies `custom_components/`, `hacs.json` and
  `LICENSE` only, which never held the full serial.
- The first two words (`[16690, 13633]`, "A25A", 4 of 11 characters) are
  quoted on purpose in about a dozen docstrings, as the example of what the
  mask exists for. That fragment does not identify the device and stays.

**Reach:**

- First published in **ec9eb62** (2026-09-10, "Milestones 3, 4, 6 and 7 …
  v0.1.0a1"). Every later commit on `proper-ha-integration` carries it:
  29 commits up to b3d0e70.
- **All twelve tags** `v0.1.0a1` … `v0.1.0a12` point at commits that carry
  it, and so do the GitHub releases made from them (source archives).
- **One fork has the branch**: `BuggiTheBeat/Sungrow-SHx-Inverter-Modbus-Home-Assistant`,
  `proper-ha-integration` at 68d8ca0 (Release 0.1.0a5). Checked over the
  API on 2026-10-13 for the forks pushed since 2026-09-10; the other 152
  forks predate the leak, but a fork's network shares objects, so GitHub
  Support is still needed for cached commits (step 6).
- No pull request was ever opened from the branch.

## The fix in the tree (done, uncommitted)

Both tests now use the words of the invented `A123456789` (`16689, 12851,
13365, 13879, 14393, 0`). The wallbox serial is now published as the
inverter's is: a hashed stand-in, `wallbox.serial_anonymized_hashed`, with
the words masked (schema 21). Commit this **first**, as an ordinary commit,
so the rewrite below has a clean tree to rewrite onto.

## The rewrite

`git filter-repo` replacing the six words in every commit, rather than
dropping files or commits. It keeps every commit and every message, so the
history still reads the same; only the SHAs change.

### 0. Before anything

- [ ] Tell gerd: what leaked, since when, and that it is being removed. Ask
      whether he wants anything beyond this (e.g. telling Sungrow support).
- [ ] Announce a freeze on `proper-ha-integration`: anyone with a clone must
      re-clone afterwards, and a pull from an old clone would bring the
      serial straight back.
- [ ] Pause the preview mirror's schedule (its workflow in the mirror
      repository), so it does not sync mid-rewrite.
- [ ] Make sure nothing unpushed is lost: everything committed and pushed,
      so the backup below is complete.

### 1. Work in a fresh mirror clone, never the dev checkout

    git clone --mirror https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant.git sungrow-rewrite.git
    cp -a sungrow-rewrite.git sungrow-backup.git     # kept offline, deleted once step 7 passes

`--mirror` takes every branch and tag, which is what the rewrite has to
cover. The backup **contains the serial**: keep it local, and delete it at
the end.

### 2. The replacement file

**The real words are never written into this plan or any tracked file**:
that would publish the serial a second time. `replacements.txt` is
generated at rewrite time from the old history, outside any repository,
and deleted with the backup:

    git -C sungrow-rewrite.git show b3d0e70:tests/test_fingerprint_label.py | python3 -c '
    import re, sys
    text = sys.stdin.read()
    block = text[text.index("actually answered"):]
    real = re.findall(r"\"2120([0-5])\": (\d+),", block)[:6]
    fake = [16689, 12851, 13365, 13879, 14393, 0]   # the invented A123456789
    assert [i for i, _ in real] == list("012345"), real
    for (i, word), f in zip(real, fake):
        print(f"\"2120{i}\": {word},==>\"2120{i}\": {f},")
    ' > ../replacements.txt
    wc -l ../replacements.txt     # 6

Each line is scoped to its dict entry, `"21204": <word>,`, so the numbers
cannot match anywhere else. Holding 21202/21203 elsewhere in the tests
carry other values and are not touched.

The first two lines also replace the "A25A" fragment inside these two
dicts, so the assertions next to them (`"A25A" not in …`,
`startswith("A25A")`) would fail in rewritten historical commits. That is
acceptable: old commits are not re-run. The current tree asserts `A123`.

### 3. Rewrite

    pip install git-filter-repo
    cd sungrow-rewrite.git
    git filter-repo --replace-text ../replacements.txt

It rewrites every ref, tags included, and drops the old objects.

### 4. Verify, before pushing anything

    # For each left-hand side in ../replacements.txt, nothing may remain:
    cut -d'=' -f1 ../replacements.txt | while read -r old; do
        git log --all --format=%h -S"$old"            # must print nothing
    done
    git tag | wc -l                                               # still 12
    git log --oneline proper-ha-integration | wc -l               # unchanged count
    git diff <old-head-sha> proper-ha-integration --stat          # only the two test files

Then check out the rewritten head in a scratch worktree and run `make
check`: it must be green, which it is only if the tree fix above was
committed before the rewrite.

### 5. Push

    git push --force --mirror origin

`--mirror` rewrites branches **and tags** and would delete any remote ref
missing locally; the clone was a mirror, so there are none. If that feels
too broad, push the branch and the twelve tags explicitly instead:

    git push --force origin proper-ha-integration
    git push --force origin 'refs/tags/v0.1.0a*'

**The tags' SHAs change.** The GitHub releases stay attached to the tag
names, but their source archives are rebuilt from the new commits. PyPI is
untouched: wheels and sdists are files, not commits. HACS's preview channel
installs from the mirror, which is unaffected.

### 6. What a force-push cannot reach

- **GitHub keeps the old commits reachable by SHA** (cached views,
  `/commit/<sha>` URLs) until garbage-collected. Open a request with GitHub
  Support ("remove sensitive data", see GitHub's docs page *Removing
  sensitive data from a repository*), listing the repository and the old
  SHAs from ec9eb62 to b3d0e70. They purge cached views and dangling
  commits.
- **The fork `BuggiTheBeat/…`** holds the old branch. Ask its owner to
  delete the branch or the fork; failing that, include it in the GitHub
  Support request.
- Clones elsewhere: the maintainer's other machines (the Windows checkout
  at `C:\Users\mkaiser\Documents\git\…`), and any contributor who pulled
  the branch. Re-clone; do not pull into an old clone.

### 7. Afterwards

- [ ] Re-clone the dev checkout (or `git fetch && git reset --hard
      origin/proper-ha-integration` after stashing nothing worth keeping).
- [ ] Resume the preview mirror; its next sync finds the rewritten head.
- [ ] Delete `sungrow-backup.git` and the old clone.
- [ ] Confirm on github.com that a search for one of the words in the
      repository finds nothing (code search indexes only the default
      branch, so also open the two test files on the branch).
- [ ] Close it out with gerd.

## So it does not happen again

`tests/test_no_real_serials.py` should catch the serial in word form: decode
every run of five or more integers in 0x2020-0x7E7E (printable ASCII pairs)
found in a tracked file to text, and hold the result to the same shape check
and allow-list as a string. The leaked words would have failed it on the
commit that introduced them. Not written yet.
