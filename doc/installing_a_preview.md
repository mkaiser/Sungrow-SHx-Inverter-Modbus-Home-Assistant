# Installing the preview

This integration is a **preview**, labelled as one in its version number, in
its name in *Add integration*, and by a notice under **Settings → Repairs**.

> **You probably want [`main`](../../../tree/main) instead**: the YAML
> package, in use by thousands of people and the only finished part of this
> project. A preview is for people who want to help find what is broken.

**A preview sets up diagnostics only.** It identifies your inverter, works out
which registers it answers and gives you a survey to send back. It creates
**no sensors for the readings**. The full setup is built; it waits because
choosing whether to take over `modbus_sungrow.yaml`'s entity ids decides
where years of history attach, and that is not a thing to hand somebody in
an alpha. An entry made now can be upgraded later without losing anything.

It installs through **HACS**, from a second repository, the *preview
channel*: HACS reads a repository's default branch, and this one's is the
YAML package. Four steps; the third is the one people forget.

## 1. Add the preview channel to HACS

**HACS → ⋮ (top right) → Custom repositories**:

| Field | Value |
| --- | --- |
| Repository | `https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant-preview` |
| Type | **Integration** |

![HACS custom repositories dialog with the preview repository added as an Integration](../device-survey/images/HACS-add-custom-repository.png)

HACS itself needs a GitHub account (it asks for a device code at
<https://github.com/login/device>). Any account works; it is not tied to this
integration.

## 2. Download it

Open the repository HACS lists and press **Download**. The version shown is a
**commit hash**: the channel follows the development branch and publishes no
releases of its own, so the hash is what identifies your code. Quote it in
bug reports.

## 3. Restart, with internet access

The register knowledge is a separate Python package,
[`sungrow-modbus`](https://pypi.org/project/sungrow-modbus/), pinned in the
integration's `manifest.json`. On the first start Home Assistant
pip-installs it, so that start is slower and needs to reach PyPI. Without it,
setup fails with `RequirementsNotFound` and the integration does not appear:
a network problem, not a bug.

## 4. Add the integration

**Settings → Devices & services → Add integration →** search for
**Sungrow Modbus (preview)**.

![Add integration searching for Sungrow modbus, showing Sungrow Modbus (preview)](../device-survey/images/HACS-add-integration-sungrow-modbus.png)

Choose **Perform the device survey**.

![The first screen, offering Perform the device survey](../device-survey/images/HA-settings-configure-integration.png)

**Search my network** probes the range you confirm and identifies what
answers; or type the address (behind a WiNet-S, the dongle's). Where more than
one device answers, it lists them with each inverter's part in a cluster.
Last come a few questions no register can answer, all optional and editable
later under **Configure** ([every option](integration_options.md)).

## Running the survey

On the device page (Settings → Devices & services → Sungrow Modbus → the
device):

![Device page with the two diagnosis buttons](../device-survey/images/HA-settings-device-start-survey.png)

- **Run read only diagnosis** reads and never writes. The sensors beside it
  show progress; when it finishes, a notification links the document for an
  hour, and **Download diagnostics** carries the same document for good.
- **Run complete diagnosis and tests** adds the control test, which writes
  settings and puts them back. Read
  [what it does, and how to opt out](../device-survey/README.md#it-reads-and-writes-only-if-you-say-yes)
  first.

Send the document to
[the survey issue](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/786).
For a bug, open an issue with **Download diagnostics** (serial and address
removed) and the commit hash HACS shows.

## Updating

HACS offers an update whenever the channel moves; a commit that changes
nothing you install does not notify you. Press **Update**, then restart: Home
Assistant installs the library version the new pin names. The entry, its
entities and their history survive.

## Going back

1. **Settings → Devices & services → Sungrow Modbus →** delete the entry.
2. **HACS →** the integration **→ ⋮ → Remove**.
3. Restart.

If you took over the YAML package's entity ids, returning to the package needs
the reverse migration in [integration_migration.md](integration_migration.md).

Once the integration reaches `main`, **remove the preview channel from HACS
before installing from this repository**: both install the same integration
at the same path.
