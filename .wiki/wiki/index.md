# Wiki Index

## Entities

- [iHomeManager](entities/device-ihomemanager.md) — Slave 247 on 502, 503 or 504, no documented serial, read by the survey, never measured #ihomemanager #unmeasured
- [Sungrow Logger](entities/device-logger.md) — Logger1000/3000/4000 at unit 247, named by type code, read raw, never measured #logger #unmeasured
- [SBH battery](entities/device-sbh-battery.md) — High-voltage pack for the SH-T, unit 2 through a dongle #battery #sbh #sub-device
- [SBR battery](entities/device-sbr-battery.md) — Unit 200 direct, 2 through a WiNet-S; cells and modules not forwarded by a dongle #battery #sbr #sub-device
- [SH-RT hybrid inverters](entities/device-sh-rt.md) — Three-phase SAPPHIRE-H hybrids: what is established and which surveys show it #inverter #sh-rt #sapphire-h #three-phase
- [SH-T hybrid inverters](entities/device-sh-t.md) — SH15T and SH20T on PEARL-H, only read through a dongle #inverter #sh-t #pearl-h #three-phase
- [Sungrow AC wallbox](entities/device-wallbox.md) — Unit 3 through a WiNet-S or 248 over TLS at its own address; read only #wallbox #ac22e-01 #ac011e-01 #sub-device #tls
- [WiNet-S communication module](entities/device-winet-s.md) — Everything the dongle changes: refusals, zeros, stale readbacks, TLS on 516 #dongle #winet-s #transport
- [PEARL-H_B000.V000.P071](entities/firmware-pearl-h-b000-v000-p071.md) — SH-T firmware; 31211 answers, forced discharge acts, 13074's write scale not determined #firmware #pearl-h-b000-v000-p071
- [SAPPHIRE-H_01011.95.03](entities/firmware-sapphire-h-01011-95-03.md) — Older SH-RT numbering; the only firmware where 13074 writes 1:1 #firmware #sapphire-h-01011-95-03
- [SAPPHIRE-H_B001.V000.P020](entities/firmware-sapphire-h-b001-v000-p020.md) — SH-RT; 13074 writes x10, no PV cut #firmware #sapphire-h-b001-v000-p020
- [SAPPHIRE-H_B001.V000.P022](entities/firmware-sapphire-h-b001-v000-p022.md) — SH-RT; 13074 writes x10, the PV cut (31211) is confirmed #firmware #sapphire-h-b001-v000-p022
- [SAPPHIRE-H_B001.V000.P023](entities/firmware-sapphire-h-b001-v000-p023.md) — SH-RT, most measured; 13074 writes x10, PV cut confirmed #firmware #sapphire-h-b001-v000-p023
- [Installation peter-sm](entities/installation-peter-sm.md) — SH10RT-V112 on P023 with an SBR160, two control tests; 13074 writes x10 #installation #peter-sm
- [Installation bar12](entities/installation-bar12.md) — SH10RT-20 with SBR096, cable and WiNet-S, P020 then P023 #installation #bar12
- [Installation firetribe](entities/installation-firetribe.md) — SH6.0RT-V112 on P023 with SBR096, cable and a busy WiNet-S #installation #firetribe
- [Installation fullhd23](entities/installation-fullhd23.md) — SH15T on P071 through a WiNet-S #installation #fullhd23
- [Installation fwitten](entities/installation-fwitten.md) — SH10RT-V112 master/slave cluster, read before and after the P023 upgrade #installation #fwitten
- [Installation gerd](entities/installation-gerd.md) — SH8.0RT-V112 on P022 with SBR096 and the only measured wallbox #installation #gerd
- [Installation jm493](entities/installation-jm493.md) — SH15T on P071 with SBH200 through a WiNet-S #installation #jm493
- [Installation mkaiser](entities/installation-mkaiser.md) — The maintainer's SH10RT on P020, control test matched every readback #installation #mkaiser
- [Installation ra1k-0](entities/installation-ra1k-0.md) — SH20T on P071 with SBH400, the first SH-T control test; iHomeManager and wallbox present, unread #installation #ra1k-0
- [Installation sisu70](entities/installation-sisu70.md) — SH10RT-20 on P023 with SBR128, cable and dongle, read while polling #installation #sisu70
- [Register 13000 \(running state\)](entities/register-13000.md) — Running state; 0x0000 is Running, and a dongle re-encodes it #register #input #running-state
- [Register 13074 \(export power limit\)](entities/register-13074.md) — Export power limit; writes x10 on B001 firmware, 1:1 on 01011.95.03 #register #holding #export-limit #write-scale
- [Register 31211 \(PV generation cut\)](entities/register-31211.md) — Undocumented PV generation cut, gated by firmware #register #holding #pv-cut #firmware-gated #undocumented
- [Register 6100 \(transport probe\)](entities/register-6100.md) — Answers on a cable, refused through a dongle: the transport question #register #input #transport

