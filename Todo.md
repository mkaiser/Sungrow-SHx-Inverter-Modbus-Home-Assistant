Todo.md contains only next steps (forward looking).
Anything done should be removed here.


## Fingerprint Folder restructuring
create a separate plan:

from fingerprint:
A: Address
    "ip_address_last_two_octets": "178.041",
    for recreation we need the complete local ip address. Can we just read the computers network interface and find the local LAN address (the first two octets, are not ALWAYS 192.168).
    Then we could just enter the last two octects in the command to recreate the fingerprint. This would be more user friendly and less error prone.

B.
  "read_on": "2026-09-08",
  "read_at_local": "2026-09-08T19:51:22+02:00",

  Why two values? one should be enough.

What is the difference between device-fingerprints/scripts/python/probe.py and src/sungrow_modbus/discovery.py?

# Summary (2026-10-16)

0.1.0a15 on PyPI: one launcher, `survey.{sh,cmd}`, which offers the control
test as its last question and runs it into the survey's document; the
survey's logic is in the package, so the published launchers run. Before it,
0.1.0a14: the wallbox at its own address (TLS 516, unit 248) in the
integration and the survey, and `direct-lan` in every cable document's name.
gerd's wallbox document is published in `device-fingerprints/`, beside the
inverter documents. Every site re-fingerprinted; control tests merged at
fwitten's master and gerd; the integration passed on gerd's hardware.
Open:

1. **A charging car at gerd's** for 21313 against 21308 over a session (does
   it go to 0 when charging stops?) and the signedness of 21308/21310. Two
   dongle runs about five minutes apart, 90 s of quiet before each, while the
   car charges.
2. Small items below.

# Next steps

## Fingerprinting

- `tests/test_no_real_serials.py`: decode runs of 16-bit integers that
  are printable ASCII pairs to text before matching the serial shape, so a
  serial stored as register words fails the suite (how gerd's leaked).
- `survey.sh control --simulated` exits 4: the simulator stores 13074 as
  handed and the run writes at the default x10 when the scale probe gives
  no answer, so leg B reports a wrong slope. Contradicts "a simulator
  cannot produce a finding".
- The fwitten master's LAN port takes ~39 min per survey: 13199 and the
  three firmware strings time out (10 s each) instead of refusing, and
  the narrowing retries them register by register.
- Windows: a `ConnectionResetError [WinError 10054]` traceback during
  identification; harmless, but reads as a failure.

## Integration

- A second entry for the same inverter on another endpoint aborts
  `already_configured`, even with the first disabled (the unique id is the
  serial). Decide whether one inverter may have a cable and a dongle entry
  -- CLAUDE.md says one entry is one endpoint.
- Optional: have the integration's own fingerprint carry `export_scale`
  once its entity has probed. It stores only the factor in entry data, not
  the write behind it.

## Wall box integration

Measured at gerd's AC22E-01 on 2026-10-14. Addresses are in memory, not here.

**What is now known**

- **Two ways to the wallbox's registers, both measured:**

  | Path | Protocol | Unit |
  | --- | --- | --- |
  | through the WiNet-S, at the dongle's address | plain Modbus TCP, port 502 | 3 |
  | directly, at the wallbox's own LAN address | Modbus TCP inside TLS, port 516 | 248 |

  Same wallbox: firmware string, lifetime energy and the live block agree
  word for word. Only unit 248 answers over TLS (0-255 swept). The wallbox
  has no port 502 and no web interface; its certificate is Sungrow-signed
  (issuer `OT.SUNGROW`, CN `sun`), byte-identical to the WiNet-S's at the
  same house -- so it authenticates nothing.
- **Not through the inverter's own LAN port.** No unit from 0 to 255 answers
  the wallbox's model name (input 21216) there; the link was alive -- unit
  1 answered its device type, 0x0E0E -- and the inverter itself goes silent
  on the wallbox's addresses rather than refusing them.
- **The direct path shows more than the dongle.** Where both answer, the
  dongle returns 0 for: input 21210-21213 (an ASCII identity-like string;
  not to be published until it is understood), 21240-21249 (a second
  version string, `V1.0...`), 21331-21335 (0xFFFF directly), 21359 and
  21362-21364 (values directly). Input 21267 reads 12372 directly, 0
  through the dongle. And the firmware string at 21226 reads whole.
  Holding registers: the same 50 addresses either way.
- **Over TLS a read must start on the first register of a data point.**
  Reproducible on fresh connections (21295 x24 answers, 21296 and 21300
  time out). The full map, one-register reads at every address (serial
  skipped), protocol addresses:
  - input: 21210, 21212, 21214, 21215, 21223, 21224, 21225, 21240, 21243,
    21258, 21261-21272, 21274-21279, then every second address 21281-21299,
    21301-21307, 21309, 21311-21317, 21319, 21321, 21322, 21326, 21330,
    21331, 21336, 21337, 21339-21345, 21347, 21349-21355, 21357,
    21359-21365, 21369, 21373, 21374;
  - holding: 21200, 21202-21204, 21206, 21208, 21210-21212, 21214-21216,
    21220, 21222-21233, 21249, 21281, 21297-21301, 21311-21317.

  Every mapped field starts on one (model name 21215, type code 21223,
  phases 21224, firmware 21225, nominal voltage 21261, phase mode 21269,
  minimum power 21271; the 32-bit live values every second address), so
  the map is also **the wallbox's own field layout**, undecoded registers
  included. Through the dongle any start works -- it reads the wallbox its
  own way.
- **The integration's reads already comply, and work over TLS through the
  real library**: `ModbusTlsParams(port=516, verify=False,
  check_hostname=False)`, unit 248 -- identity (input 21215 x20), ratings
  (21261 x12), live (21299 x23), settings (holding 21202 x10, 21231 x1) all
  answered.
- **The stack can reach it.** `modbus-connection` has `ModbusTlsParams`
  (`verify=False` for a self-signed device certificate), and Home
  Assistant's `modbus.async_get_unit` accepts it.

**To do**

- [ ] Decode what only the direct path shows: 21240-21249 (version
      string), 21331-21335, 21359, 21362-21364, 21267, holding 21249-21312.
      21210-21213 is masked until a second wallbox shows whether it
      identifies the unit.
- [ ] Still only a charging car can settle 21313 and the signedness of
      21308/21310 -- now readable both ways, which doubles the evidence.


# Future work
## modbus proxy
- investigate: Does it make sense to provide a modbusproxy from this integration? So evcc and other software can use the inverter and wallbox through this integration?
reuse existing modbusproxies, don't reinvent

OR: proide some kind of mqtt interface for inverter and wallbox to evcc. Does evcc have a standard config for this?

## Ihome Manager
https://github.com/TCzerny/ha-modbus-manager/blob/main/docs/Communication%20Protocol%20of%20iHomeManager_V1.0.2.pdf


## code cleanup

The wallbox device was created after the inverter device. Now in the pypi integration there is are specific wallbox_*.py files, but not inverter files, which is confusing.