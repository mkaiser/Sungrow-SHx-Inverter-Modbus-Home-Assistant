#!/usr/bin/env python3
"""A one-off hardware watch that puts the house back, whatever happens.

For the scripts that drive a real inverter through Home Assistant for an hour
to answer one question -- `plans/`'s hardware runs, not the shipped capability
test, which restores over its own Modbus connection and holds no credential
that can expire. Import it:

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from ha_watch import dev_instance, run, watching

    def body(watch):
        watch.wait_for_quiet("sensor.hwr_sh10rt_diagnosis_test_summary")
        watch.press(                          # so no capability test writes
            "select.hwr_sh10rt_diagnosis_mode", "select_option",
            option="read_only",               # over the register under test
        )
        watch.press("switch.hwr_sh10rt_forced_startup", "turn_on")
        ...                                   # the measurement
    sys.exit(run(dev_instance(), Path("13017-watch.json"), "13017 watch", body))

and the restore happens on the way out of `watching`, by whichever path --
the measurement finishing, an exception, a Ctrl-C -- newest press first, so
the mode goes back to auto repeat after the register it was switched off for.

**Why this exists.** A watcher that wrote to the maintainer's house and
restored in a `finally` block left register 13017 on for 50 minutes past its
window on 2026-11-17: it held an access token from the start, the token
expired 29 minutes in, and all five restore attempts returned HTTP 401. The
measurement survived; the house did not go back, and only a person noticing
put it right (wiki: 13017 left on for 90 minutes). So, in this order:

1. **The credential is minted when it is used, never held from the start**,
   and the restore forces a fresh one before its first write. A token that
   cannot be minted is an error before anything is pressed.
2. **The note is on disk before the first write.** It names every entity
   pressed and the state it held, so `--restore <note>` puts the house back
   from another process after this one has died. No note, no writes.
3. **The restore runs by the capability test's rule**, which owns it (wiki:
   the capability test's restore): every way out goes through it, it reads
   back what it wrote, and it ends when the house is back rather than when a
   budget runs out.
4. **A house left changed is said loudly**, on stderr, with the command that
   finishes the job, and the process exits 5 -- the one code that means a
   house is left changed.
5. **It looks before it presses.** A script pressed *Diagnosis: stop* 21
   seconds into a run auto repeat had started, interrupted it, and then could
   not re-arm what it had switched off. `wait_for_quiet` reads `running_since`
   on *Diagnosis: test summary* and waits for a run in flight rather than
   pressing through it.

Only the dev instance is written to by password: `dev` / `dev` is an open door
on any instance somebody else can reach, so `dev_instance` refuses a
non-loopback URL for the same reason `ha_onboard.py` does. A production
instance is read-only (`doc/development.yaml`, `production_home_assistant_api`),
and a long-lived token is accepted here only so that reading one is possible,
never to press something at a house over the network.

    ha_watch.py --url http://127.0.0.1:8125 --quiet sensor.…_test_summary
    ha_watch.py --url http://127.0.0.1:8125 --restore 13017-watch.json
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

#: The one code that means a house is left changed, as the capability test's.
EXIT_LEFT_CHANGED = 5

#: How old a token may be before the next call mints another. Home Assistant's
#: login flow hands out tokens that live 30 minutes; ten keeps every call well
#: inside that without asking the server how long it has left.
MAX_TOKEN_AGE = 600

#: What the restore waits between attempts, then the last figure for ever.
#: Never a deadline -- the sequence runs out of patience, not out of tries.
BACKOFF = (5, 5, 10, 20, 30, 60)

LOOPBACK = {"127.0.0.1", "localhost", "::1", "[::1]"}

#: How a state read back from an entity is written again, by platform. A
#: platform that is not here cannot be pressed: there is no way to put it
#: back, and pressing what cannot be restored is the thing this module exists
#: to prevent.
RESTORES: dict[str, Callable[[str], tuple[str, dict[str, Any]]]] = {
    "switch": lambda state: (f"turn_{'on' if state == 'on' else 'off'}", {}),
    "number": lambda state: ("set_value", {"value": float(state)}),
    "select": lambda state: ("select_option", {"option": state}),
    "time": lambda state: ("set_value", {"time": state}),
}

#: States that say the entity's own value is not known. A press needs to know
#: where the house was, so these are refused rather than restored to the word
#: "unknown" (wiki: a failed read is not a refusal).
NOT_A_VALUE = frozenset({"unknown", "unavailable", ""})


def _login_flow() -> Any:
    """Return `ha_onboard`'s client class, which owns the login flow.

    Loaded by path rather than imported, so this module works whether it is
    run as a script or imported from one in another directory. Borrowed
    rather than copied because three endpoints in two files drift: that file
    states what the flow is and why `dev` / `dev` is written down.
    """
    path = Path(__file__).resolve().parent / "ha_onboard.py"
    spec = importlib.util.spec_from_file_location("ha_onboard", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Instance


class HouseLeftChanged(RuntimeError):
    """The restore did not get everything back, and somebody has to act."""

    def __init__(self, note: Path, outstanding: list[str]) -> None:
        """Say what is still changed and how to finish putting it back."""
        self.note = note
        self.outstanding = outstanding
        super().__init__(
            f"THE HOUSE IS LEFT CHANGED: {', '.join(outstanding)} did not go "
            f"back. The note is {note}; finish it with "
            f"`ha_watch.py --url <url> --restore {note}`."
        )


class Instance:
    """One Home Assistant over HTTP, with a token minted when it is used.

    Nothing here keeps a credential for later. `bearer` mints one on the
    first call that needs it and again once it is `MAX_TOKEN_AGE` old, and a
    401 mints another and retries once -- so a call forty minutes into a
    watch carries a token minted forty minutes in, not one minted at the
    start. `fresh()` forces that, which is what the restore does before its
    first write.
    """

    def __init__(
        self,
        url: str,
        *,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
    ) -> None:
        """Point at one instance, by password login or by a long-lived token."""
        if token is None and (username is None or password is None):
            raise ValueError("an instance needs either a token or a login")
        self.url = url.rstrip("/")
        self._username = username
        self._password = password
        self._long_lived = token
        self._token: str | None = None
        self._minted = 0.0

    def fresh(self) -> None:
        """Drop the token held, so the next call mints one."""
        self._token = None

    def bearer(self) -> str:
        """Return a token no older than `MAX_TOKEN_AGE`, minting if need be."""
        if self._long_lived is not None:
            return self._long_lived
        if self._token is None or time.monotonic() - self._minted > MAX_TOKEN_AGE:
            assert self._username is not None and self._password is not None
            client = _login_flow()(self.url)
            client.log_in(self._username, self._password)
            if not client.token:
                raise RuntimeError(f"no access token from {self.url}")
            self._token = str(client.token)
            self._minted = time.monotonic()
        return self._token

    def _call(
        self, path: str, payload: dict[str, Any] | None = None, *, retry: bool = True
    ) -> Any:
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(
            self.url + path,
            data=data,
            headers={
                "Authorization": f"Bearer {self.bearer()}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as answer:
                raw = answer.read().decode()
        except urllib.error.HTTPError as error:
            if error.code == 401 and retry:
                # The one failure this module exists for: the token has gone
                # stale. Mint another and go again, once, so a stale token is
                # never the reason a register stays written.
                self.fresh()
                return self._call(path, payload, retry=False)
            raise
        return json.loads(raw) if raw.strip() else None

    def state(self, entity_id: str) -> dict[str, Any]:
        """Return one entity's state document: `state` and `attributes`."""
        answer = self._call(f"/api/states/{urllib.parse.quote(entity_id)}")
        if not isinstance(answer, dict):
            raise RuntimeError(f"unexpected state for {entity_id}: {answer!r}")
        return answer

    def call(self, domain: str, service: str, entity_id: str, **data: Any) -> None:
        """Call one entity service, the way a dashboard would."""
        self._call(
            f"/api/services/{domain}/{service}", {"entity_id": entity_id, **data}
        )


