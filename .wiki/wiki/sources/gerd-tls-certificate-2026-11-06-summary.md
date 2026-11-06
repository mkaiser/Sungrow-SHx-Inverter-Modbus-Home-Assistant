---
type: source
title: gerd-tls-certificate-2026-11-06.md
source_path: raw/gerd-tls-certificate-2026-11-06.md
ingested: '2026-11-06'
created: '2026-11-06'
tags:
  - winet-s
  - wallbox
  - tls
  - gerd
---

# gerd's WiNet-S and wallbox, their TLS certificate, 2026-11-06

The first certificate *hash* this project has recorded, from port 516 of
[gerd](../entities/installation-gerd.md)'s [WiNet-S](../entities/device-winet-s.md) and of his
[wallbox](../entities/device-wallbox.md) at its own address. Source:
`raw/gerd-tls-certificate-2026-11-06.md`.

- **The two are the same certificate, byte for byte**: SHA-256
  `84505e46778f2611df26ed1ad8a4e872945f7eb33e050e617c96a73add005b5b`, serial number 0x1,
  RSA-2048, `CN=sun` issued by `OT.SUNGROW`, valid 2024-10-24 to 2054-10-17.
- Two different Sungrow products serving one certificate, with serial number 1 and a thirty-year
  validity, is what a certificate built into the firmware looks like, not one made per device. If
  so, its private key ships with every unit, and this TLS encrypts the link but authenticates
  nothing.
- **Not yet proven across houses.** Both readings are from one house. The same hash from a
  WiNet-S anywhere else settles it.
