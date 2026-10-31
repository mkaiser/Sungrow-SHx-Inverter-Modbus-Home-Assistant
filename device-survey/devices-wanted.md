# Devices wanted

**Which measurements are still missing, and what each one would settle.**
What has been measured is [compatibility.md](../doc/compatibility.md).

**How to send one:** [Contributing your device survey](README.md#contributing-your-device-survey).

## Most wanted

In the order it would help. Each line names what one survey settles;
details are under [Why each one](#why-each-one).

| # | Device or situation | What one survey settles |
| --- | --- | --- |
| 1 | **Any single-phase inverter** (RS, K or MG family) | Nothing single-phase has ever been read; 18 of the 42 models are. Every capability the RS family is given today is an inference |
| 2 | **An iHomeManager** (unit 247, port 502, 503 or 504) | The first reading of the device at all. Its Modbus TCP must be opened in the app first, see [item 2](#2-an-ihomemanager) |
| 3 | **An SH-T (SH15T, SH20T…) on its own LAN port**, with the control test, in daylight | Every T so far was read through a WiNet-S. Settles the export limit's write scale (register 13074) on P071, the PV cut on P071, and an SBH pack on a direct link |
| 4 | **A Sungrow Logger1000, 3000 or 4000** | The first reading. Answer *a Logger* to the transport question so the survey also reads the Logger itself |
| 5 | **A wallbox other than the one already read**, an AC011E-01 above all | Which of its registers identify a unit and which are a model constant, and a scale another source reads differently |
| 6 | **A charging car**, at any house with a Sungrow wallbox | What input 21313 does over a session, and whether 21308/21310 are signed. Two runs a few minutes apart while charging |
| 7 | **Version 1 between `.95.03` and `.95.12`, or a `.95.14` that is not 10 kW** | Where the export limit's write scale changes ([#763](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/763)) |
| 8 | **An SBR other than SBR096, SBR128 or SBR160** | Battery sizes nobody has read |
| 9 | **A second master/slave cluster** | Whether a slave's address 2 is a rule or one house's convention |
| 10 | **Any inverter behind a Modbus proxy** | What a proxy does to the readings; no document has one |
| — | **A WiNet-S certificate hash**, five seconds, no survey | Whether every WiNet-S shares one TLS certificate, see [the last item](#a-winet-s-certificate-hash) |

## Not needed any more

Already read several times over. Please send one of these **only** if it
differs from what is in [`results/inverter/`](results/inverter/) in one of the ways below:

- an **SH10RT, SH10RT-20 or SH10RT-V112 on P023**, on either path (five
  houses);
- an **SH8.0RT-V112 on P022** or an **SH6.0RT-V112 on P023**;
- an **SBR096** behind any of those.

It is still worth sending when it brings **a firmware update** since your
last survey (that is how a silent change is noticed), **the first control
test** for its model and firmware, **both paths** of one machine minutes
apart, or a **battery size** nobody has read.

## Where the coverage is today

28 documents from 10 houses: 11 inverters, 13 inverter documents with a
control test, and one wallbox read at its own address.

| Axis | Covered | Missing |
| --- | --- | --- |
| Inverter model | **7 of 42**: SH10RT, SH10RT-20, SH6.0RT-V112, SH8.0RT-V112, SH10RT-V112, SH15T, SH20T | every model outside RT and T |
| Product family | RT and T | RS, MG, RL, K, CX |
| Phase / output type | three phase 3P4L only | **single phase**, and three phase 3P3L |
| Inverter firmware | `B001.V000.P020`, `P022`, `P023`, `B000.V000.P071` | a fifth |
| Version 1 | `SAPPHIRE-H_01011.95.03`, `.95.12`, `.95.13`, `.95.14`, `PEARL-H_01011.01.45` | see item 7 |
| Communication module | WiNet-S `P040`, `P043`, `P044`, `P045`; WiNet-S2 `P032`, `P033` | a Logger |
| Battery | SBR096, SBR128, SBR160, SBH200, SBH400, one Pylontech | the other SBR and SBH sizes, other third-party packs |
| Transport | direct LAN, WiNet-S and WiNet-S2, wired and WiFi | a Logger, a Modbus proxy, **a T on its own LAN port** |
| Wallbox | AC22E-01 | AC011E-01, AC007-00 |
| iHomeManager | none | any |
| Sungrow Logger | none | any |

## Why each one

What has been measured, and what each answer would change, is in the
[wiki](../.wiki/wiki/index.md); these say only why a survey is wanted.

### 1. Any single-phase inverter

Nothing single-phase has been read. Every RS capability in
[compatibility.md](../doc/compatibility.md) is inferred from the family; one
survey confirms the lot or finds the first exception. Fewer entities than the
YAML package gave on the same machine is itself a finding.

### 2. An iHomeManager

Never measured. **Open its Modbus TCP first**, in the iSolarCloud app:
*iHomeManager settings → Forwarding channel settings*, port 502, 503 or 504,
SSL off. Each port takes one connection, so stop other clients. The survey
finds it at unit 247 and writes a document of its own. It may also silence
inverter registers 5741-5746 (#647, #651). See
[iHomeManager](../.wiki/wiki/entities/device-ihomemanager.md).

### 3. An SH-T on its own LAN port, in daylight

Every T so far was read through a WiNet-S. Run it with the control test, PV
cut allowed: it settles 13074's write scale and the PV cut on P071, and reads
an SBH pack's cell layout, which a dongle refuses. See
[SH-T](../.wiki/wiki/entities/device-sh-t.md).

### 4. A Sungrow Logger1000, 3000 or 4000

Never measured; it fronts a whole installation, the shape the
one-entry-per-endpoint design was built for. **Answer "a Logger" to the
transport question** so the survey also reads it at unit 247, and say which
unit ids it lists. See [Logger](../.wiki/wiki/entities/device-logger.md).

### 5. A wallbox other than the AC22E-01

Sungrow publishes no register document. An AC011E-01 would settle the output
current setting's scale, 0.1 A here against 0.01 A in another source's
AC011E-based map ([wallbox_registers.md](../doc/wallbox_registers.md)). The
survey finds one behind a WiNet-S, or at its own address on port 516.

### 6. A charging car

Two runs a few minutes apart while a car charges: what input 21313 does over
a session, and whether 21308/21310 are signed.

### 7. Version 1 between `.95.03` and `.95.12`, or a `.95.14` that is not 10 kW

13074 stores a written word 1:1 only on `.95.03` and multiplies it by ten on
every later firmware measured ([register 13074](../.wiki/wiki/entities/register-13074.md),
[#763](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/763)).
A machine in between places the change: `survey.sh control <host>
--export-scale` asks with one write that changes nothing. A `.95.14` that is
not 10 kW tells "0.1 % of rated power" from "10 W" apart, which coincide at
10 kW.

### 8. An SBR other than SBR096, SBR128 or SBR160

Sizes nobody has read ([SBR battery](../.wiki/wiki/entities/device-sbr-battery.md)).

### 9. A second master/slave cluster

One cluster gave two rules the config flow relies on: a slave's device
address is 2, and a slave answers 0 where a standalone inverter answers
0xFFFF. A second shows whether they are rules or one house's convention.

### 10. Any inverter behind a Modbus proxy

A proxy holds one connection and rebuilds every frame, so it changes what a
dropped or padded read means. No document has one.

### A WiNet-S certificate hash

Five seconds, no survey. A WiNet-S serves Modbus over TLS on port 516 with a
certificate that looks baked into the firmware. A hash from another site
shows whether every dongle shares one key:

```bash
python - <<'PY'
import hashlib, socket, ssl
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
raw = socket.create_connection(("YOUR.DONGLE.IP", 516), 8)
with ctx.wrap_socket(raw, server_hostname="x") as tls:
    print(hashlib.sha256(tls.getpeercert(True)).hexdigest())
PY
```

## Also worth sending

- **Both transports of one machine**, minutes apart: every such pair so far
  produced a rule.
- **The same machine after a firmware update**: updates arrive silently.

## Not wanted

- Readings from an installation whose owner has not agreed. A stand-in serial
  is not consent.
- A reading taken while something else polled the inverter.