def dev_instance(url: str = "http://127.0.0.1:8125") -> Instance:
    """Return the development instance, logged in as `dev` / `dev`.

    Loopback only. Those credentials are deliberately public, which is
    exactly why they must never reach a machine somebody else can reach
    (`ha_onboard.py` says it at length).
    """
    host = urllib.parse.urlsplit(url).hostname or ""
    if host not in LOOPBACK:
        raise ValueError(f"{url} is not loopback: dev/dev is an open door there")
    return Instance(url, username="dev", password="dev")


class Watch:
    """What one watch pressed, and what putting it back needs.

    Built by `watching`, which is what runs the restore. Nothing here is a
    `finally` block of the caller's own: that is the mistake this replaces.
    """

    def __init__(self, instance: Instance, note: Path, what: str) -> None:
        """Prepare a watch. The note is written on the first press."""
        self.instance = instance
        self.note = note
        self.what = what
        self.pressed: list[dict[str, str]] = []

    # -- looking before pressing ---------------------------------------------

    def run_in_flight(self, summary_entity: str) -> str | None:
        """Return when a diagnosis run started, or None if none is running.

        `running_since` on *Diagnosis: test summary*, which is set exactly
        while an extended run is in flight -- auto repeat's own runs included,
        which is the case worth catching.
        """
        since = self.instance.state(summary_entity)["attributes"].get("running_since")
        return None if since is None else str(since)

    def wait_for_quiet(self, summary_entity: str, *, poll: int = 30) -> None:
        """Wait while a diagnosis run is in flight. No deadline, on purpose.

        A run is minutes to hours of somebody's inverter answering questions,
        and interrupting it loses the run and leaves its restore to a stop
        this script does not control. Waiting costs this script its hour;
        pressing through costs the house's.
        """
        while (since := self.run_in_flight(summary_entity)) is not None:
            print(
                f"a diagnosis run has been in flight since {since}: waiting "
                f"{poll}s rather than pressing through it",
                flush=True,
            )
            time.sleep(poll)

    # -- pressing ------------------------------------------------------------

    def press(self, entity_id: str, service: str, **data: Any) -> None:
        """Note where the entity is, flush the note, then call the service.

        Refuses before writing anything where the entity's platform cannot be
        written back, or where its state is not a value: a press whose
        restore cannot be worked out is a house nobody can put back.
        """
        domain = entity_id.split(".", 1)[0]
        if domain not in RESTORES:
            raise ValueError(
                f"{entity_id}: a {domain} cannot be put back by this module, "
                f"so it is not pressed (it knows {', '.join(sorted(RESTORES))})"
            )
        before = self.instance.state(entity_id)["state"]
        if before in NOT_A_VALUE:
            raise ValueError(
                f"{entity_id} reads {before!r}: where it should go back to is "
                "not known, so it is not pressed"
            )
        self.pressed.append({"entity_id": entity_id, "state": before})
        self._flush()
        self.instance.call(domain, service, entity_id, **data)
        after = self.instance.state(entity_id)["state"]
        print(f"pressed {entity_id}: {before} -> {after}", flush=True)

    def _flush(self) -> None:
        """Write the note. Called before every write, never after."""
        self.note.write_text(
            json.dumps(
                {
                    "url": self.instance.url,
                    "what": self.what,
                    "written_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "pressed": self.pressed,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    # -- putting it back -----------------------------------------------------

    def restore(self) -> list[str]:
        """Put everything back, newest press first. Returns what would not go.

        A fresh token before the first write, because a restore is the one
        call that must not fail on a credential. Then each entity is written
        and **read back**, and a mismatch is tried again for as long as it
        takes: `BACKOFF`'s last figure repeats, so this ends when the house is
        back or when a person stops it.
        """
        self.instance.fresh()
        outstanding: list[str] = []
        left = list(reversed(self.pressed))
        while left:
            entry = left[0]
            try:
                done = self._restore_one(entry["entity_id"], entry["state"])
            except KeyboardInterrupt:
                # A person stopping the restore is the only thing that ends
                # it, and then everything still pressed is outstanding: going
                # on to the next entity would make them press Ctrl-C once per
                # register to get their shell back.
                print("\nrestore interrupted", file=sys.stderr, flush=True)
                return outstanding + [item["entity_id"] for item in left]
            left.pop(0)
            if not done:
                outstanding.append(entry["entity_id"])
        if not outstanding:
            self.note.unlink(missing_ok=True)
        return outstanding

    def _restore_one(self, entity_id: str, state: str) -> bool:
        """Write one entity back until it reads back. `KeyboardInterrupt` out."""
        domain = entity_id.split(".", 1)[0]
        service, data = RESTORES[domain](state)
        for attempt, wait in enumerate(_waits(), start=1):
            try:
                self.instance.call(domain, service, entity_id, **data)
                now = self.instance.state(entity_id)["state"]
                if _same(now, state):
                    print(f"restored {entity_id} to {state}", flush=True)
                    return True
                reason = f"reads {now}, wanted {state}"
            except Exception as error:  # noqa: BLE001 - the traceback goes out below
                reason = f"{type(error).__name__}: {error}"
                if attempt == 1:
                    # Once, on the first failure: it is the only record of why
                    # somebody's inverter is still carrying this watch's
                    # value, and the attempts after it are the same line over
                    # and over (wiki: the capability test's restore).
                    traceback.print_exc()
            print(
                f"restore of {entity_id} attempt {attempt} did not take "
                f"({reason}); again in {wait}s",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(wait)
        return False  # pragma: no cover - `_waits` does not run out


def _waits() -> Iterator[int]:
    """Yield `BACKOFF`, then its last figure for ever."""
    yield from BACKOFF
    while True:
        yield BACKOFF[-1]


def _same(now: str, wanted: str) -> bool:
    """Whether a state read back is the one wanted, numbers by value."""
    if now == wanted:
        return True
    try:
        return float(now) == float(wanted)
    except (TypeError, ValueError):
        return False


@contextmanager
def watching(instance: Instance, note: Path, what: str) -> Iterator[Watch]:
    """Run a watch, and put the house back on the way out of it, every way out.

    Raises `HouseLeftChanged`, after saying so on stderr, where the restore
    could not finish. An exception from the body is raised after the restore
    has run, not instead of it.
    """
    watch = Watch(instance, note, what)
    # Before anything is pressed: a credential that cannot be minted now is a
    # watch that could not restore later, and finding that out here costs
    # nothing.
    instance.fresh()
    instance.bearer()
    try:
        yield watch
    finally:
        outstanding = watch.restore()
        if outstanding:
            left = HouseLeftChanged(note, outstanding)
            print(f"\n{'=' * 72}\n{left}\n{'=' * 72}", file=sys.stderr, flush=True)
            raise left


def run(
    instance: Instance, note: Path, what: str, body: Callable[[Watch], None]
) -> int:
    """Run `body` under `watching`, and return the process's exit code.

    0 where the house is back, `EXIT_LEFT_CHANGED` where it is not -- so a
    caller is `sys.exit(run(...))` and cannot get the code wrong.
    """
    try:
        with watching(instance, note, what) as watch:
            body(watch)
    except HouseLeftChanged:
        return EXIT_LEFT_CHANGED
    return 0


def restore_note(instance: Instance, note: Path) -> int:
    """Put a dead watch's note back: the way out when the watcher is gone.

    The same restore, from another process, as `--restore <snapshot>` is for
    the capability test.
    """
    document = json.loads(note.read_text(encoding="utf-8"))
    watch = Watch(instance, note, str(document.get("what", note.name)))
    watch.pressed = list(document.get("pressed", []))
    if not watch.pressed:
        print(f"{note} has nothing pressed; nothing to put back")
        return 0
    outstanding = watch.restore()
    if outstanding:
        left = HouseLeftChanged(note, outstanding)
        print(f"\n{'=' * 72}\n{left}\n{'=' * 72}", file=sys.stderr, flush=True)
        return EXIT_LEFT_CHANGED
    return 0


def main(argv: list[str] | None = None) -> int:
    """Read whether a run is in flight, or finish a note's restore."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://127.0.0.1:8125")
    parser.add_argument(
        "--quiet",
        metavar="SUMMARY_ENTITY",
        help="say whether a diagnosis run is in flight, and exit",
    )
    parser.add_argument(
        "--restore", metavar="NOTE", type=Path, help="put a watch's note back"
    )
    args = parser.parse_args(argv)
    if not args.quiet and not args.restore:
        parser.error("one of --quiet or --restore is needed")
    instance = dev_instance(args.url)
    if args.quiet:
        since = Watch(instance, Path("unused"), "read").run_in_flight(args.quiet)
        print("quiet" if since is None else f"a run has been in flight since {since}")
    return restore_note(instance, args.restore) if args.restore else 0


if __name__ == "__main__":
    raise SystemExit(main())
