# T041 - A first Sungrow Logger diagnosis

**A first Sungrow Logger diagnosis** (#786). Unblocks Logger entities.
The map is done from Sungrow's protocol 1.0.2.9
(`sungrow_modbus.logger`, every field `spec`; where every document is:
`.wiki/wiki/queries/where-are-sungrows-documents.md`); what a first
diagnosis settles is on `.wiki/wiki/queries/what-does-a-logger-answer.md`.
It reached diagnoses with 0.1.0a26, which the diagnosis pins. Missing:

1. **Its TLS port, untried.** The diagnosis asks unit 247 over TLS on 516
   (a current Logger1000 opens only that port); no Logger has answered
   there yet, so that path is held to fakes only (`tests/test_logger.py`).
2. **What sits behind it.** Each inverter and meter answers at its
   forwarding address (the Logger's Device List page), not at a unit the
   diagnosis guesses; `identify` looks at units 1-5 only. A DTSU666 is a
   device nothing maps.
3. **A contributor with one.** Nobody has offered; the #262 participants
   are the leads: horstvogel (2025-12-23, a Logger1000 EU read over
   Modbus TCP at unit 247), RafAustralia, purcell-lab and NBS23.
4. **The protocol number's word order.** The map reads 8001-8002 high
   word first; the one iHomeManager measured sends "AW0" low word first
   (fixed for it, 2026-11-10). Check the Logger's on its first reading.
