#!/usr/bin/env python3
"""Walk a fresh Home Assistant through onboarding, so nobody types it again.

A new instance opens on `onboarding.html` and asks for an account before it
will show anything. That is correct for a real installation and pure friction
for a dev one: the account is local to a gitignored directory, it guards
fabricated data, and it is the same `dev` / `dev` this project has always
used -- written down in `doc/development.yaml` on purpose so anybody can pick
the instance up.

So this does it over the API instead, in the order the frontend does:

1. `POST /api/onboarding/users` creates the account and returns an auth code;
2. `POST /auth/token` exchanges that code for an access token;
3. `POST /api/onboarding/core_config`, `/analytics` and `/integration`
   complete the remaining steps, which need that token -- without them the
   browser still opens on a wizard.

    python scripts/ha_onboard.py --url http://127.0.0.1:8124
    python scripts/ha_onboard.py --url http://127.0.0.1:8123 --wait 300

**Idempotent, and that is the point**: it asks what is already done and does
only the rest, so a boot script can call it every time. An instance that is
fully onboarded makes it print one line and exit 0.

It waits for the instance to answer, because the caller usually starts Home
Assistant and this in the same breath, and a first boot spends minutes
installing component requirements before it serves anything.

**It refuses a non-loopback URL.** These credentials are deliberately public,
which is exactly why they must never reach a machine somebody else can
reach: `dev` / `dev` on a real instance is an open door. Point it at
127.0.0.1 or localhost, or pass `--username`/`--password` of your own.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

LOOPBACK = {"127.0.0.1", "localhost", "::1", "[::1]"}

#: The steps Home Assistant reports, in the order they must be done. `user`
#: is first because everything after it needs the token it returns.
ORDER = ("user", "core_config", "analytics", "integration")


def remaining(status: list[dict[str, object]]) -> list[str]:
    """Name the onboarding steps still outstanding, in the order to do them.

    Takes the payload of `GET /api/onboarding` -- a list of
    `{"step": ..., "done": ...}` -- and ignores any step this script does not
    know how to drive, rather than guessing at a future one.
    """
    outstanding = {
        str(entry["step"]) for entry in status if not entry.get("done", False)
    }
    return [step for step in ORDER if step in outstanding]


class Instance:
    """The few Home Assistant endpoints onboarding needs."""

    def __init__(self, url: str) -> None:
        """Point at one instance. Nothing is contacted until a call is made."""
        self.url = url.rstrip("/")
        self.client_id = self.url + "/"
        self.redirect = self.client_id + "?auth_callback=1"
        self.token: str | None = None

    def _call(
        self,
        path: str,
        payload: dict[str, object] | None = None,
        *,
        form: bool = False,
        authenticated: bool = False,
    ) -> object:
        headers: dict[str, str] = {}
        data = None
        if payload is not None:
            if form:
                data = urllib.parse.urlencode(payload).encode()
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            else:
                data = json.dumps(payload).encode()
                headers["Content-Type"] = "application/json"
        if authenticated:
            if self.token is None:
                raise RuntimeError(f"{path} needs a token and none was obtained")
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(self.url + path, data=data, headers=headers)
        with urllib.request.urlopen(request, timeout=30) as answer:
            raw = answer.read().decode()
        return json.loads(raw) if raw.strip() else None

    def status(self) -> list[dict[str, object]]:
        """Ask which steps are outstanding. An empty list means none are.

        A 404 counts as "none": Home Assistant answers this endpoint while
        onboarding is pending and some versions stop serving it once it is
        finished. Treating that as "not up yet" is the difference between
        one line and a ten-minute wait, and it is a *server* answering
        either way -- which is why this catches `HTTPError` here rather than
        letting the caller's connection-retry loop see it.
        """
        try:
            answer = self._call("/api/onboarding")
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return []
            raise
        if not isinstance(answer, list):
            raise RuntimeError(f"unexpected onboarding payload: {answer!r}")
        return answer

    def wait_until_answering(self, seconds: int) -> list[dict[str, object]]:
        """Poll until the instance serves its onboarding status, or give up."""
        deadline = time.monotonic() + seconds
        announced = False
        while True:
            try:
                return self.status()
            except urllib.error.HTTPError:
                # The instance answered, with something this script did not
                # expect. Waiting cannot fix that, so let it out.
                raise
            except (urllib.error.URLError, OSError, RuntimeError) as error:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"{self.url} did not answer within {seconds}s ({error})"
                    ) from error
                if not announced:
                    # A first boot installs every component's requirements
                    # before it serves anything, so this is normal and worth
                    # saying once rather than every two seconds.
                    print(
                        f"waiting for {self.url} to come up (up to {seconds}s)",
                        flush=True,
                    )
                    announced = True
                time.sleep(2)

    def create_user(self, name: str, username: str, password: str) -> None:
        """Create the first account, and keep the token it hands back."""
        answer = self._call(
            "/api/onboarding/users",
            {
                "client_id": self.client_id,
                "name": name,
                "username": username,
                "password": password,
                "language": "en",
            },
        )
        if not isinstance(answer, dict) or "auth_code" not in answer:
            raise RuntimeError(f"no auth code in {answer!r}")
        self._exchange(str(answer["auth_code"]))

    def log_in(self, username: str, password: str) -> None:
        """Get a token for an account that already exists.

        Needed when the user step is done but a later one is not -- an
        instance somebody half-onboarded by hand, which is otherwise the one
        case this script could not finish.
        """
        flow = self._call(
            "/auth/login_flow",
            {
                "client_id": self.client_id,
                "handler": ["homeassistant", None],
                "redirect_uri": self.redirect,
            },
        )
        if not isinstance(flow, dict) or "flow_id" not in flow:
            raise RuntimeError(f"no login flow in {flow!r}")
        result = self._call(
            f"/auth/login_flow/{flow['flow_id']}",
            {"username": username, "password": password, "client_id": self.client_id},
        )
        if not isinstance(result, dict) or result.get("type") != "create_entry":
            if isinstance(result, dict) and result.get("errors"):
                # Seen for real: an instance whose `.storage/auth` survived
                # while `auth_provider.homeassistant` -- the password store --
                # did not. Home Assistant then reports the account step as
                # done, because users exist, and no password can ever match.
                # No API can repair that, so say what will.
                raise RuntimeError(
                    f"login as {username} was refused ({result['errors']}). "
                    "If the account step is reported done but nothing can log "
                    "in, the instance has users in .storage/auth with no "
                    "auth_provider.homeassistant behind them -- move .storage "
                    "aside and let it onboard from scratch."
                )
            raise RuntimeError(f"login as {username} was refused: {result!r}")
        self._exchange(str(result["result"]))

    def _exchange(self, code: str) -> None:
        answer = self._call(
            "/auth/token",
            {
                "client_id": self.client_id,
                "grant_type": "authorization_code",
                "code": code,
            },
            form=True,
        )
        if not isinstance(answer, dict) or "access_token" not in answer:
            raise RuntimeError(f"no access token in {answer!r}")
        self.token = str(answer["access_token"])

    def finish(self, step: str) -> None:
        """Complete one post-account step. `integration` wants more than the rest."""
        if step == "integration":
            self._call(
                "/api/onboarding/integration",
                {"client_id": self.client_id, "redirect_uri": self.redirect},
                authenticated=True,
            )
        else:
            self._call(f"/api/onboarding/{step}", {}, authenticated=True)


def main(argv: list[str] | None = None) -> int:
    """Onboard the instance named on the command line, as far as it needs."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--url", default="http://127.0.0.1:8123", help="the instance to onboard"
    )
    parser.add_argument("--username", default="dev")
    parser.add_argument("--password", default="dev")
    parser.add_argument(
        "--name", default="Developer", help="the account's display name"
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=600,
        help="seconds to wait for the instance to answer (a first boot is slow)",
    )
    args = parser.parse_args(argv)

    host = urllib.parse.urlparse(args.url).hostname or ""
    if host not in LOOPBACK:
        print(
            f"refusing to onboard {args.url}: these credentials are public, so "
            "they belong only on a loopback address",
            file=sys.stderr,
        )
        return 2

    instance = Instance(args.url)
    try:
        status = instance.wait_until_answering(args.wait)
    except TimeoutError as error:
        print(f"{error}", file=sys.stderr)
        return 1

    steps = remaining(status)
    if not steps:
        print(f"{args.url} is already onboarded -- nothing to do")
        return 0

    try:
        for step in steps:
            if step == "user":
                instance.create_user(args.name, args.username, args.password)
            else:
                if instance.token is None:
                    instance.log_in(args.username, args.password)
                instance.finish(step)
            print(f"onboarding: {step} done", flush=True)
    except Exception as error:  # one line beats a traceback for a dev script
        print(f"onboarding failed at {step}: {error}", file=sys.stderr)
        print(
            "Finish it in the browser; nothing here is required for the "
            "instance to run.",
            file=sys.stderr,
        )
        return 1

    print(f"{args.url} is onboarded -- log in as {args.username} / {args.password}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
