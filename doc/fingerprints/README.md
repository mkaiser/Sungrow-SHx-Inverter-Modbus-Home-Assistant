# Capability fingerprints

What a particular Sungrow installation actually answers, recorded by
`python scripts/discover_probe.py capabilities <host> --save doc/fingerprints`.

These are the evidence the capability model is built from. The register map is
one map for every model, but which parts of it a device answers varies by
model, phase count, wiring, transport and firmware — so a fingerprint from a
real machine is worth more than an inference from the YAML's comments.

## Three files, and why

`--save` writes three things per read:

| File | Contents | Published? |
| --- | --- | --- |
| `.capabilities.json` | Which registers answered — `present`, `unavailable` (the specification's `0xFFFF` convention), `refused`, `no answer` — plus device type code and output type | **Yes** |
| `.readings.json` | The values, with the serial replaced and the host dropped | **Yes** |
| `.raw.json` | The values with the real serial, host and exact time | **No** — gitignored |

The **fingerprint** is what the capability model is built from, and it is
identical between two reads an hour apart, so it diffs usefully when firmware
changes.

The **readings** are a decoding fixture, and that is worth more than it
sounds: real values from real hardware are what prove a scale factor, a word
order or a signedness right. A meter reading of `62658` decoding to −2878 W
demonstrates the signed 16-bit interpretation in a way a synthesised number
never could, and the same captures can seed the simulator so it behaves like
an inverter rather than like plausible arithmetic.

What makes a raw read private is not the values on their own but the serial,
the host and the exact time together — a timestamped set of live power,
battery and meter readings is a statement about when somebody was at home. So
the published file replaces the serial with a **stand-in of the same shape**,
derived from a hash of the real one so a machine always maps to the same
stand-in, drops the host, and rounds the time to the day. The shape is
preserved because the string decoder is itself under test.

If you are publishing a reading from **somebody else's** installation, ask
them first. A stand-in serial is not consent.

## Contributing one

If you have a model that is not here — especially an RS, an MG, a T-series, or
anything with a wallbox, an SBR battery or a Logger — a report from it is the
single most useful thing you can send.

Download [scripts/collect_fingerprint.py](../../scripts/collect_fingerprint.py)
and run it against your inverter:

```bash
python collect_fingerprint.py 192.168.1.50
```

It needs **nothing installed** — plain Python 3.9 or newer, no packages — and
it **only reads**: the two Modbus read function codes are the only ones the
file implements, and you are welcome to check before running it. It writes one
JSON file and publishes nothing by itself.

Look at the file, then attach it to an issue if you are happy to. Your serial
number is replaced with a stand-in and your inverter's address is not in it.

If the output says the device hung up several times, that is normal on Sungrow
hardware — the script reconnects around each one, so the report is still
complete.

Maintainers working in this repo can use
`python scripts/discover_probe.py capabilities <host> --save doc/fingerprints`
instead, which uses the device library and writes the private `.raw.json`
alongside.