## Concepts

- [Contention](concepts/contention.md) — Few sessions, 90 s to recover; progressive failure means contention, a fixed address means a fault #modbus #sessions #polling
- [The control test's restore](concepts/control-test-restore.md) — Snapshot before the first write, raw-word restore, never skipped; exit 5 means a house is left changed #control-test #restore #safety
- [The control test](concepts/control-test.md) — Part B: three legs (plumbing, scale, behaviour) and the rules the procedure turns on #control-test #writes #scale #survey
- [A generator the inverter cannot see](concepts/external-generator.md) — A non-Sungrow inverter makes load_power low; external.py adds it back #load-power #external #options
- [A failed read is not a refusal](concepts/failed-read-is-not-refusal.md) — Exception responses are answers, link failures are not; probes are three-valued #modbus #probes #evidence
- [Firmware gating](concepts/firmware-gating.md) — Firmware is read first; ABSENT from refusals, CONFIRMED only from a watched write #firmware #capabilities #writes
- [Identify by what answers](concepts/identify-by-what-answers.md) — Sweep unit ids, never trust a port; the unit table by device and transport #discovery #unit-id #config-flow
- [Adopting the legacy entity ids](concepts/legacy-id-adoption.md) — Claim the YAML entity_id at creation so history continues; renames are refused onto known ids #migration #history #entity-id #recorder
- [The legacy slot of a second inverter](concepts/legacy-slot.md) — Which inverter was inv n is measured from the serial sensor; None is not the empty slot #migration #history #multi-inverter
- [Padded frames](concepts/padded-frames.md) — 2612 and 2628 send 15-register frames; layout.COUNTS and ISOLATE, measured with a strict client #modbus #layout #block-read
- [Protocol addresses and register numbers](concepts/protocol-addresses.md) — Addresses are one below register numbers; maps use reg(), no literal addresses #addresses #registers #convention
- [Serial anonymization](concepts/serial-anonymization.md) — Stand-ins in every published document, transcripts never tracked, the tree checked by shape #privacy #serial #survey
- [Transport detection](concepts/transport-detection.md) — 6100 decides cable versus dongle; what differs by transport #transport #winet-s #capabilities
- [Zero and empty mean absent](concepts/zero-means-absent.md) — A dongle's 0 and a NUL-filled string are not evidence of a capability #capabilities #winet-s #decoding

## Sources

- [ac22e01-gerd-anon-41346964423-wallbox-tls.json](sources/ac22e01-gerd-anon-41346964423-wallbox-tls-summary.md) — AC22E-01 wallbox, gerd, at its own address over TLS #survey #wallbox #ac22e-01 #gerd #tls
- [cross_reference_modbus_manager.md](sources/cross-reference-modbus-manager-summary.md) — TCzerny/ha-modbus-manager compared register by register; the MIT iHomeManager map #ihomemanager #cross-reference #licences
- [gerd-wallbox-isolarcloud-2026-10-30.md](sources/gerd-wallbox-isolarcloud-2026-10-30-summary.md) — gerd's AC22E-01 beside Sungrow's portal: 21201-21206 is the serial, 21300 and 21310 in Wh #wallbox #ac22e-01 #gerd #isolarcloud
- [github-issues-user-findings.md](sources/github-issues-user-findings-summary.md) — Issues #654-#775 read in full; a YAML package cannot decide anything #users #issues #yaml-package
- [legacy_entity_map.json](sources/legacy-entity-map-summary.md) — What the YAML package produces; the tests hold the integration to it #yaml-package #migration #entity-id
- [sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-lan.json](sources/sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-lan-summary.md) — SH10RT-20, B001.V000.P020, bar12, a WiNet-S on Ethernet #survey #sh10rt-20 #sapphire-h-b001-v000-p020 #bar12 #winet_lan
- [sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan.json](sources/sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan-summary.md) — SH10RT-20, B001.V000.P020, bar12, a WiNet-S on WiFi #survey #sh10rt-20 #sapphire-h-b001-v000-p020 #bar12 #winet_wlan #control-test
- [sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-meter-direct-lan.json](sources/sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-meter-direct-lan-summary.md) — SH10RT-20, B001.V000.P023, bar12, the inverter's own LAN port #survey #sh10rt-20 #sapphire-h-b001-v000-p023 #bar12 #direct_lan
- [sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan.json](sources/sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan-summary.md) — SH10RT-20, B001.V000.P023, bar12, a WiNet-S on WiFi #survey #sh10rt-20 #sapphire-h-b001-v000-p023 #bar12 #winet_wlan
- [sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-meter-direct-lan.json](sources/sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-meter-direct-lan-summary.md) — SH10RT-20, B001.V000.P023, sisu70, the inverter's own LAN port #survey #sh10rt-20 #sapphire-h-b001-v000-p023 #sisu70 #direct_lan
- [sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-winet-lan.json](sources/sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-winet-lan-summary.md) — SH10RT-20, B001.V000.P023, sisu70, a WiNet-S on Ethernet #survey #sh10rt-20 #sapphire-h-b001-v000-p023 #sisu70 #winet_lan
- [sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-winet-wlan.json](sources/sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-winet-wlan-summary.md) — SH10RT-20, B001.V000.P023, sisu70, a WiNet-S on WiFi #survey #sh10rt-20 #sapphire-h-b001-v000-p023 #sisu70 #winet_wlan
- [sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan.json](sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-summary.md) — SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port #survey #sh10rt #sapphire-h-b001-v000-p020 #mkaiser #direct_lan #control-test
- [sh10rt-v112-3p-fwitten-anon-33442450531-battery-none-direct-lan.json](sources/sh10rt-v112-3p-fwitten-anon-33442450531-battery-none-direct-lan-summary.md) — SH10RT-V112, pre-B001 firmware, fwitten slave, the inverter's own LAN port #survey #sh10rt-v112 #sapphire-h-01011-95-03 #fwitten #direct_lan #control-test
- [sh10rt-v112-3p-fwitten-anon-33442450531-battery-none-winet.json](sources/sh10rt-v112-3p-fwitten-anon-33442450531-battery-none-winet-summary.md) — SH10RT-V112, pre-B001 firmware, fwitten slave, a WiNet-S (medium not reported) #survey #sh10rt-v112 #sapphire-h-01011-95-03 #fwitten #winet #export-scale
- [sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan.json](sources/sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan-summary.md) — SH10RT-V112, pre-B001 firmware, fwitten master, the inverter's own LAN port #survey #sh10rt-v112 #sapphire-h-01011-95-03 #fwitten #direct_lan #control-test
- [sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-winet.json](sources/sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-winet-summary.md) — SH10RT-V112, pre-B001 firmware, fwitten master, a WiNet-S (medium not reported) #survey #sh10rt-v112 #sapphire-h-01011-95-03 #fwitten #winet #export-scale
- [sh10rt-v112-b001v000p023-3p-anonymous-anon-91477823483-battery-sbr160-meter-direct-lan.json](sources/sh10rt-v112-b001v000p023-3p-anonymous-anon-91477823483-battery-sbr160-meter-direct-lan-summary.md) — SH10RT-V112, B001.V000.P023, anonymous, the inverter's own LAN port #survey #sh10rt-v112 #sapphire-h-b001-v000-p023 #anonymous #direct_lan #control-test
- [sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan.json](sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-summary.md) — SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port; 13074 times ten, battery capped at 10 W #survey #sh10rt-v112 #sapphire-h-b001-v000-p023 #peter-sm #direct_lan #control-test
- [sh10rt-v112-b001v000p023-3p-fwitten-anon-33442450531-battery-none-direct-lan.json](sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-33442450531-battery-none-direct-lan-summary.md) — SH10RT-V112, B001.V000.P023, fwitten slave, the inverter's own LAN port #survey #sh10rt-v112 #sapphire-h-b001-v000-p023 #fwitten #direct_lan #control-test
- [sh10rt-v112-b001v000p023-3p-fwitten-anon-33442450531-battery-none-winet.json](sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-33442450531-battery-none-winet-summary.md) — SH10RT-V112, B001.V000.P023, fwitten slave, a WiNet-S (medium not reported) #survey #sh10rt-v112 #sapphire-h-b001-v000-p023 #fwitten #winet #export-scale
- [sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan.json](sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan-summary.md) — SH10RT-V112, B001.V000.P023, fwitten master, the inverter's own LAN port #survey #sh10rt-v112 #sapphire-h-b001-v000-p023 #fwitten #direct_lan #control-test
- [sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-winet.json](sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-winet-summary.md) — SH10RT-V112, B001.V000.P023, fwitten master, a WiNet-S (medium not reported) #survey #sh10rt-v112 #sapphire-h-b001-v000-p023 #fwitten #winet #export-scale
- [sh15t-b000v000p071-3p-fullhd23-anon-08484305020-battery-unknown-winet-lan.json](sources/sh15t-b000v000p071-3p-fullhd23-anon-08484305020-battery-unknown-winet-lan-summary.md) — SH15T, B000.V000.P071, FullHD23, a WiNet-S on Ethernet #survey #sh15t #pearl-h-b000-v000-p071 #fullhd23 #winet_lan
- [sh15t-b000v000p071-3p-jm493-anon-00578206904-battery-sbh200-winet-lan.json](sources/sh15t-b000v000p071-3p-jm493-anon-00578206904-battery-sbh200-winet-lan-summary.md) — SH15T, B000.V000.P071, jm493, a WiNet-S on Ethernet #survey #sh15t #pearl-h-b000-v000-p071 #jm493 #winet_lan
- [sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan.json](sources/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-summary.md) — SH20T, B000.V000.P071, ra1k_0, a WiNet-S on WiFi #survey #sh20t #pearl-h-b000-v000-p071 #ra1k-0 #winet_wlan
- [sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-004-005.json](sources/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-004-005-summary.md) — SH20T, B000.V000.P071, ra1k_0, a WiNet-S on WiFi, the first SH-T control test #survey #sh20t #pearl-h-b000-v000-p071 #ra1k-0 #winet_wlan #control-test
- [sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-meter-direct-lan.json](sources/sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-meter-direct-lan-summary.md) — SH6.0RT-V112, B001.V000.P023, firetribe, the inverter's own LAN port #survey #sh6.0rt-v112 #sapphire-h-b001-v000-p023 #firetribe #direct_lan #control-test
- [sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-winet-lan.json](sources/sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-winet-lan-summary.md) — SH6.0RT-V112, B001.V000.P023, firetribe, a WiNet-S on Ethernet #survey #sh6.0rt-v112 #sapphire-h-b001-v000-p023 #firetribe #winet_lan #control-test
- [sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan.json](sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-summary.md) — SH8.0RT-V112, B001.V000.P022, gerd, the inverter's own LAN port #survey #sh8-0rt-v112 #sapphire-h-b001-v000-p022 #gerd #direct_lan #control-test #export-scale
- [sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan.json](sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-summary.md) — SH8.0RT-V112, B001.V000.P022, gerd, a WiNet-S on WiFi #survey #sh8-0rt-v112 #sapphire-h-b001-v000-p022 #gerd #winet_wlan #export-scale #wallbox
- [wallbox_registers.md](sources/wallbox-registers-summary.md) — The AC wallbox map, with how strongly each row is held #wallbox #registers #ac22e-01

## Queries

- [Does a wallbox answer unit 248 on RS485?](queries/does-a-wallbox-answer-unit-248-on-rs485.md) — Open: reported by others, never measured #wallbox #rs485 #open
- [Does a busy WiNet-S refuse with 0x04?](queries/does-a-busy-winet-s-refuse-with-0x04.md) — Answered: yes, reproduced at gerd with three clients #winet-s #contention #answered
- [Does the PV cut work on P022 and P071?](queries/does-the-pv-cut-work-on-p022-and-p071.md) — P022 confirmed at gerd; P071 open, no watched write #pv-cut #register-31211 #open
- [What does an iHomeManager answer?](queries/what-does-an-ihomemanager-answer.md) — Open: never surveyed #ihomemanager #open #survey-wanted
- [What does a Sungrow Logger answer?](queries/what-does-a-logger-answer.md) — Open: never surveyed #logger #open #survey-wanted
