# T056 - Helping users set up the Energy dashboard

The guide is written and linked from the README (`doc/energy_dashboard.md`:
hybrid, SG, battery, wallbox, several inverters with a Sum helper for one
power total), and the ordinary setup's success dialog links it
(`ENERGY_DASHBOARD_GUIDE_URL`).

**Nothing can pre-fill the dashboard** (checked against Home Assistant
2026.11): core's `energy` component offers an integration only the solar
*forecast* platform, and the sources are the user's own preferences, so
anything that writes them needs an explicit action and a confirmation, never
a setup step.

The dashboard's Energy view names the house's own entities field by field
(`frontend/energy-setup.js`), and while nothing is set up an administrator
with one inverter can have them added (`energy/save_prefs`, confirmed, never
over an existing setup). Checked on the simulator 2026-11-24, where
`energy/validate` reported only statistics not there yet; released in 0.1.0a54. The
grid power's sign (import positive) is what 26 of the committed diagnoses show.

Unverified, each answered by one house, and stated as open in the guide:
whether the import and export totals need a meter fitted (what a house
without one reads), and whether the *Total …* energies, which keep the YAML
package's `total` state class, behave across an inverter reset. Feeds
`legacy/doc/dashboard.md`'s Energy dashboard row.
