# bar12's WiNet-S, its TLS certificate, 2026-11-06

Taken by the maintainer's session over a VPN to bar12, after the house was confirmed by an identity
read through the same address: unit 1 there answered as an SH10RT-20 with the stand-in
`anon-81257679535`. One TLS connection to port 516 of the WiNet-S; no Modbus over TLS. No address,
no serial.

| | WiNet-S |
| --- | --- |
| SHA-256 of the DER certificate | `84505e46778f2611df26ed1ad8a4e872945f7eb33e050e617c96a73add005b5b` |
| Subject | `CN=sun,OU=sun,O=OT,L=NJ,ST=JS,C=CN` |
| Issuer | `CN=OT.SUNGROW,OU=sungrow,O=OT,L=NJ,ST=JS,C=CN` |
| Serial number | 0x1 |
| Valid | 2024-10-24 to 2054-10-17 |
| Key | RSA, 2048 bits |
| Protocol, cipher | TLS 1.2, `ECDHE-RSA-AES256-GCM-SHA384` |

The hash equals the one taken at gerd's WiNet-S and wallbox the same evening.
