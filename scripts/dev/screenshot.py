#!/usr/bin/env python3
r"""Retake a documentation screenshot from a scratch Home Assistant, headless.

Runs on the Playwright venv `scripts/dev/setup.sh` makes, not on the dev
environment's Python, so its pins never meet Home Assistant's:

    ~/.local/share/sungrow-screenshots/bin/python scripts/dev/screenshot.py \
        options-capability-test --url http://127.0.0.1:8125

The instance must be a **scratch** one with a Sungrow entry on the simulator
(`doc/development.md`, "Screenshots for the docs"): a shot clicks through
flows, and never belongs on an instance whose entry reaches real hardware.
So, like `ha_onboard.py`, this refuses a non-loopback URL and logs in as the
public `dev` / `dev`.

Each shot writes its file into `device-diagnosis/images/`; look at it before
committing it.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
import sys
from urllib.parse import urlparse

from playwright.sync_api import Page, sync_playwright

REPO = Path(__file__).resolve().parents[2]
IMAGES = REPO / "device-diagnosis" / "images"
LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def log_in(page: Page, url: str, username: str, password: str) -> None:
    """Log in through the form, as a person would."""
    page.goto(url)
    page.locator("input[name=username]").fill(username)
    page.locator("input[name=password]").fill(password)
    page.keyboard.press("Enter")
    page.wait_for_url(lambda now: "/auth/" not in now, timeout=30_000)


def settle(page: Page) -> None:
    """Let the login finish storing its session before navigating away.

    The session is stored once the first page after the login has loaded; a
    navigation before that lands back on the login form.
    """
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2_000)


def open_options(page: Page, url: str) -> None:
    """Open the Sungrow entry's options dialog from its integration page.

    The entry's cog is an `ha-icon-button` with no label of its own; the
    `button` inside it carries "Configure", which is what the role finds.
    """
    settle(page)
    page.goto(f"{url}/config/integrations/integration/sungrow_modbus")
    page.wait_for_load_state("networkidle")
    page.locator("ha-config-entry-row").get_by_role("button", name="Configure").click()
    # The dialog's host element has no box of its own, so Playwright calls it
    # hidden even when open: wait for the form inside it instead.
    page.locator("ha-dialog ha-form").first.wait_for()
    page.wait_for_timeout(1_000)


def options_capability_test(page: Page, url: str) -> Path:
    """Shoot the options dialog's capability test section, expanded."""
    open_options(page, url)
    section = page.locator("ha-expansion-panel").filter(
        has_text="What the capability test may do"
    )
    section.locator("[slot=header], .summary, .top").first.click()
    page.wait_for_timeout(1_000)
    target = IMAGES / "HA-settings-configure-capability-test.png"
    section.screenshot(path=str(target))
    return target


def device_diagnosis(page: Page, url: str) -> Path:
    """Shoot the device page's card with the two diagnosis buttons."""
    settle(page)
    page.goto(f"{url}/config/devices/dashboard")
    page.wait_for_load_state("networkidle")
    page.get_by_text("SH10RT", exact=True).first.click()
    page.wait_for_url(lambda now: "/config/devices/device/" in now, timeout=30_000)
    page.wait_for_load_state("networkidle")
    card = page.locator("ha-card").filter(has_text="Run read-only diagnosis").last
    card.wait_for()
    page.wait_for_timeout(1_000)
    target = IMAGES / "HA-settings-device-start-diagnosis.png"
    card.screenshot(path=str(target))
    return target


def setup_menu(page: Page, url: str) -> Path:
    """Shoot the first screen of Add integration.

    The dialog's host has no box of its own, so the shot is clipped to the
    first ancestor of the menu item the size of a dialog's surface.
    """
    settle(page)
    page.goto(f"{url}/config/integrations/dashboard")
    page.wait_for_load_state("networkidle")
    page.get_by_role("button", name="Add integration").click()
    page.wait_for_timeout(2_000)
    page.keyboard.type("Sungrow")
    page.wait_for_timeout(2_000)
    page.locator("dialog-add-integration").get_by_text("Sungrow Modbus").first.click()
    item = page.get_by_text("Perform the device diagnosis").first
    item.wait_for()
    page.wait_for_timeout(1_000)
    box = item.evaluate(
        """item => {
            let node = item;
            while (node && node.nodeType !== 9) {
                if (node.nodeType === 11) {
                    node = node.host;
                    continue;
                }
                const r = node.getBoundingClientRect();
                const wide = r.width >= 500 && r.width <= 900;
                if (wide && r.height >= 350 && r.height <= 800) {
                    return {x: r.x, y: r.y, width: r.width, height: r.height};
                }
                // Slotted content climbs through its slot, into the shadow
                // tree that draws the surface, not straight to its host.
                node = node.assignedSlot || node.parentNode;
            }
            return null;
        }"""
    )
    if box is None:
        raise RuntimeError("the dialog's surface was not found")
    target = IMAGES / "HA-settings-configure-integration.png"
    page.screenshot(path=str(target), clip=box)
    return target


SHOTS: dict[str, Callable[[Page, str], Path]] = {
    "setup-menu": setup_menu,
    "device-diagnosis": device_diagnosis,
    "options-capability-test": options_capability_test,
}


def main() -> int:
    """Take the chosen shot."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("shot", choices=sorted(SHOTS))
    parser.add_argument("--url", default="http://127.0.0.1:8125")
    parser.add_argument("--username", default="dev")
    parser.add_argument("--password", default="dev")
    args = parser.parse_args()
    url = args.url.rstrip("/")
    if urlparse(url).hostname not in LOOPBACK:
        print(f"{url} is not loopback: shots run on a scratch instance only")
        return 2

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        # English, because the docs are; tall, so a dialog is not scrolled.
        context = browser.new_context(
            locale="en-US", viewport={"width": 1280, "height": 2000}
        )
        page = context.new_page()
        log_in(page, url, args.username, args.password)
        target = SHOTS[args.shot](page, url)
        browser.close()
    print(f"Wrote {target.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
