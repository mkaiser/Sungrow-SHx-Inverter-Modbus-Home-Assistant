---
type: source
title: mkaiser-self-consumption-standby-2026-11-21.md
source_path: raw/mkaiser-self-consumption-standby-2026-11-21.md
ingested: '2026-11-21'
created: '2026-11-21'
tags:
  - mkaiser
  - self-consumption
  - home-assistant
---

# The inverter self-consumption estimate in Standby, 2026-11-21

[mkaiser](../entities/installation-mkaiser.md)'s SH10RT on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md) in Standby at night, battery empty, read from
the production Home Assistant's recorder. Source: `raw/mkaiser-self-consumption-standby-2026-11-21.md`.

| Fact | Evidence |
| --- | --- |
| In Standby PV and battery read 0, so the estimate is import minus load: 1990 - 1986 W, read as 4.6 W | one moment's states |
| **Over 2.5 h of Standby the estimate centred on zero**: median 0.6 W, range -181 to 174 W | the recorder's series, 1738 values |

## What it means

- The inverter's own draw passes through the meter and is counted in the load it reports, so the
  balance cannot see a Standby draw. A few watts at night looks plausible and is chance.
- Kept as a number all the same, by the maintainer's call (2026-11-21); the by-day reading is
  [the production install](mkaiser-production-install-2026-11-21-summary.md)'s.
