# Installing the preview

This integration is a **preview**. It is labelled everywhere it is cheap to
label it: in the version number, in the integration's name in the *Add
integration* dialog, and as a notice under **Settings → Repairs** that stays
there for as long as the version is a preview.

> **You probably want [`main`](../../../tree/main) instead.** That is the YAML
> package: five years of evolution, in use by thousands of people, and the
> only part of this project that is finished. A preview is for people who
> want to help find what is broken.

**This first release sets up diagnostics only.** It connects to your inverter,
works out which model and firmware it is and which registers it answers, and
gives you a survey you can send back. It creates **no sensors for the
readings** — if you came here to see your solar production on a dashboard, the
YAML package above is what does that today.

The full setup is built and tested; it is switched off in this release on
purpose, because it contains the one decision in this integration that cannot
be undone. Choosing to take over `modbus_sungrow.yaml`'s entity IDs decides
which IDs years of recorder history and every dashboard card attach to, and
getting it wrong breaks both without saying anything. That is not a thing to
hand somebody in an alpha.

The *Add integration* dialog still offers it, so you can tell it exists and is
coming; choosing it explains that it is not in this release and sets the entry
up for diagnostics instead. An entry you create now can be upgraded to a full
one later without being deleted and without losing the answers you gave.

It installs through **HACS**, from a second repository called the *preview
channel* — `…-preview`, not this one. Why it has to be a second repository is
[explained at the end](#why-the-preview-lives-in-a-second-repository); the
short version is that HACS reads a repository's default branch, and this
repository's default branch is the YAML package.

Four steps. The third one is the one people forget.

## 1. Add the preview channel to HACS

**HACS → ⋮ (top right) → Custom repositories**, then:

| Field | Value |
| --- | --- |
| Repository | `https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant-preview` |
| Type | **Integration** |

**HACS itself needs a GitHub account**, if you have not set it up before. Its
own configuration asks you to type a device code at
<https://github.com/login/device>, and there is no way past it — that is HACS
talking to GitHub about *its* rate limits, not this project asking you for
anything. Any account works, including one made for the purpose. Nothing
about it is tied to this integration.

## 2. Download it

Open the repository HACS now lists and press **Download**.

The version HACS shows is a **commit hash**, not `0.1.0a2`. That is correct
and it matters later: the preview channel follows this project's development
branch and publishes no releases of its own, so a hash is what identifies the
code you are running. Quote it in bug reports.

## 3. Restart, and let Home Assistant fetch the library

**This step needs working internet access**, and it is the one that surprises
people. The register knowledge lives in a separate Python package,
[`sungrow-modbus`](https://pypi.org/project/sungrow-modbus/), pinned exactly
in the integration's `manifest.json` — so on the first start after
downloading, Home Assistant pip-installs it, exactly as it does for a
built-in integration.

Consequences worth knowing:

- The first start is **slower**, and the log will mention installing
  requirements. That is normal.
- If it cannot reach PyPI, setup fails with `RequirementsNotFound` and the
  integration will not appear. That is a network problem, not a bug in the
  integration.
- The pin names the pre-release exactly, so `pip` installs it without needing
  `--pre`. You do not have to do anything about this; it is stated because a
  pre-release usually *does* need that flag.

## 4. Add the integration

**Settings → Devices & services → Add integration →** search for
**Sungrow Modbus (preview)**.

From there the integration finds the inverter itself: it sweeps the network
you confirm, identifies what answers by asking it rather than by assuming a
unit id, and offers each way it can reach the machine — a direct cable in
preference to a WiNet-S dongle, because a cable forwards more registers.

You will be asked one question that matters and cannot be undone casually:
**whether to keep the YAML package's entity ids**. Read
[integration_migration.md](integration_migration.md) before answering it.
Keeping them means years of recorder history and every dashboard card carry
on working; taking modern ids means the integration migrates the history
across. Either answer works, but they are not the same answer.

If you would rather not add any devices yet, the first screen also offers
**diagnostics only**: no entities, nothing polled on a schedule, just the
tools for producing a reading of your installation.

## Updating

HACS offers an update whenever the channel moves, and that is **as the code
is written** rather than on a release schedule. A commit that touches only
the library source, the scanner or the documentation changes nothing you
would install, so it does not notify you.

Press **Update**, then restart. Home Assistant notices a changed pin in
`manifest.json` and installs the matching library version on the way up. The
config entry survives, and so do your entities and their history.

## Going back

1. **Settings → Devices & services → Sungrow Modbus →** delete the entry.
2. **HACS →** the integration **→ ⋮ → Remove**.
3. Restart.

If you chose to keep the YAML package's entity ids, the history is now
attached to the integration's entities, and returning to the YAML package
needs the reverse migration — [integration_migration.md](integration_migration.md)
covers it, and it is reversible: a rename moves the recorder rows rather than
copying them, so nothing is duplicated and nothing is lost.

## Why the preview lives in a second repository

Worth stating precisely, because "there is a release now" sounds like it
should be enough and is not.

HACS decides which version of a repository to read in this order: the latest
**stable** release, then a tag you explicitly selected, then the repository's
**default branch**. A pre-release does not count as a stable release — HACS
records it separately and never uses it to make that decision. Turning on
*Show beta versions* changes which versions HACS offers you **after** it has
accepted a repository; it does not change which version HACS reads in order
to accept it.

This repository's default branch is `main`, which holds the YAML package and
has no `custom_components/` directory at all. So HACS reads `main`, finds no
integration, and rejects it with *"Repository structure for main is not
compliant"*. The preview channel exists to be a repository whose default
branch **is** the integration.

[doc/preview-mirror/sync.yml](preview-mirror/sync.yml) is the whole
mechanism: one workflow, living in that repository, which polls a few times
an hour and copies the development branch from here — `custom_components/`,
`hacs.json` and a README of its own, and nothing else. It **pulls rather than
being pushed to**, which is why it needs no credential in either repository:
reading this one takes no token because it is public, and writing to itself
uses its own.

Two refusals keep it usable:

- It publishes the newest commit whose **CI passed**, walking back from the
  branch head rather than insisting on it — a documentation-only commit has
  no checks at all, and stalling behind one would hold back the good commit
  underneath.
- It will not publish a commit whose **pinned library cannot serve it**. Home
  Assistant installs that library from PyPI, so a commit importing something
  the pinned wheel does not contain could not start; the channel stays on the
  last good commit until the library is released. Not hypothetical — see
  `scripts/check_pinned_library.py`, which is the check it runs.

It is temporary, and it has one rule: **remove it from HACS before installing
from this repository**, once the integration reaches `main`. Both provide the
same integration at the same path, so keeping both is a conflict rather than
an upgrade.

## What to do when something is wrong

Two things make a report actionable, and both are read-only.

**Diagnostics.** Settings → Devices & services → Sungrow Modbus → ⋮ →
**Download diagnostics**. It carries what the integration read, what it
decided about your hardware, and what failed, with the serial and address
removed.

**A capability survey**, which is now a button rather than a command.
Settings → Devices & services → Sungrow Modbus → the device → **Run
capability survey**. It reads and never writes, and on a cable it is over in
a second; over a VPN it can take minutes, which is why the three sensors
beside the button say how far along it is and what it is reading.

When it finishes, a notification carries a summary and a download link. That
link is signed and stops working after an hour — press the button again for
a fresh one, or use **Download diagnostics** on the same page, which carries
the same document and never expires.

The document names your inverter by a **stand-in** rather than its serial
number, and carries your address only if you said it may. Send it to the
issue tracker or Discord; it is how this project learns what varies between
installations, which is the thing no specification has told it reliably.

If you set the integration up as *Diagnostics only*, it asked you a few
questions on the way in — which cable, whether a Modbus proxy is in the path,
whether anything else was polling. Those answers go into the document and no
register can answer them. They are editable afterwards under the
integration's **Configure** → *Help this project*.

Two things in that section change what the survey *reads* rather than what it
says. **Also sweep the raw register bands** is off, and is the expensive one:
an ordinary survey reads the registers this integration already knows about,
while the sweep reads 1510 addresses across twelve bands including the ones no
specification documents. That is how every undocumented register this project
knows was found — and it takes about five minutes on a cable, longer through a
WiNet-S, because an address with nothing behind it goes quiet rather than
refusing and each one costs a full timeout. Turn it on if you were asked for a
dump or you are curious what your model answers; the progress sensors name the
band being swept while it runs.

(The **Advanced** section has a switch with a similar name, *Include a raw
register dump in diagnostics*. That one is a different, much cheaper thing: it
re-reads only the addresses already mapped, into the diagnostics file. It
cannot find a register nobody knows about.)

There is still a standalone scanner for anyone who would rather not install
anything, and it does more: it runs the block read test, which the button
does not. See
[contributing a fingerprint](device-fingerprints/README.md#contributing-one).

Then open an issue quoting **the commit hash HACS shows you**. The channel
publishes no releases of its own, so a hash rather than a version is what
says which code you ran — and between releases many hashes share one version
number, so the version alone does not. That hash belongs to the preview
repository; its commit message names the commit here that it came from.

It is worth more than a report that says "the new integration".
