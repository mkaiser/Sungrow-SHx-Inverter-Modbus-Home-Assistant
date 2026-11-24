# T081 - The included cards: keeping them current, and crediting their author

`power-flow-card-plus` and `energy-flow-card-plus` by flixlix (Luca Félix, MIT) ride in the library's wheel
(`src/sungrow_modbus/cards/`, not committed; `scripts/release/fetch_cards.py` fetches, verifies and renames them).
Two things are left: how they stay current, and how the author is thanked.

## Status log

- **2026-11-24**: planned, nothing built. The versions and SHA-256 digests are written in `fetch_cards.py` (`POWER`,
  `ENERGY`) and move only by hand: v0.6.1 and v0.5.1, both from 2026-11-10.

## Keeping them current

**Not Renovate.** A bump is a version, a digest and, possibly, three patches that match minified code
(`Card.patches`); a regex rule can write the first two and cannot know the third broke. A bot's pull request that
merges green would ship an upstream file nobody read, into every user's browser. What we want is **a person looks at each
bump, and a machine does the arithmetic**.

1. **`.github/workflows/cards.yml`, weekly and on demand.** For each card: the latest GitHub release of its repository
   (`gh api repos/flixlix/<repo>/releases/latest`), skipping pre-releases. Newer than the pinned version: download the asset,
   compute its SHA-256, run `Card.patched` on it, and open **one pull request** against the integration branch that
   changes only `VERSION` and the digest in `fetch_cards.py`. The patch's failure (`expected exactly one ...`) is the
   result worth having: the run goes red and the pull request says why instead of being opened green.
2. **The review is the pull request's body**: both versions, the release notes upstream wrote, the diff of the two bundles'
   size, and a checklist -- load the dashboard on the scratch instance, *Home -> Today* and *Now* draw, no console error.
   Nothing merges by itself, and a release is the maintainer's as ever.
3. **A test that fails on a stale pin** is not wanted: a card a month old is no fault.
4. **`doc/maintainer_setup.md`** gets a section: what the workflow does, how to bump by hand
   (`python scripts/release/fetch_cards.py` after editing the two lines), and that a new patch means reading the new bundle.

Cost: one small workflow and a section; no new dependency. Needs from the maintainer: permission for the workflow to open
pull requests (repository setting *Allow GitHub Actions to create pull requests*).

## Crediting the author

MIT asks only that the licence text travel with the code, and it does: `LICENSE.power-flow-card-plus` is in the wheel, a
header names each bundle, and `doc/attribution.md` and `doc/dashboard.md` name the author. What is left is to be seen
doing it, in three places users read, and one the author does.

### README, *Acknowledgements*

A third group after the wallbox sources, in the section's voice (what it gave us, not that it is good):

> The dashboard's power flow and the day's energy flow are drawn by two cards from one author, who published them under
> the MIT licence:
>
> - **[flixlix/power-flow-card-plus](https://github.com/flixlix/power-flow-card-plus)** (v0.6.1) and
>   **[flixlix/energy-flow-card-plus](https://github.com/flixlix/energy-flow-card-plus)** (v0.5.1), by Luca Félix. They
>   come with the integration unchanged but for the element's name, so that nothing needs HACS and a copy of yours is
>   left alone. Their licence travels in the package.

The versions in that text are the pins, so a bump of `fetch_cards.py` edits the README line too: a test
(`tests/test_dashboard.py`) holds the README's two versions to `fetch_cards.POWER` and `ENERGY`, so they cannot drift.

### The dashboard

- **Where**: the Diagnosis view's *Info* group, beside *Integration* and *Device page*, as a third link button,
  **Power flow cards by flixlix** (`Leistungsflusskarten von flixlix`), opening `https://cards.flixlix.com` in a new tab.
  Not on Home: a credit beside a circle is clutter every day for something needed once.
- **How**: a new layout card `{"type": "credit-link"}` built like `integration-link` (`linkButton`, an external address
  instead of a path), its two texts in `shared.js`. It shows only where the flow cards could be shown, so it is left out
  for a house with neither (no inverter in the family).
- **Revision**: the views change, so `layout.json`'s `revision` rises, `changes` gets a line, and the digest in
  `tests/test_dashboard_layout.py` follows. `doc/dashboard.md` names the link in *Diagnosis* and the credit in
  *The power flow*, which already carries the author's name.

### Release notes

- **A standing line in the tag message** while the cards ship, for every release, not only one that moves them:
  *"Power and energy flow cards by flixlix (MIT): power-flow-card-plus v0.6.1, energy-flow-card-plus v0.5.1."* A release
  that bumps a card says so in its own bullet above it, with what changed upstream in a sentence.
- **Where it is written down**: `doc/maintainer_setup.md` (the paragraph on the tag message as the release note) and the
  release skill's step 3, so the next session adds the line without being told; the versions come from
  `scripts/release/fetch_cards.py`.

### The author

- **Telling them**, once, as a courtesy and not a request for leave: an issue on `flixlix/power-flow-card-plus`
  (discussions are off) that says the cards are bundled unchanged except for the element's name, links the integration,
  and thanks them. It is outward-facing and in the maintainer's name, so **the maintainer sends it, or says so**; the text is
  drafted in the session that does it, and one issue covers both cards.
- **Supporting them**: neither repository carries a funding file, and the profile names no sponsor page. Nothing to link
  until they publish one; look again at each bump.

## Order

1. The README group and its test, the release-note line (maintainer_setup, the release skill) and the *Info* link with its
   layout revision -- one small change.
2. The workflow and its section, tried once on a `workflow_dispatch` run against the current pins (it must open nothing).
3. The note to the author, with the maintainer.
