# Maintainer setup

Things only the maintainer can do, because they need an account, a credential,
or physical access to hardware. Everything else in `Todo.md` can proceed
without them.

Applies to the **integration** track only. The YAML package needs none of it.

## 1. Releasing

`custom_components/sungrow_modbus/manifest.json` pins
`sungrow-modbus==<version>`, and Home Assistant pip-installs a custom
integration's requirements exactly as it does a built-in one. So every
release of the integration is also a release of the library to PyPI, and an
install works only once that upload exists. In the devcontainer the library
is installed editable from `src/`, which no user has.

A release is a tag:

```bash
make version VERSION=0.1.0a18      # pyproject, manifest, the scripts' PEP 723 pins
git commit -am "Release 0.1.0a18"
git tag -a v0.1.0a18               # the tag message is the published release note
git push --follow-tags
```

`.github/workflows/release.yml` then checks the tag against the files, runs
ruff, pytest, hassfest and the HACS check, publishes the GitHub release
(marked pre-release by PEP 440's rule) and uploads the library to PyPI through
Trusted Publishing -- the `pypi` environment and a publisher configured on
PyPI for this repository and workflow, so **no API token is stored in
secrets**. Write the tag message for users: it is the release note, and
GitHub's own generator would list every commit since 2022.

Before tagging:

- `make ci` runs what CI runs, including the build and the gate that the
  built wheel provides every import the integration and the survey make.
- Run hassfest locally (`make refs` fetches what it needs):

      python -c "import sys; sys.path.append('.reference/core'); \
        sys.argv=['hassfest','--integration-path','custom_components/sungrow_modbus',\
        '--action','validate']; \
        from script.hassfest.__main__ import main; raise SystemExit(main())"

  Appended to `sys.path`, not prepended, so the **installed** Home Assistant
  wins: `.reference/core` is a partial clone with no `homeassistant.generated`.
  The finding it most often makes: a repair issue is `title` + `description`
  *or* `title` + `fix_flow`, never both (*"two or more values in the same
  group of exclusion 'fixable'"*). For a fixable issue the text belongs in
  the fix flow's step.
- After the upload, `make pin-check` asks PyPI the same question of the
  published wheel. It is legitimately red between releases, and it must be
  green before anyone is told to install something.

**Versioning.** One version, in `pyproject.toml`, mirrored into the
manifest and the survey scripts by `scripts/release/sync_version.py` and
checked in CI, pytest and at release. It accepts only the normalised PEP 440
spellings (`0.1.0a1`, `b1`, `rc1`), which `release.yml` marks pre-release.
`v*` tags are the integration; the YAML package keeps its dated scheme.
Testers are told it is a preview in three places: the version (`pip` needs
`--pre`), the "(preview)" name in `manifest.json` and `hacs.json`, and a
`preview_release` repair. A rename during the preview is a registry
migration away, not a broken install.

Uploads are immutable -- a version number can never be reused -- and PyPI
treats `sungrow-modbus` and `sungrow_modbus` as the same project. The manual
*Rehearse the PyPI publish* workflow (`testpypi.yml`) uploads a `.devN`
version to TestPyPI over its own publisher and `testpypi` environment, for
when the publishing setup changes.

## 2. Running things from the host instead of the container

Most work belongs in the devcontainer, because that is where Home Assistant,
the device library and the test suite are — Home Assistant needs Python 3.14.2
or newer and a specific set of pinned dependencies, none of which exist on the
host. Reopening the folder natively would mean rebuilding all of that, which is
what the container exists to avoid.

The host is genuinely better for two things:

- **Multicast**, which a Docker bridge does not carry — so mDNS discovery can
  only be answered from the host.
- **Any site the container cannot route to**, though in practice it follows the
  host's routing already.

[device-survey/scripts/survey.sh](../device-survey/scripts/survey.sh)
(`survey.cmd` on Windows) is built for this: it runs the survey through `uv`,
which fetches Python and the pinned library itself, so it runs on the host
with nothing set up. It writes its document and transcript beside itself, in
`device-survey/`; when the workspace is a bind mount from the host
folder, that is visible on both sides.

### The mDNS question

Does a WiNet-S advertise itself over mDNS? It needs a house with a dongle,
and a run **on the host**, not in the container:

```bash
pip install "sungrow-modbus[discovery]"     # zeroconf, for this check only
python device-survey/scripts/python/probe.py mdns
```

If the dongle advertises its serial and model, host discovery becomes free and
exact. A negative answer is just as useful — it settles the question. An
inverter's own LAN port announces nothing, so a house without a dongle cannot
answer it.

### Which command runs where

| Command | Runs | Because |
| --- | --- | --- |
| `python device-survey/scripts/python/probe.py mdns` | **host only** | Multicast does not cross the Docker bridge; needs the `discovery` extra |
| `make scan HOST=…`, `probe.py sweep/units/capabilities/dump`, `blocks.py` | either | They run on the device library: the editable install in the container, or the version `survey.sh` fetches through uv on the host |

## 3. Capturing a system

```bash
make scan HOST=<host>          # or device-survey/scripts/survey.sh <host>
make scan-local HOST=<host>    # the same on this tree's library
```

What the survey does and writes is in
[device-survey/README.md](../device-survey/README.md). To publish a
document, move it into `device-survey/results/inverter/` (or `wallbox/`),
run `make gen` for `doc/compatibility.md`, and ingest it into the wiki
(`.wiki/AGENTS.md`). Never the `sungrow-scan-*.log` transcript: it carries
the real serial and addresses. **Ask an owner before publishing their
readings**; a stand-in serial is not consent.

## 4. Reaching the remote systems

The devcontainer reaches the LAN through the Docker bridge. Remote sites work
the same way once they are routable from the host — the container follows the
host's routing without needing to know anything about it, so the only thing it
needs is an address.

Two things to check:

- **Overlapping subnets.** If two sites are both on `192.168.178.0/24` — the
  FRITZ!Box default — they cannot both be reachable at once, and worse, a
  probe would silently reach the wrong inverter. Give each site a distinct
  subnet, or make one reachable at a time and say which is live.
- **The Docker bridge is `172.17.0.0/16`**, so a site on that range would
  collide with the container itself.

Over a VPN, slow a sweep down (`probe.py sweep` with a longer `--timeout` and
a lower `--concurrency`): its defaults are tuned for a LAN and rule live hosts
out before a tunnel answers.

## 5. HACS and brands

HACS validates a repository's brand: it wants the domain listed in the Home
Assistant [brands repository](https://github.com/home-assistant/brands), and
falls back to `custom_components/<domain>/brand/icon.png` inside the
repository. The icons are at `custom_components/sungrow_modbus/brand/`
(`scripts/helpers/make_brand_icon.py` draws them), which satisfies the
fallback.

Submitting `sungrow_modbus` to the brands repository puts a real icon in
Home Assistant's own UI, not only in HACS; it is part of the merge decision
in `Todo.md`.

HACS reads a repository's *default branch* unless there is a stable release
(`version_to_download()` in HACS's `repositories/base.py`), and this
repository's default branch is the YAML package. So while the integration is
pre-release it reaches HACS users through the preview channel: a second
repository whose default branch *is* the integration, synced by
`doc/preview-mirror/sync.yml`, which must stay byte-identical to the copy
running there. See [installing_a_preview.md](installing_a_preview.md);
`scripts/dev/hacs_testbed.sh` installs from it the way a user does. HACS
itself requires a GitHub account.

## 6. Keeping data out of the cloud

Worth being precise, because "cloud" means two different things here and the
answers differ.

**Anthropic's API.** Everything in a Claude Code session — prompts, tool calls
and their output — is sent to the API to produce the next response. So the
rule is not about where a file sits, it is about whether anything **prints**
it. A key in a file that is never read never leaves the machine; the same key
`cat`ed into a terminal has been transmitted. That is why the Home Assistant
token belongs in an environment file that gets *sourced*, never displayed:

```bash
printf 'HA_URL=http://<ip>:8123\nHA_TOKEN=<paste>\n' > ~/.claude/sungrow-ha.env
chmod 600 ~/.claude/sungrow-ha.env
```

and why it should not be pasted into the chat either. Session transcripts are
themselves stored under `~/.claude/projects/`, so anything shown in a session
is also on disk in the clear.

**GitHub, and this public repository.** A different axis, and permanent:
anything committed is public and stays in the history even if deleted later.
The protections in place:

- `.testdata/` is gitignored and holds the production database copy and
  anything else from a real installation. The survey and the control test
  write beside themselves instead, and `.gitignore` names each file they
  write.
- Every published document carries a hashed stand-in for the serial, and the
  real one reaches only the transcript; `tests/test_no_real_serials.py`
  fails on anything serial-shaped in a tracked file that is not on its list
  of invented ones.
- Connection details for the maintainer's own inverter are deliberately not in
  the repo; they live in the maintainer's own `secrets.yaml`.

**The shortest version:** keep credentials out of the container where you can.
Where one must be inside, keep it outside the repo, `chmod 600`, and never
print it.

## 7. Repository settings, for the HACS default store later

Needed before submitting to `hacs/default`, and free to do now: a repository
**description**, **topics**, and **issues enabled**. The brand icon exists.
Submission also needs at least one full, non-pre-release GitHub release.
Expect the review to take months.

## 8. The production database, when there is time

The migration cannot be verified at real scale without it. The
maintainer's instance has run the YAML package for years, and is the only
way to show history and statistics survive at scale. Collect from it
`home-assistant_v2.db`, `.storage/core.entity_registry`,
`core.device_registry`, `core.restore_state`, `.storage/lovelace*` and the
`modbus_sungrow.yaml` in use, into the gitignored `.testdata/`: real
household data, never in the repo or CI. Run the migration against a copy and
assert a known sensor's history and statistics are continuous, and diff the
entity map against the real `unique_id` → `entity_id` map: any divergence is a
silent history-loss case. `scripts/dev/seed_migration_testbed.py` builds the
same situation on the dev instance for review in the GUI.

A long-lived token as in item 6 answers a useful part of it read-only in the
meantime, but only a copy lets a migration actually be run and rolled back.

## 9. Test systems

| Setup | What only this one proves |
| --- | --- |
| Reference: SH10RT, third-party battery, cable | The default development target |
| fwitten: two SH10RT-V112 (master/slave), SBR, cables and dongles | Multi-device, unit 2 slaves, a firmware upgrade read before and after |
| gerd: SH8.0RT-V112, SBR, wallbox, cable and dongle | The wallbox; cable against dongle on one inverter |
| bar12: SH10RT-20, SBR, cable and dongle | A second cable/dongle pair; writes allowed |

Two sites on the same subnet cannot both be routed; check before trusting an
address. Section 4 has the access details.
