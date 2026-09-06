# Maintainer setup

Things only the maintainer can do, because they need an account, a credential,
or physical access to hardware. Everything else in
[the plan](integration_plan.md) can proceed without them — but the first item
blocks anyone from installing the integration at all.

Applies to the **integration** track only. The YAML package needs none of it.

## 1. Claim the PyPI name — blocking

`custom_components/sungrow_modbus/manifest.json` pins
`sungrow-modbus==<version>`, and Home Assistant pip-installs a custom
integration's requirements exactly as it does a built-in one. That package does
not exist yet, so **a HACS install fails at start-up**. It works in the
devcontainer only because `scripts/setup` installs the library editable, which
no user has.

There is no way to reserve a name on PyPI. A name is claimed by uploading, and
a Trusted Publishing "pending publisher" explicitly does not hold it.
**`0.0.1` is the version that claims it**, deliberately: uploads are immutable,
so whatever goes first is permanent, and `0.1.0` is worth keeping for the first
release that deserves the number. So:

1. Create a PyPI account and enable 2FA (mandatory).
2. On PyPI → *Your projects* → *Publishing*, add a **pending publisher**:
   - Owner `mkaiser`
   - Repository `Sungrow-SHx-Inverter-Modbus-Home-Assistant`
   - Workflow `release.yml`
   - Environment `pypi`
   - Project name `sungrow-modbus`
3. Rehearse against TestPyPI first — worth the ten minutes, because an upload
   is immutable and OIDC misconfiguration only shows at upload time. It needs
   its own account and its own pending publisher on **test.pypi.org**, with
   workflow `testpypi.yml` and environment `testpypi`; create a GitHub
   environment of that name too, then run *Rehearse the PyPI publish* from the
   Actions tab. Every run picks a fresh `.devN` version, so it can be repeated
   until it works. The run prints the exact `pip install` line to verify with.
4. Tag a release. The first publish creates the project and claims the name:

   ```bash
   python scripts/sync_version.py --set 0.0.1   # already true
   git commit -am "Release 0.0.1"
   git tag v0.0.1
   git push --follow-tags
   ```

Before any of that, `python -m build && twine check dist/*` in the container
catches metadata problems with no account involved — the package builds clean
and passes as of 2026-09-06.

`.github/workflows/release.yml` already carries the `pypi` job, using OIDC, so
**no API token is stored in secrets**. Note that uploads are immutable — a
version number can never be reused — and that PyPI treats `sungrow-modbus` and
`sungrow_modbus` as the same project.

## 2. Running things from the host instead of the container

Most work belongs in the devcontainer, because that is where Home Assistant,
the device library and the test suite are — Home Assistant needs Python 3.14.2
or newer and a specific set of pinned dependencies, none of which exist on the
host. Reopening the folder natively would mean rebuilding all of that, which is
what the container exists to avoid.

But **the workspace is a bind mount from the Windows filesystem**, so anything
run on the host that writes into the repository folder is visible from inside
the container immediately, and the other way round. That covers the cases where
the host is genuinely better:

- **Multicast**, which a Docker bridge does not carry — so mDNS discovery can
  only be answered from the host.
- **Any site the container cannot route to**, though in practice it follows the
  host's routing already.

[scripts/collect_fingerprint.py](../scripts/collect_fingerprint.py) is built
for exactly this: no dependencies, plain Python 3.9 or newer, so it runs on the
host with nothing installed. Write its output into the repository folder and it
appears on both sides.

### The mDNS question — five minutes, high value

Run this **on the host**, not in the container:

```bash
pip install zeroconf          # the only dependency, and only for this check
python scripts/discover_probe.py mdns
```

If the dongle advertises its serial and model, host discovery becomes free and
exact, and the address-sweep subsystem stops being needed at all. A negative
answer is just as useful — it settles the question. If you would rather not
install anything, say so and a standard-library-only version can be written.

### Which command runs where

Three tools, three homes, and mixing them up produces confusing errors:

| Command | Runs | Because |
| --- | --- | --- |
| `python scripts/collect_fingerprint.py <ip>` | **host or container** | No dependencies at all |
| `python scripts/discover_probe.py mdns` | **host only** | Multicast does not cross the Docker bridge; needs `zeroconf` |
| `python scripts/discover_probe.py capabilities/units/dump` | **container only** | Uses the device library, which is installed there |

## 3. Capture the test systems

Four are available. One read-only session over all four is worth more than
visiting each at its own milestone, because three decisions have been made on
paper and can be checked cheaply now — above all the naming ladder, designed
without ever having seen two inverters of the same model.

