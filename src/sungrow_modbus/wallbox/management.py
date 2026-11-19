"""Whether a wallbox is under an inverter's management, inferred from 21203.

Nothing the wallbox reports says who drives it. Input 21314 reads 1 idle and
3 charging on every wallbox read, and an inverter's EV charger block reads its
factory state -- PV surplus at 16.0 A -- on houses with no wallbox at all
(wiki: device-wallbox). So the only evidence is behaviour, and there is one
piece of it: **an inverter under whose management a wallbox charges rewrites
the wallbox's output current (holding 21203) every few seconds.** Measured at
gerd's over the cable and through the WiNet-S alike: in user-defined mode
21203 settles at the inverter's user current, in fast charge it is the
inverter's own offer of 24-28 A, and either way it follows what the inverter
decides rather than staying where it was.

Nothing here writes, and nothing here reads anything of its own: it is fed the
polls the readings checks are already fed. What it answers decides what is
*shown* and what the diagnosis says it is waiting for. **It never decides what
is written** -- that is the owner's word in the entry's options
(`wallbox_capability_test.declared_standalone`), because a wrong *standalone*
writes registers an inverter overwrites within seconds, and a setting that
happens to sit still is not proof that nobody is driving it.

Asymmetric on purpose, in both directions:

* **managed** needs the setting to move while a car charges and while this
  integration writes nothing. Two moves, because one can be the owner
  changing the current in Sungrow's app.
* **standalone** needs a whole charging session's worth of polls with the
  setting never moving -- and it is still only an inference, offered to a
  person to confirm.
* a wallbox with no car on it says nothing either way, however long it is
  watched, and this reports that rather than a guess.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

#: An inverter drives this wallbox: 21203 moved with nothing here writing it.
MANAGED = "managed"

#: Nothing appears to drive it: 21203 held still through a charge. An
#: inference, never a licence to write (the module docstring says why).
STANDALONE = "standalone"

#: Not enough seen. The honest answer for a wallbox no car has plugged into.
UNKNOWN = "unknown"

#: How many moves of 21203 during a charge mean an inverter is driving it. Two,
#: because one move can be the owner changing the current in Sungrow's app.
MOVES_FOR_MANAGED = 2

#: How many charging polls with the setting untouched suggest nobody is. 30 on
#: the ten-second tier is five minutes of charging, which is many times the
#: few seconds an inverter takes to write it again.
STEADY_POLLS_FOR_STANDALONE = 30

#: A difference in the setting smaller than this is not a move: 21203 is a
#: 0.1 A register, so a count is the smallest change it can express.
MOVE_A = 0.1


@dataclass
class Management:
    """What drives this wallbox, from how 21203 behaves while a car charges.

    Kept in memory only. It is cheap to establish again -- a few minutes of
    the next charging session -- and the answer that matters across restarts
    is the owner's, which is an option on the entry.
    """

    #: Polls seen with a car charging.
    charging_polls: int = 0
    #: Times the setting moved between two such polls.
    moves: int = 0
    #: The setting at the last charging poll.
    last: float | None = None

    def observe(self, setting: float | None, *, charging: bool) -> None:
        """Take one poll: the output current setting, and whether a car charges.

        A poll without a charge is dropped rather than counted as steady: an
        inverter has nothing to write then, so stillness means nothing. The
        same goes for the first poll of a session, which has nothing to be
        compared with.
        """
        if not charging or setting is None:
            # An idle wallbox, or a setting that did not read. Either way the
            # next poll has nothing to compare with: a move on the other side
            # of the gap was not seen, and counting one would be inventing it.
            self.last = None
            return
        self.charging_polls += 1
        if self.last is not None and abs(setting - self.last) >= MOVE_A:
            self.moves += 1
        self.last = setting

    def verdict(self) -> tuple[str, str]:
        """Return (what drives it, the reading that says so)."""
        if self.moves >= MOVES_FOR_MANAGED:
            return (
                MANAGED,
                f"the output current setting moved {self.moves} times during a "
                "charge, which nothing here wrote",
            )
        if self.charging_polls >= STEADY_POLLS_FOR_STANDALONE and not self.moves:
            return (
                STANDALONE,
                f"the output current setting held still for {self.charging_polls} "
                "polls of a charge; no inverter appears to drive it",
            )
        if self.charging_polls:
            return (
                UNKNOWN,
                f"{self.charging_polls} of {STEADY_POLLS_FOR_STANDALONE} polls of "
                f"a charge, {self.moves} with the setting moved",
            )
        return UNKNOWN, "no charge seen yet: nothing an inverter would be writing"

    def as_dict(self) -> dict[str, Any]:
        """Return the inference and its counts, for a document or an attribute."""
        state, detail = self.verdict()
        return {
            "management": state,
            "management_detail": detail,
            "charging_polls": self.charging_polls,
            "setting_moves": self.moves,
        }

    def load(self, state: Mapping[str, Any]) -> None:
        """Take counts back, for a caller that did keep them."""
        self.charging_polls = int(state.get("charging_polls") or 0)
        self.moves = int(state.get("setting_moves") or 0)
