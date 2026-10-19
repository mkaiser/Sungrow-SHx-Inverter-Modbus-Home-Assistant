# Maintainer setup

Things only the maintainer can do, because they need an account, a credential,
or physical access to hardware. Everything else in
[the plan](integration_plan.md) can proceed without them.

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
- Run hassfest locally (AGENTS.md has the command; `make refs` fetches what
  it needs).
- After the upload, `make pin-check` asks PyPI the same question of the
  published wheel. It is legitimately red between releases, and it must be
  green before anyone is told to install something.

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

[device-fingerprints/scripts/survey.sh](../device-fingerprints/scripts/survey.sh)
(`survey.cmd` on Windows) is built for this: it runs the survey through `uv`,
which fetches Python and the pinned library itself, so it runs on the host
with nothing set up. It writes its document and transcript beside itself, in
`device-fingerprints/`; when the workspace is a bind mount from the host
folder, that is visible on both sides.

### The mDNS question

Does a WiNet-S advertise itself over mDNS? It needs a house with a dongle,
and a run **on the host**, not in the container:

```bash
pip install "sungrow-modbus[discovery]"     # zeroconf, for this check only
python device-fingerprints/scripts/python/probe.py mdns
```

If the dongle advertises its serial and model, host discovery becomes free and
exact. A negative answer is just as useful — it settles the question. An
inverter's own LAN port announces nothing, so a house without a dongle cannot
answer it.

### Which command runs where

| Command | Runs | Because |
| --- | --- | --- |
| `python device-fingerprints/scripts/python/probe.py mdns` | **host only** | Multicast does not cross the Docker bridge; needs the `discovery` extra |
| `make scan HOST=…`, `probe.py sweep/units/capabilities/dump`, `blocks.py` | either | They run on the device library: the editable install in the container, or the version `survey.sh` fetches through uv on the host |

## 3. Capturing a system

The published documents are in
[device-fingerprints/inverter/](../device-fingerprints/inverter/) and
[device-fingerprints/wallbox/](../device-fingerprints/wallbox/), and
[devices-wanted.md](../device-fingerprints/devices-wanted.md) says what is
missing, in the order it would help.

Run the one entry point:

```bash
make scan HOST=<host>          # or device-fingerprints/scripts/survey.sh <host>
```

It identifies every device on the endpoint before asking anything — which is
what tells one inverter reached two ways from two inverters — then asks what
no register can answer, checks the transport against the answer, runs the
block read test on the still-idle link, reads every register, finds a wallbox
on its own address (TLS on 516) and surveys it into a document of its own,
and prints what it found. Its last question offers the control test, and
defaults to no.

`make scan-local HOST=<host>` runs the same through the launcher on this
tree's library, which is what to use when the survey needs something the
published wheel does not have yet.

Everything is **read-only** unless that last question is answered yes. The
one file in `device-fingerprints/` that writes a register is
`sungrow_control_test.py`, which the survey runs only then.

The document and its transcript land in `device-fingerprints/`, where both
are gitignored. Publish a document by moving it into `inverter/` (or
`wallbox/`) and committing it with `doc/compatibility.md`, which
`scripts/generate/generate_compatibility.py` rebuilds from them. Leave the `sungrow-scan-*.log` transcript alone — it
carries the real serial and the addresses. And if a system belongs to
somebody else, **ask them before publishing its readings**; a stand-in
serial is not consent.

For anyone outside this repo — the users whose models nobody here owns —
[device-fingerprints/](../device-fingerprints/) is a folder they can download
and run with `./survey.sh` or `survey.cmd`; its README is written for them.

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

To do: submit `sungrow_modbus` to the brands repository before applying to
the HACS default store — it is what puts a real icon on the integration in
Home Assistant's own UI rather than only in HACS.

HACS reads this repository's default branch, which is the YAML package, so
while the integration is pre-release it reaches HACS users through the
preview channel; see `doc/preview-mirror/` and
[installing_a_preview.md](installing_a_preview.md).

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
  the repo; they live in his `secrets.yaml`.

**The shortest version:** keep credentials out of the container where you can.
Where one must be inside, keep it outside the repo, `chmod 600`, and never
print it.

## 7. Repository settings, for the HACS default store later

Needed before submitting to `hacs/default`, and free to do now: a repository
**description**, **topics**, and **issues enabled**. The brand icon exists.
Submission also needs at least one full, non-pre-release GitHub release.
Expect the review to take months.

## 8. Still open, and yours to decide

- **Generate a Lovelace dashboard, or rely on entity metadata** and document
  the auto-generated view? This decides how much dashboard code the
  integration carries.
- Credit for the wallbox project author in the docs — permission is already
  granted, so this is courtesy.
- Obtain Sungrow's *Logger Communication Protocol AW0 1.0.2.9* if the Logger
  milestone is pursued; the copy found online 404s.

## 9. The production database, when there is time

The migration cannot be verified at real scale without it. See
[the plan](integration_plan.md#the-production-testbed) for what to collect and
how to take it safely. A long-lived token as in item 6 answers a useful part of
it read-only in the meantime, but only a copy lets a migration actually be run
and rolled back.
