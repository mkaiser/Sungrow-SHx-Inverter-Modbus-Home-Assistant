# The first stable release

What the first stable release needs, and what follows it: `main`, the
catalog, the preview channel, the production database and the YAML track.
Todo items T047-T053 and T068.

## T047 - When to merge into `main`.** The merge retires the preview channel
and opens the HACS default store, which also needs the brand in
`home-assistant/brands` (`scripts/helpers/make_brand_icon.py` draws it).
At the merge, the links that name the `proper-ha-integration` branch move
to `main` (`grep -rn proper-ha-integration custom_components`: the Energy
dashboard guide and the preview repair's entity names).

## T068 - What a `main` link finds after the merge.** `main` changes
meaning at the merge: today the YAML package's root, afterwards the
integration. Of the 38 files on today's `main` (`doc/images/` and
`.github/` aside), **four** paths exist on this branch -- `.gitignore`,
`LICENSE`, `README.md`, `doc/attribution.md`. The rest 404 from every
link ever written, `modbus_sungrow.yaml` included, and so do the two
links printed in the header of every installed copy of the package:
`doc/installation.md` and `doc/migration_guide.md`. Those two 404s are
accepted (the maintainer, 2026-11-20), because the line above them in the
same header -- `From github.com/mkaiser/...`, added with T066 -- lands a
reader at the repository, whose README carries the move.

GitHub's branch-rename redirect does not help. It applies to links naming
the *old* name, only while no branch of that name exists, and a real
`main` shadows it at once; raw links never follow it. The only way to
control what a `main` link finds is a file at that path.

Decided (the maintainer, 2026-11-20): today's `main` becomes
`2026-legacy`, pairing with `2025-legacy`, which keeps its name and holds
the pre-2026 line; **one** path gets a file on the new `main`,
`modbus_sungrow.yaml`, and everything else 404s. A re-download then stops
a working install until its owner reads the file -- accepted, as the
price of retiring the package. Tag the final state
`yaml-package-2026-06-19` (its release date) at the same time, so the
bytes stay addressable if the branch is ever deleted.

Three steps, all at the merge and none before it. The rename is safe to
do early -- no workflow on `main` names a branch, and until the new `main`
exists GitHub's redirect sends every `main` link to `2026-legacy` -- but
early costs the default branch of the repository thousands of people
install from changing weeks before anything arrives there, so it waits.

1. Rename `main` to `2026-legacy`. **Left to do.**
2. The file below, at `modbus_sungrow.yaml`. **Done early**, on
   `proper-ha-integration`, which is what becomes the new `main` -- so the
   merge needs no file work. With it went the three generated
   multi-inverter files and the two workflows that committed into
   `legacy/` (`auto-generate-multiple-inverter_configs.yml`,
   `generate-sensor-list.yml`). `scripts/generate/generate_second_inverter_config.py`
   stays: `tests/test_legacy_slot.py` now runs its transforms in memory to
   prove the `_inv_<n>` slot, where it used to read the committed output.
3. The two deep links in the YAML's own header --
   `blob/main/doc/installation.md` and `blob/main/doc/migration_guide.md`
   -- to `blob/2026-legacy/...`. **Done early** in
   `legacy/modbus_sungrow.yaml`; **left to do** is the same edit in
   `2026-legacy`'s own copy at the rename, which makes the two identical
   again. Everyone who downloads after that has live links, and only copies
   already installed carry the dead ones.

Until the rename, every `2026-legacy` link written for steps 2 and 3 is
dead. That is the accepted cost of doing them early, and it costs nothing
today: nobody installs the YAML package from this branch.

The tag waits with them, or for T053: the header says *Release date
2026-06-19* but `main` has moved since, so there is no final state to
tag yet.

The file is comments only, which is why it stops the install: Home
Assistant has no package to load, setup fails, and the owner opens the
file. It carries the links its own header used to carry, because it is
the only path still answering:

```yaml
# modbus_sungrow.yaml has moved, and is superseded.
#
# The YAML package is on the 2026-legacy branch:
#   https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/blob/2026-legacy/modbus_sungrow.yaml
# Its installation and migration guides moved with it, under doc/ there.
#
# What replaces it is the Sungrow Modbus integration, on this branch:
# Settings -> Devices & services -> Add integration. Your recorder
# history, statistics and dashboards survive the switch --
# doc/integration_migration.md says how, and how to go back.
#
# This file is this notice and nothing else, so Home Assistant has
# nothing to load here and the package fails to set up. Your inverter is
# fine; the file you meant to download is the link above.
```

## T048 - Submitting to the catalog, when the merge is decided.** The catalog
is `hacs/default`, run by the HACS team and read by the Marketplace; a PR
from a personal account adds `owner/repository` to its `integration`
file, alphabetically, with the template filled in. Review is automated
checks and then "months" in the queue (read on hacs.xyz and
contributors.home-assistant.io/marketplace, 2026-11-06; not checked
against `hacs/default` itself). Where this repository stands:

