---
type: concept
title: A remote site's link drops, and the tunnel does not recover
tags: [remote, vpn, polling, evidence]
created: '2026-11-14'
---

# A remote site's link drops, and the tunnel does not recover

A watch over a WireGuard tunnel to a remote owner's site goes silent when the site's internet
line is cut, and **the tunnel does not come back by itself when the line does**. It has to be
taken down and brought up again.

- **At [gerd](../entities/installation-gerd.md) the provider cut the line overnight** (about
  02:52, found at about 07:00). Every read of the wallbox and the inverter timed out for hours,
  and a TCP connect to the wallbox's port failed, while the tunnel interface and its route
  stayed up on our side (`.wiki/raw/gerd-site-link-loss-2026-11-14.md`).
- **Restarting the tunnel fixed it at once**: a fresh handshake within seconds, then normal
  reads of both devices (`.wiki/raw/gerd-site-link-loss-2026-11-14.md`).
- **An interface that is up says nothing about the link.** Check the handshake age and a TCP
  connect to a device port before blaming a device.
- **Timeouts that clear on the next read are not an outage.** Isolated ones came earlier the
  same night (01:12 and 01:15), each followed by a normal read
  (`.wiki/raw/gerd-site-link-loss-2026-11-14.md`).
- **A drop of the site's link is not a device fault.** Both devices stopped at the same moment,
  and both were unchanged after it. Read as a failed read, not a refusal
  ([failed read](failed-read-is-not-refusal.md), [contention](contention.md) for the other
  cause of silence).
- **For a watch left running unattended**, re-test the link and restart the tunnel when every
  read fails, never while another client talks to the site.

Not established: whether a keepalive on the site's side would have let the tunnel recover.
