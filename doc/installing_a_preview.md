# Installing a preview release

This integration ships **preview** releases first — `0.1.0a1`, `0.1.0b2` and
so on. They are labelled everywhere it is cheap to label them: in the version
number, in the integration's name in the *Add integration* dialog, and as a
notice under **Settings → Repairs** that stays there for as long as the
version is a preview.

> **You probably want [`main`](../../../tree/main) instead.** That is the YAML
> package: five years of evolution, in use by thousands of people, and the
> only part of this project that is finished. A preview is for people who
> want to help find what is broken.

## The short version

**HACS cannot install this yet.** Not because a release is missing — one
exists — but because of *where HACS looks*, which is explained in
[Why HACS does not work yet](#why-hacs-does-not-work-yet). Until the
integration reaches the repository's default branch, installing a preview
means copying one folder.

That is four steps, and the third one is the one people forget.

## 1. Get the files

Every release has a source archive. From the
[releases page](../../../releases), open the release you want and download
**Source code (zip)** under Assets — or fetch a tag directly:

```bash
git clone --branch v0.1.0a2 --depth 1 \
  https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant.git
```

Take the tag, not the branch. `proper-ha-integration` moves whenever
development happens, and the whole point of a version number is being able to
say which code you are running when you report something.

## 2. Copy one folder into your configuration

Copy `custom_components/sungrow_modbus/` out of the archive and into your
Home Assistant configuration directory, so that this file exists:

```
<config>/custom_components/sungrow_modbus/manifest.json
```

Nothing else from the archive is needed — not `src/`, not `legacy/`, not the
scripts. The library the integration depends on comes from PyPI in step 3.

How you get the file there depends on how Home Assistant is installed:

| Installation | How to copy files in |
| --- | --- |
| Home Assistant OS | the **Terminal & SSH** or **Samba share** add-on, or **Studio Code Server** |
| Supervised / Container | the directory you mounted as `/config` |
| Core (venv) | the configuration directory you pass to `hass -c` |

## 3. Restart Home Assistant, and let it fetch the library

**This step needs working internet access**, and it is the one that surprises
people. The register knowledge lives in a separate Python package,
[`sungrow-modbus`](https://pypi.org/project/sungrow-modbus/), pinned exactly
in `manifest.json` — so on the first start after you copy the folder in, Home
Assistant pip-installs it, exactly as it does for a built-in integration.

Consequences worth knowing:

- The first start is **slower**, and the log will mention installing
  requirements. That is normal.
- If it cannot reach PyPI, setup fails with `RequirementsNotFound` and the
  integration will not appear. That is a network problem, not a bug in the
  integration.
- The pin names the pre-release exactly, so `pip` installs it without needing
  `--pre`. You do not have to do anything about this; it is stated because a
  pre-release usually *does* need that flag.

## 4. Add it

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

## Updating to a newer preview

Replace the folder with the one from the newer tag and restart. Home
Assistant notices the changed pin in `manifest.json` and installs the
matching library version on the way up.

The config entry survives, and so do your entities and their history.

## Going back

1. **Settings → Devices & services → Sungrow Modbus → delete the entry.**
2. Delete `<config>/custom_components/sungrow_modbus/`.
3. Restart.

If you chose to keep the YAML package's entity ids, the history is now
attached to the integration's entities and returning to the YAML package
needs the reverse migration —
[integration_migration.md](integration_migration.md) covers it, and it is
reversible: a rename moves the recorder rows rather than copying them, so
nothing is duplicated and nothing is lost.

## Why HACS does not work yet

Worth stating precisely, because "there is a release now" sounds like it
should be enough and is not.

HACS decides which version of a repository to read in this order: the latest
**stable** release, then a tag the user has explicitly selected, then the
repository's **default branch**. A pre-release does not count as a stable
release — HACS records it separately and never uses it to make that decision.
Turning on *Show beta versions* changes which versions HACS offers you
**after** it has accepted the repository; it does not change which version
HACS reads in order to accept it.

This repository's default branch is `main`, which holds the YAML package and
has no `custom_components/` directory at all. So HACS reads `main`, finds no
integration there, and rejects the repository with *"Repository structure for
main is not compliant"*.

That resolves itself when any of three things happens, and all are in
[integration_plan.md](integration_plan.md):

- the integration is merged into `main`, which is where this is going — the
  integration is meant to **replace** the YAML package, not sit beside it;
- a **stable** release is cut, at which point HACS reads that release instead
  of the branch; or
- a **preview channel** exists: a separate repository whose default branch
  *is* the integration, which HACS therefore accepts. Its URL is what you add
  under **HACS → ⋮ → Custom repositories**, category *Integration*, and the
  install becomes the ordinary two clicks — which is the point of it.

  [doc/preview-mirror/sync.yml](preview-mirror/sync.yml) is the whole
  mechanism: one workflow, dropped into that repository, which polls a few
  times an hour and copies the **development branch** from here —
  `custom_components/`,
  `hacs.json` and a README of its own, and nothing else. It **pulls rather
  than being pushed to**, which is why it needs no credential in either
  repository: reading this one takes no token because it is public, and
  writing to itself uses its own.

  So that channel is a **rolling** one: you get the integration as it is
  being written, and an update arrives whenever the files HACS installs
  actually change. A commit here that touches only `src/`, the scanner or
  the documentation produces nothing there, so it does not notify you.

  Two refusals keep it usable. It publishes the newest commit whose **CI
  passed**, walking back from the branch head rather than insisting on it —
  a documentation-only commit has no checks at all, and stalling behind one
  would hold back the good commit underneath. And it will not publish a
  commit whose **pinned library cannot serve it**: Home Assistant installs
  that library from PyPI, so a commit that imports a module the pinned wheel
  does not contain cannot start, and the channel stays on the last good
  commit until the library is released. That is not hypothetical — see
  `scripts/check_pinned_library.py`, which is the check it runs.

  It is temporary, and it has one rule: **remove it from HACS before
  installing from this repository**, once the integration reaches `main`.
  Both provide the same integration at the same path, so keeping both is a
  conflict rather than an upgrade.

Once one of those is true, installing a preview through HACS becomes: add the
repository under **HACS → ⋮ → Custom repositories** with category
*Integration*, open it, enable **Show beta versions**, and pick the preview
you want.

## What to do when something is wrong

Two things make a report actionable, and both are read-only.

**Diagnostics.** Settings → Devices & services → Sungrow Modbus → ⋮ →
**Download diagnostics**. It carries what the integration read, what it
decided about your hardware, and what failed, with the serial and address
removed.

**A survey**, if you are willing to run one command. It reads and never
writes, takes 5–40 minutes depending on the link, and produces both a file
you can publish and a private one that stays on your machine — see
[contributing a fingerprint](device-fingerprints/README.md#contributing-one).
It is how this project learns what varies between installations, which is the
thing no specification has told it reliably.

Then open an issue with **which code you installed**, because that is what
makes the rest of the report usable.

- Installed from a **tag**, by copying the folder: the version, `0.1.0a2`.
- Installed through the **preview channel** in HACS: the **commit hash** HACS
  shows you. That channel follows a branch and publishes no releases of its
  own, so HACS displays a hash instead of a version — and between releases
  several of those hashes share one version number, which means the version
  alone does not say which code you ran. The hash belongs to the preview
  repository; its commit message names the commit here that it came from.

Either way it is worth more than a report that says "the new integration".
