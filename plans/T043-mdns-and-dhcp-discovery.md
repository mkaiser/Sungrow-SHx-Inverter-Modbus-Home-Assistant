# T043 - DHCP discovery: what is still open

**mDNS is done** (maintainer, 2026-11-23): three houses' dongles and a wallbox were heard over it
(wiki: the mDNS query), and the matcher ships. What is open is **DHCP**: the matcher (0.1.0a41,
`wifi_module.py`) offers a port for Sungrow's one IEEE prefix `AC199F*`, and no house has yet been seen found by
it. A house qualifies whose inverter port takes its address by DHCP; a fixed address is never seen.

**A diagnosis says it from schema 29**: `network_names.home_assistant` carries `set_up_by` (the discovery an entry was set
up from) and `dhcp_knows_address`. `dhcp` in the first settles it; the second says only that Home Assistant could have
offered the device, because a router's tracker and a network scan fill the same table. The section used to
be lost from an inverter's *Download diagnostics*, which rebuilt the document without it, and was never taken for an SG;
both carry it now. Entries already set up by hand can show `dhcp_knows_address` only.

Deferred, nothing waits on them: a WiNet-S's *Visit* link for a cable entry, found by the inverter serial in its TXT.
