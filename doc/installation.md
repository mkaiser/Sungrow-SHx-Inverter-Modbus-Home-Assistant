# Installation / Configuration

Starting with **v2.0**, this project ships as a proper Home Assistant custom
integration (`sungrow_shx`) — no `!include`, no `packages:`, no edits to
`secrets.yaml`. Everything is driven from the UI.

If you are upgrading from the pre-2.0 YAML package, read
[`migration_guide.md`](migration_guide.md) first.

## Prerequisites

- **Home Assistant 2024.11 or newer.** <!-- TODO: verify minimum HA version against manifest.json -->
- **[HACS](https://hacs.xyz/)** installed (recommended). Users without HACS
  can drop `custom_components/sungrow_shx/` into their HA config directory
  manually — see below.
- Basic admin access to your Home Assistant instance (to restart it and add
  integrations).

### Network prerequisites

- The inverter must be **reachable from the Home Assistant host on TCP
  port `502`** (Modbus). Prefer the inverter's internal LAN port; WiNet-S
  Ethernet and Wi-Fi also work, but with more jitter.
- You need the inverter's **IP address** and its **Modbus unit ID / slave
  address** (default `1`). If a battery is connected, you also need the
  **SBR slave ID** (default `200`); use `0` if no battery.
- If your router or host firewall restricts outbound traffic, open a rule
  for `<HA host> → <inverter IP>:502/tcp`.
- If you run multiple controllers, make sure only one is polling the
  inverter at a time — Sungrow's Modbus endpoint does not handle parallel
  masters well.


## Install via HACS (recommended)

1. Open **HACS** in the Home Assistant sidebar.
2. Click the **⋮** menu (top right) → **Custom repositories**.
3. Paste the repository URL
   `https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant`,
   set category to **Integration**, and click **Add**.
4. Search for **Sungrow SHx Inverter** in the HACS integration list and
   click **Download**.
5. **Restart Home Assistant.**

Alternative one-click entrypoint (opens the HACS dialog pre-filled):
[Add to HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=mkaiser&repository=Sungrow-SHx-Inverter-Modbus-Home-Assistant&category=integration).
<!-- TODO: verify the my.home-assistant.io redirect URL once the repo is registered with HACS default -->


## Install without HACS (manual custom component)

1. Download or clone this repository.
2. Copy the directory
   `custom_components/sungrow_shx/` into your Home Assistant config folder
   so the final path is `<config>/custom_components/sungrow_shx/`.
3. Restart Home Assistant.

HACS is still the recommended path because it handles updates automatically.


## Add the integration

1. Go to **Settings → Devices & services → Add Integration**.
2. Search for **Sungrow SHx Inverter**.
3. Fill in the form:

   | Field | Description | Default |
   |---|---|---|
   | Host | IP or hostname of the inverter | — |
   | Port | Modbus TCP port | `502` |
   | Slave ID | Inverter unit ID | `1` |
   | SBR Slave ID | Battery stack unit ID (`0` = no battery) | `200` |
   | Battery max power (W) | Upper bound for charge/discharge numbers | `5000` |
   | Inter-request delay (ms) | `5` for LAN, `20`+ for WiNet-S | `5` |

4. Click **Submit**. The integration creates a device and its sensors,
   switches, numbers and selects.

### Options (scan intervals)

Open **Settings → Devices & services → Sungrow SHx Inverter → Configure**
to tune the four polling buckets: realtime (5 s), fast (10 s), medium (60 s),
slowest (600 s).


## Multi-inverter setups

Repeat *Add Integration* once per inverter. Each config entry is an
independent device with its own entities. The old
`modbus_sungrow_multiple_inverters_{1,2,3}.yaml` files and the regex-based
generator script are no longer required.


## Post-install sanity check

1. Go to **Settings → Devices & services → Sungrow SHx Inverter → *(device)***.
2. In the entity list, find a known entity such as
   **Total DC power** (`sensor.sungrow_inverter_total_dc_power`).
3. If it is disabled by default, click the entity → **Settings** →
   toggle **Enabled** → **Update**.
4. Return to the entity and confirm it has a non-`unknown` value within
   the first polling cycle (≈ 5–15 s).

If you also want to use the Home Assistant Energy Dashboard or the
bundled default dashboard, follow [`dashboard.md`](dashboard.md).


## Troubleshooting

- **`cannot_connect` when submitting the config flow.**
  The HA host cannot reach the inverter on TCP `502`. Check:
  - IP address is correct and the inverter is online,
  - no firewall (router, OS, or Docker network) is blocking the port,
  - only one Modbus master is talking to the inverter at a time,
  - for WiNet-S, try raising the inter-request delay to `20` ms or more.

- **`invalid_slave` (or no data after connect).**
  The Modbus unit ID you entered does not match the inverter. Verify the
  **Slave ID** / unit ID in the inverter's Modbus settings (on the local
  display or in iSolarCloud) and re-run the config flow.

- **Battery entities are missing / show `unknown`.**
  The SBR slave ID is wrong or no battery is attached. If you have no
  battery, set **SBR Slave ID** to `0` in the integration options; the
  battery-specific entities will then be skipped cleanly instead of
  staying unavailable.

- **Orphaned / duplicate entities after migrating from YAML.**
  See [`cleanup_entities.md`](cleanup_entities.md) to remove them.

- **Anything else.** See [`faq.md`](faq.md) and the
  [GitHub discussions](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/discussions).
