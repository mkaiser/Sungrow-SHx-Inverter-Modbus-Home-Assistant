"""Running a capability survey from the device page, and saying where it is.

The survey used to run inside the options flow, behind a spinner. That was
wrong in three ways a contributor feels: a modal dialog cannot be left while
it works, an indeterminate spinner says nothing about how long a slow link
will take, and when it finished there was nowhere to put a *download* button
because a config flow has no such thing.

So it lives here instead, as state a device page can render. One runner per
config entry, holding what the last run did and what the current one is
doing, and telling the entities when either changes.

Three things this buys that the flow could not:

- **It survives navigation.** Press the button, go and look at something
  else, come back. The run is a task on the event loop, not a dialog.
- **The step is a state**, so the recorder keeps it. The history of the
  "current step" sensor *is* the log of what was probed and in what order --
  which is the thing a maintainer asks for when a survey stalls on one
  house's link and nowhere else.
- **A document can be downloaded**, because a signed URL can be put in a
  notification. See `download.py`.

Nothing here talks Modbus. `fingerprint.async_build` does the reading and
calls back with a fraction and a label; this turns those into state.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components import persistent_notification
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from .const import DISCORD_URL, DOMAIN, LINK_VALID, SURVEY_ISSUE_URL

if TYPE_CHECKING:
    from . import SungrowConfigEntry

_LOGGER = logging.getLogger(__name__)

#: Dispatcher signal, per entry, fired whenever the state below changes.
#: Entities subscribe to it rather than polling the runner.
SIGNAL_SURVEY = "sungrow_modbus_survey_{}"


@dataclass(frozen=True)
class SurveyState:
    """What the survey is doing, or last did.

    Frozen, and replaced rather than mutated, so an entity reading it while a
    probe updates it can never see half of one state -- the callback runs on
    the event loop between awaits, which is exactly where a mutable version
    would tear.
    """

    running: bool = False
    """True from the moment the button is pressed until the task ends."""

    fraction: float | None = None
    """Progress from 0.0 to 1.0, or None when nothing has run yet.

    Derived from a count of reads, not from time: a survey over a VPN takes
    twenty times as long as one over a cable, and the count is the only part
    of that which is knowable in advance.
    """

    step: str | None = None
    """What is being read right now, in the words the document uses."""

    started: datetime | None = None
    finished: datetime | None = None

    fields_read: int | None = None
    """Decoded fields in the finished document, for the summary line."""

    error: str | None = None
    """Why the last run failed, or None. Kept until the next run starts."""

    document: dict[str, Any] | None = field(default=None, repr=False)
    """The last document, held in memory for the download view to serve.

    Not written to disk. It carries a stand-in serial rather than a real one,
    but it is still somebody's installation, and a file in `www/` is served
    to anyone who can reach Home Assistant.
    """

    @property
    def percent(self) -> int | None:
        """The fraction as whole percent, which is what a sensor shows."""
        if self.fraction is None:
            return None
        return round(self.fraction * 100)


class SurveyRunner:
    """Owns one entry's survey: starts it, tracks it, announces it."""

    def __init__(self, hass: HomeAssistant, entry: SungrowConfigEntry) -> None:
        """Prepare a runner. Nothing runs until `async_start`."""
        self.hass = hass
        self.entry = entry
        self.state = SurveyState()
        self._task: asyncio.Task[None] | None = None
        self._lapsed: CALLBACK_TYPE | None = None

    @property
    def signal(self) -> str:
        """The dispatcher signal this runner's entities listen on."""
        return SIGNAL_SURVEY.format(self.entry.entry_id)

    @callback
    def _set(self, **changes: Any) -> None:
        """Replace the state and tell the entities, in that order."""
        self.state = replace(self.state, **changes)
        async_dispatcher_send(self.hass, self.signal)

    @callback
    def async_start(self, options: dict[str, Any] | None = None) -> bool:
        """Begin a survey. Returns False when one is already running.

        Refusing rather than queueing: two surveys at once would interleave
        their reads on one serialized connection, and a Sungrow grants few
        sessions. The button is disabled while one runs, so this is the
        second line of defence rather than the first.
        """
        if self._task is not None and not self._task.done():
            _LOGGER.debug("Survey already running for %s", self.entry.title)
            return False

        # A run already announced has a timer waiting to mark its link
        # lapsed. Left alone it would fire later and overwrite *this* run's
        # notification -- same `notification_id` -- with the words "the link
        # has expired", on a link that is minutes old.
        self._async_cancel_lapse()

        self._set(
            running=True,
            fraction=0.0,
            step=None,
            started=dt_util.now(),
            finished=None,
            error=None,
            fields_read=None,
        )
        self._task = self.entry.async_create_background_task(
            self.hass,
            self._async_run(options),
            name=f"sungrow survey {self.entry.entry_id}",
        )
        return True

    async def _async_run(self, options: dict[str, Any] | None) -> None:
        """Build the document, and end in a state either way.

        A failure is kept and shown rather than raised. Somebody who pressed
        a button offering to help is owed the reason, and a link that fails
        here is worth reporting in its own right -- the four states a probe
        can end in exist precisely because "it did not work" is not one
        answer but several.
        """
        # Imported here rather than at module level: `fingerprint` imports
        # the library, and this module is imported by the platforms.
        from .fingerprint import async_build

        try:
            document = await async_build(
                self.hass,
                self.entry,
                options,
                on_progress=self._on_progress,
                # Only here. This is the one caller that can spend five
                # minutes: a background task, with a progress bar somebody
                # can watch and a notification at the end. The diagnostics
                # download builds the same document and leaves it off,
                # because nothing there survives a wait like that.
                allow_dump=True,
            )
        except Exception as err:  # the message is the useful part
            _LOGGER.warning("Survey failed for %s: %s", self.entry.title, err)
            self._set(
                running=False,
                step=None,
                fraction=None,
                finished=dt_util.now(),
                error=f"{type(err).__name__}: {err}",
            )
            return

        # `values` is the decoded map, and its size is the number worth
        # showing: "95 of 104 fields" is how every summary in this project
        # reports a survey, and the other 9 are named beside it.
        readings = document.get("readings", {})
        self._set(
            running=False,
            fraction=1.0,
            step=None,
            finished=dt_util.now(),
            fields_read=len(readings.get("values", {})),
            error=None,
            document=document,
        )
        try:
            self._async_offer_the_document(document)
        # Deliberately broad, and logged rather than raised: the survey
        # succeeded and its state already says so. Losing the announcement
        # is bad, but losing it *silently* is what it used to do -- this
        # ran outside the try above, so anything it raised ended the task
        # with a bare asyncio traceback and a device page claiming success.
        except Exception:
            _LOGGER.exception(
                "The survey for %s finished but could not be announced. "
                "The document is still on the device page, under Download "
                "diagnostics",
                self.entry.title,
            )

    @callback
    def _async_offer_the_document(self, document: dict[str, Any]) -> None:
        """Put the finished document in front of the person who asked for it.

        A notification rather than anything in the entity: this is the one
        moment the integration has something to *give* somebody, and a
        sensor's attributes are not a place you can click. The link is signed
        and short-lived; `download.py` says why.

        Three things are said that the first version left out, each because
        a contributor hit it:

        - **where the notification is.** A persistent notification is a badge
          in the sidebar, and somebody watching the device page for a progress
          bar does not see it appear. So the button's own sensors say a run
          finished, and this says where the file is.
        - **that the link lapses, and when.** The notification outlives its
          signature by design -- an hour later it is still sitting there with
          a URL that now 401s, which reads as the integration being broken.
          The time is named here, and `_async_mark_lapsed` rewrites this
          message when it arrives.
        - **that a markdown link does not work at all.** Measured, after a
          contributor clicked one and nothing happened while the endpoint
          answered 200 to the same URL from curl. The frontend routes
          same-origin anchors internally; see the comment on the anchor
          below.

        And the route that never expires is named beside the one that does:
        the device page's own **Download diagnostics** builds the same
        document, from the same code, with the same testimony.
        """
        # Imported late for the same reason as `async_build`: this module is
        # imported by the platforms, and `download` imports the HTTP stack.
        from .download import async_download_url
        from .fingerprint import summarise

        url = async_download_url(self.hass, self.entry)
        lapses = dt_util.now() + LINK_VALID

        persistent_notification.async_create(
            self.hass,
            (
                # Rendered from the document rather than from the run, so a
                # summary cannot promise something the file does not carry.
                f"{summarise(document)}\n\n"
                # Raw HTML with `target`, not `[text](url)`. A markdown link
                # renders as a bare same-origin anchor, and the frontend's
                # global click handler swallows exactly those: it takes any
                # anchor with no `target`, no `download` and no `rel=external`
                # whose origin matches the page, calls preventDefault(), and
                # hands the path to the client-side router. `/api/...` is not
                # a panel, so the router does nothing at all -- the link looks
                # dead while the endpoint is answering 200. `target` is also
                # the only one of those three escapes that survives Home
                # Assistant's markdown sanitiser, whose whitelist for an
                # anchor is exactly ("target", "href", "title").
                f'<a href="{url}" target="_blank">Download the document</a>'
                " — this link stops working at "
                f"{lapses.strftime('%H:%M')}. After that, press "
                "**Run capability survey** again for a fresh one, or use "
                "**Download diagnostics** on the device page, which carries "
                "the same document and never expires.\n\n"
                "It carries a stand-in serial rather than the real one, and "
                "your address only if you allowed it. Send it to "
                f"[the issue tracker]({SURVEY_ISSUE_URL}) or "
                f"[Discord]({DISCORD_URL}) — what varies between "
                "installations is the thing no specification has told this "
                "project reliably."
            ),
            title=f"Survey finished: {self.entry.title}",
            notification_id=self._notification_id,
        )
        self._lapsed = async_call_later(self.hass, LINK_VALID, self._async_mark_lapsed)

    @property
    def _notification_id(self) -> str:
        """One id per entry, so a second run replaces rather than stacks."""
        return f"{DOMAIN}_survey_{self.entry.entry_id}"

    @callback
    def async_shutdown(self) -> None:
        """Drop the pending timer when the entry unloads.

        An hour-long timer outliving its config entry would fire against a
        runner nobody can see and a notification nobody asked for, and it is
        what Home Assistant's own test harness calls a lingering timer.
        """
        self._async_cancel_lapse()

    @callback
    def _async_cancel_lapse(self) -> None:
        """Forget a pending "the link has expired" rewrite."""
        if self._lapsed is not None:
            self._lapsed()
            self._lapsed = None

    @callback
    def _async_mark_lapsed(self, _now: datetime) -> None:
        """Say the link died, rather than leaving one that silently 401s.

        Replacing the notification rather than dismissing it: the summary is
        the part worth keeping -- somebody may not have read it yet -- and a
        notification that vanishes on its own looks like something went
        wrong. What changes is the promise, which is no longer true.
        """
        self._lapsed = None
        document = self.state.document
        if document is None:
            return
        # Imported late, as above.
        from .fingerprint import summarise

        persistent_notification.async_create(
            self.hass,
            (
                f"{summarise(document)}\n\n"
                "The download link in this notification has expired. Press "
                "**Run capability survey** again for a fresh one, or use "
                "**Download diagnostics** on the device page — that carries "
                "the same document and never expires.\n\n"
                "It carries a stand-in serial rather than the real one, and "
                "your address only if you allowed it. Send it to "
                f"[the issue tracker]({SURVEY_ISSUE_URL}) or "
                f"[Discord]({DISCORD_URL})."
            ),
            title=f"Survey finished: {self.entry.title}",
            notification_id=self._notification_id,
        )

    @callback
    def _on_progress(self, fraction: float, step: str) -> None:
        """Record one step. Called from the reading loop, on the event loop."""
        self._set(fraction=fraction, step=step)


@callback
def async_runner(entry: SungrowConfigEntry) -> SurveyRunner:
    """Return the runner for one entry, from its runtime data."""
    return entry.runtime_data.survey


Progress = Callable[[float, str], None]
"""What `fingerprint.async_build` calls after each read it can count."""
