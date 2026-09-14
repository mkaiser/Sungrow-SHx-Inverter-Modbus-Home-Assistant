"""Handing the finished survey document to the person who ran it.

A config flow has no download button, which is most of why the survey moved
to the device page. Home Assistant's own answer to "let the user save this
file" is an authenticated HTTP view plus a **signed path**: a URL carrying a
short-lived signature, so a plain link in a notification works without the
browser holding a token.

That is what `homeassistant.components.diagnostics` does for its own
download, and it is worth copying rather than inventing -- the alternative,
writing the document into `www/`, serves it to anyone who can reach Home
Assistant, forever, with no expiry and no authentication. The document
carries a stand-in serial rather than a real one, but it is still a
description of somebody's house.

So: the document stays in memory on the runner, this view serves it to a
signed request, and the notification that appears when a survey finishes
carries the link.
"""

from __future__ import annotations

from http import HTTPStatus
import json
import logging
from typing import TYPE_CHECKING

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.components.http.auth import async_sign_path
from homeassistant.core import HomeAssistant, callback
from sungrow_modbus.fingerprint import label_for

if TYPE_CHECKING:
    from . import SungrowConfigEntry

from .const import DOMAIN, LINK_VALID

_LOGGER = logging.getLogger(__name__)

URL = "/api/sungrow_modbus/survey/{entry_id}"


class SurveyDownloadView(HomeAssistantView):
    """Serve one entry's most recent survey document as a file."""

    url = URL
    name = "api:sungrow_modbus:survey"

    # `requires_auth` stays at its default, True, and the signature is what
    # satisfies it: Home Assistant's auth middleware validates the `authSig`
    # query parameter and marks the request authenticated before the view is
    # reached. Setting it False would make this an open endpoint that any
    # unauthenticated caller could read, signature or not -- which is the
    # opposite of the intent.
    #
    # Not `@require_admin`, unlike core's diagnostics download: that link is
    # signed by the frontend on behalf of the admin who clicked it, while
    # this one is signed by a background task finishing a survey, which
    # `async_sign_path` attributes to the content user. Requiring admin would
    # reject the very link this integration hands out.

    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        """Return the document, or say why there is none."""
        hass: HomeAssistant = request.app["hass"]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            return web.Response(status=HTTPStatus.NOT_FOUND)

        runtime = getattr(entry, "runtime_data", None)
        document = getattr(getattr(runtime, "survey", None), "state", None)
        document = getattr(document, "document", None)
        if document is None:
            # Not an error: the ordinary state of an entry whose owner has
            # never pressed the button.
            return web.Response(
                status=HTTPStatus.NOT_FOUND,
                text="No survey has been run on this entry yet.",
            )

        filename = _filename(document)
        return web.Response(
            body=json.dumps(document, indent=2, sort_keys=False).encode(),
            content_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


def _filename(document: dict) -> str:
    """Name the file the way this repository names a fingerprint.

    Not a naming scheme of its own, and that is the point: a document from
    this button and one from `scripts/sungrow_scan/collect.py` describe the
    same thing in the same format, so they should arrive under the same name.
    A maintainer receiving twenty of these sorts them together, and
    `doc/device-fingerprints/` can take one without renaming it.

    `label_for` lives in the library so both producers derive it identically,
    and `tests/test_document_filenames.py` checks it against every
    fingerprint this repository has committed.

    The standalone survey appends the address tail when a name is already
    taken by a different reading; nothing here does, because a download is
    one file and the collision it guards against is a directory's problem.
    """
    return f"{label_for(document)}.json"


@callback
def async_download_url(hass: HomeAssistant, entry: SungrowConfigEntry) -> str:
    """Return a signed, time-limited URL for this entry's document."""
    return async_sign_path(
        hass,
        URL.format(entry_id=entry.entry_id),
        expiration=LINK_VALID,
    )


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the view once, however many entries exist.

    Home Assistant keeps views in a list and would happily hold several
    identical ones; the flag keeps a second entry from adding a duplicate.
    """
    if hass.data.get(f"{DOMAIN}_download_view"):
        return
    if getattr(hass, "http", None) is None:
        # `http` is a manifest dependency, so a real Home Assistant has set
        # it up before this runs. A test that drives `async_setup_entry`
        # against a bare `hass` has not, and the survey does not need a
        # download link to be tested -- so this declines rather than raising
        # and taking the whole entry down with it.
        _LOGGER.debug("No HTTP component; the survey download link is unavailable")
        return
    hass.http.register_view(SurveyDownloadView())
    hass.data[f"{DOMAIN}_download_view"] = True
