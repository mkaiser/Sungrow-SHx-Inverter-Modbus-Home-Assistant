# gerd's WiNet-S and wallbox, their TLS certificate, 2026-11-06

Taken by the maintainer's session over a VPN, with the five-second script in
`device-survey/devices-wanted.md` extended to decode the certificate: one TLS connection to port 516
of gerd's WiNet-S, then, twelve seconds later, one to port 516 of his wallbox at its own address.
No Modbus was read. No address, no serial.

| | WiNet-S | Wallbox (AC22E-01) |
| --- | --- | --- |
| SHA-256 of the DER certificate | `84505e46778f2611df26ed1ad8a4e872945f7eb33e050e617c96a73add005b5b` | `84505e46778f2611df26ed1ad8a4e872945f7eb33e050e617c96a73add005b5b` |
| Subject | `CN=sun,OU=sun,O=OT,L=NJ,ST=JS,C=CN` | the same |
| Issuer | `CN=OT.SUNGROW,OU=sungrow,O=OT,L=NJ,ST=JS,C=CN` | the same |
| Serial number | 0x1 | 0x1 |
| Valid | 2024-10-24 to 2054-10-17 | the same |
| Key | RSA, 2048 bits | the same |
| Protocol, cipher | TLS 1.2, `ECDHE-RSA-AES256-GCM-SHA384` | the same |