Run this **in the devcontainer** — it uses the device library:

```bash
python scripts/discover_probe.py capabilities <host> \
    --save doc/fingerprints --label sh10rt-v112
```

| Setup | Label to use | Why it matters |
| --- | --- | --- |
| LAN: SH10RT + Pylontech | `sh10rt-pylontech` | Done — a third-party battery |
| Remote: SH10RT-V112 + Sungrow battery | `sh10rt-v112` | A variant device code, a real Sungrow battery |
| Remote: SH10RT-V122 + battery + wallbox | `sh10rt-v122-wallbox` | The only wallbox |
| Remote: two SH10RT | `sh10rt-pair-a`, `-b` | The only multi-inverter site |

On the wallbox system, also dump the undocumented gaps:

```bash
python scripts/discover_probe.py dump <host> --unit 3 --start 21230 --count 40 --save
python scripts/discover_probe.py dump <host> --unit 3 --start 21266 --count 40 --save
```

Everything above is **read-only**. No command in `discover_probe.py` writes a
register.

For anyone outside this repo — the users whose models nobody here owns —
[scripts/collect_fingerprint.py](../scripts/collect_fingerprint.py) does the
same job with no dependencies and no checkout: a single file they can download
and run on plain Python. See [doc/fingerprints/](fingerprints/).

Then commit the `.capabilities.json` and `.readings.json` files. Leave the
`.raw.json` alone — it is gitignored, and it carries the real serial and the
exact time. And if a system belongs to somebody else, **ask them before
publishing its readings**; a stand-in serial is not consent.

## 4. Reaching the remote systems

The devcontainer reaches the LAN through the Docker bridge, which is how the
reference inverter was read. Remote sites work the same way once they are
routable from the host — the container follows the host's routing without
needing to know anything about it, so the only thing it needs is an address.

Two things to check:

- **Overlapping subnets.** If two sites are both on `192.168.178.0/24` — the
  FRITZ!Box default — they cannot both be reachable at once, and worse, a
  probe would silently reach the wrong inverter. Give each site a distinct
  subnet, or make one reachable at a time and say which is live.
- **The Docker bridge is `172.17.0.0/16`**, so a site on that range would
  collide with the container itself.

### The HACS brands check

HACS validates nine things about a repository, and the one that fails for a
new integration is **brands**: it wants the domain listed in the Home Assistant
[brands repository](https://github.com/home-assistant/brands), and falls back
to looking for assets at `custom_components/<domain>/brand/icon.png` inside
the repository itself. The icons were at the repository root, which is neither
place, so the check failed with "does not provide brand assets and is not
listed in the Home Assistant brands repository".

They now live at `custom_components/sungrow_modbus/brand/`, which satisfies
the fallback. Submitting `sungrow_modbus` to the brands repository is still
worth doing before applying to the HACS default store — it is what puts a real
icon on the integration in Home Assistant's own UI rather than only in HACS.

## 5. Keeping data out of the cloud

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

- `.testdata/` is gitignored and holds raw dumps, the production database copy,
  and anything else from a real installation.
- `scripts/discover_probe.py` splits every capture into a publishable part and
  a private part rather than leaving the judgement to whoever runs it.
- Connection details for the maintainer's own inverter are deliberately not in
  the repo; they live in his `secrets.yaml`.

**The shortest version:** keep credentials out of the container where you can.
Where one must be inside, keep it outside the repo, `chmod 600`, and never
print it.

## 6. Repository settings, for the HACS default store later

Needed before submitting to `hacs/default`, and free to do now: a repository
**description**, **topics**, and **issues enabled**. A `custom_components/sungrow_modbus/brand/icon.png` already
exists. Submission also needs at least one full GitHub release, which item 1
produces. Expect the review to take months.

## 7. Still open, and yours to decide

- **Generate a Lovelace dashboard, or rely on entity metadata** and document
  the auto-generated view? This decides how much dashboard code the
  integration carries.
- Credit for the wallbox project author in the docs — permission is already
  granted, so this is courtesy.
- Obtain Sungrow's *Logger Communication Protocol AW0 1.0.2.9* if milestone 8
  is pursued; the copy found online 404s.

## 8. The production database, when there is time

The migration cannot be verified at real scale without it. See
[the plan](integration_plan.md#the-production-testbed) for what to collect and
how to take it safely. A long-lived token as in item 5 answers a useful part of
it read-only in the meantime, but only a copy lets a migration actually be run
and rolled back.