| Requirement | Here |
| --- | --- |
| Public repository, owner submits, OSI licence | yes, MIT |
| Description, topics, issues enabled | yes |
| `hacs.json` with `name` | yes |
| `manifest.json`: domain, documentation, issue_tracker, codeowners, name, version | yes; the name still ends "(preview)" |
| Brand: `brand/icon.png` in the integration, or the domain in `home-assistant/brands` | `brand/` exists |
| HACS action and hassfest pass with no ignores | yes: CI runs both and ignores no check |
| **At least one full GitHub release** (a tag is not enough) | **no: every release is a pre-release** |
| `categories` in `manifest.json` | yes, three, and `connectivity: ["modbus"]` |

Open: whether a repository whose only releases are pre-releases passes
(not stated); so the first stable release (0.1.0, not an alpha) is the
real gate. Drop "(preview)" from the name on `main` only. The
Marketplace refreshes the catalog every 6 hours and a repository added from
a link every 48 hours.

## T049 - The preview channel under the Marketplace.** Home Assistant 2026.11
is the minimum (`hacs.json`), where HACS is built in as Settings →
Marketplace, and the docs describe the Marketplace alone: a preview
installed through HACS on 2026.9 or 2026.10 is adopted when its Home
Assistant is upgraded, so nobody needs a HACS step (decided 2026-11-12;
what the testbed checked is in `doc/maintainer_setup.md` §5). The testbed
is `make marketplace` (`hacs_testbed.sh --marketplace`: 2026.11.0 from
`.venv-marketplace/`, `config-marketplace/`, :8126, login dev/dev;
`ARGS=--adopt-hacs` starts from a copy of `config-hacs/`).

Left: a screenshot of *Add from link* for
`doc/installing_a_preview.md`, in place of HACS's custom-repository
dialog, taken on `make marketplace`.

## T050 - The production database.** The migration is verified at real scale
only against the maintainer's years-old YAML install; what to collect and
how is in `doc/maintainer_setup.md`, section 8. Two routes: a copy of the
instance's files (preferred: the migration can be run and rolled back, in
the gitignored `.testdata/`, pointed at the simulator, never at the real
inverter) or read-only API access (the entity map and statistics only).
For the API: a non-admin user's token and the instance's address are in
`~/.claude/secrets/` (never in this repository), but the hostname resolves
to IPv6 only and the devcontainer has no IPv6 route, so it is unreachable
from here until Docker gets IPv6 or an IPv4 address is given. Counts and
mismatches are reported, no serial or address.

## T051 - The YAML track's documentation, for the integration.** The pages
below open with a note that they are for the YAML package, pointing at
`doc/installing_a_preview.md` and `doc/integration_migration.md`; the
first-line documentation of the integration is `strings.json`. At the
release, the note points at the ordinary install instead of the preview.

| Page | To do |
| --- | --- |
| `legacy/doc/cleanup_entities.md` | Link it from a repair as the manual fallback, if one is built |
| `legacy/doc/dashboard.md` | A generated dashboard (Future work) |

## T052 - Handing the preview channel's users over to the release.** There is
no one-click switch: the Marketplace refuses to install an integration
whose domain another installed repository owns, and refuses to remove one
while a config entry of its domain exists, so the switch is five steps --
delete the entry, remove the preview, download this repository, restart,
set the integration up again. Home Assistant restores a deleted entity's
id when the same platform and unique id come back within 30 days, so the
ids, and with them the history, should come back; the options are asked
again. How that was read out of core 2026.11.0, and the two routes that
do not help, are in `doc/maintainer_setup.md` §5.

**For the maintainer to decide**: keep the mirror running after the
release, publishing `main`'s release tags under a name without
"(preview)", so mirror users get an ordinary *Update* and never switch
(proposed, since the switch costs a new setup), with a repair of our own
naming the five steps for whoever wants the main repository; archive the
mirror once few installs use it. To check on `make marketplace` once
`main` carries the integration: that the five steps keep the ids and the
history on a migrated install, and that a commit-tracked install switches
to versions once the mirror publishes a release.

## T053 - Deprecating and retiring the YAML package, after the release.** Once
the integration has parity, is merged into `main` and is in the HACS
default store: deprecate `legacy/modbus_sungrow.yaml` and the generated
multi-inverter files, announce it, point every `legacy/doc/` page at the
integration and `doc/integration_migration.md`, and set a date after
which the YAML package gets no further changes.

Retiring does not end migration, so the legacy-id adoption, its guards
and `tests/test_sensor_descriptions.py` stay as long as migration is
offered. `tests/test_registers.py`'s comparison with the YAML can then be
anchored to the specification instead; its scan-interval check goes first.
