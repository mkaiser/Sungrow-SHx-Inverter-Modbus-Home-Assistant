---
name: release
description: Release a new version of the integration and library (PyPI, GitHub release, preview mirror). Use when the maintainer asks to release, or a fix must reach preview users.
---

# Release

`doc/maintainer_setup.md`, section 1, is the procedure; this is the checklist.
**Every push needs the maintainer's yes for that push**, and a release is one.

1. `make check` green, with `$?` read directly, not through a pipe.
2. `make version VERSION=X.Y.Z`, then
   `python scripts/release/check_pinned_library.py --wheel dist/*.whl` on a
   fresh `make wheel`.
3. Commit `Release X.Y.Z: ...` naming any issue it fixes; `git tag -a vX.Y.Z`
   with a release note for users (the tag message is published as is).
4. With leave: `git push --follow-tags origin proper-ha-integration`.
5. `gh run watch <release.yml run> --exit-status`, then `make pin-check`.
6. `gh workflow run sync.yml -R mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant-preview`,
   then check the mirror's `manifest.json` pins the new version.
7. `Fixes #n` closes nothing from this branch (it is not the default branch):
   answer and close the issue, with the maintainer's leave for the text.
