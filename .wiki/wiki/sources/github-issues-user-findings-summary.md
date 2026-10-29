---
type: source
title: github-issues-user-findings.md
source_path: raw/github-issues-user-findings.md
ingested: '2026-10-29'
created: '2026-10-29'
tags: [users, issues, yaml-package]
---

# What users reported: issues #654 to #775

`.wiki/raw/github-issues-user-findings.md` covers the last 50 GitHub issues,
read in full with every comment, and checks each against the integration.
Issues are cited by number, and nobody is named. Two threads quote real
serials, and those are left out.

**The short version:** almost every issue has the same root cause. **A YAML
package cannot decide anything.** It polls every register for every user, so
a register that one model, firmware or transport lacks floods the log. It
writes [13074](../entities/register-13074.md) with one fixed scale, so it was
wrong for someone whichever way the scale was set. And it cannot sequence or
protect a write.

The integration answers these with [firmware gating](../concepts/firmware-gating.md)
and [transport detection](../concepts/transport-detection.md), the per-device
13074 probe, and serialized writes ([contention](../concepts/contention.md)).
The per-issue status (covered, partly, open) is in the raw file.
