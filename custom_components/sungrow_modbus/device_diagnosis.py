"""The diagnosis of a device that is not an inverter: read it, publish it.

The inverter's `DiagnosisRunner` is built around the inverter: the block read
test, the capability test, auto repeat, a ledger. A wallbox at its own
address, an iHomeManager or a Logger has none of that. Their diagnosis only
reads: it dumps the device's bands, builds the library's document for it --
the same document the terminal scripts write -- and offers it for download.

The runner keeps the inverter runner's surface where the diagnosis entities
read it (`state`, `signal`, `mode`, `continuous`, `async_start`, `async_stop`,
`async_announce_start`, `entry`), so the start and stop buttons and the three
sensors work unchanged. The download view serves `state.document` as it does
for an inverter.

Nothing here writes to a device.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import datetime
import logging
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util
from sungrow_modbus import diagnosis_document as diagnosis, dump as register_dump

from .const import (
    CONF_DIAGNOSIS_COMMENT,
    CONF_PUBLISH_ADDRESS,
    CONF_REPORTER,
    DIAGNOSIS_ISSUE_URL,
    DIAGNOSIS_MODE_READ_ONLY,
    DOMAIN,
    LINK_VALID,
)
from .coordinator import SungrowConfigEntry
from .network_records import async_network_names

_LOGGER = logging.getLogger(__name__)

#: What a builder reports progress with: a fraction and the step's words.
Progress = Callable[[float, str], None]

#: Reads the device whole and returns its document, or raises.
Builder = Callable[[Progress], Awaitable[dict[str, Any]]]

#: Turns a finished document into the notification's summary lines.
Summary = Callable[[dict[str, Any]], str]


class _NeverRepeats:
    """Auto repeat, for a device that has nothing to repeat."""

    active = False
    waiting = ""

    def next_start(self, _now: datetime) -> None:
        return None

    def attributes(self) -> dict[str, Any]:
        return {}

    @callback
    def async_turn_off(self, _why: str) -> None:
        return None


class NoLink(Exception):
    """The device answered nothing: the link, not the device. No document."""


class DeviceDiagnosisRunner:
    """Owns one non-inverter entry's diagnosis: starts it, tracks it, announces it."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: SungrowConfigEntry,
        build: Builder,
        summary: Summary,
    ) -> None:
        """Prepare a runner. Nothing runs until `async_start`."""
        # Imported here: `diagnosis.py` imports the platforms' helpers, and
        # the state class is all this needs from it.
        from .diagnosis import SIGNAL_DIAGNOSIS, DiagnosisState

        self.hass = hass
        self.entry = entry
        self.state = DiagnosisState()
        self.signal = SIGNAL_DIAGNOSIS.format(entry.entry_id)
        self.mode = DIAGNOSIS_MODE_READ_ONLY
        self.continuous = _NeverRepeats()
        self._build = build
        self._summary = summary
        self._task: asyncio.Task[None] | None = None
        self._lapsed: CALLBACK_TYPE | None = None
        self._stop_requested = False

    @callback
    def _set(self, **changes: Any) -> None:
        self.state = replace(self.state, **changes)
        async_dispatcher_send(self.hass, self.signal)

    @callback
    def async_start(self, *, capability_test: bool = False, **_: Any) -> bool:
        """Begin a read. False while one runs, or when a write test is asked for."""
        if capability_test:
            _LOGGER.warning(
                "%s has no capability test; only the read-only diagnosis runs",
                self.entry.title,
            )
            return False
        if self._task is not None and not self._task.done():
            return False
        self._async_cancel_lapse()
        self._stop_requested = False
        self._set(
            running=True,
            fraction=0.0,
            step=None,
            started=dt_util.now(),
            finished=None,
            extended=False,
            error=None,
            fields_read=None,
            part="diagnosis",
            stopped=False,
        )
        self._task = self.entry.async_create_background_task(
            self.hass,
            self._async_run(),
            name=f"sungrow diagnosis {self.entry.entry_id}",
        )
        return True

    @callback
    def async_stop(self) -> None:
        """End the read in flight. It only reads, so nothing is put back."""
        if self._task is not None and not self._task.done():
            self._stop_requested = True
            self._task.cancel()

    @callback
    def async_announce_start(self, _mode: str) -> None:
        """Say a read started, until the result replaces it."""
        persistent_notification.async_create(
            self.hass,
            "A read-only diagnosis is running. It only reads; nothing on the "
            "device changes. A notification tells you when it has finished.",
            title=f"Diagnosis started: {self.entry.title}",
            notification_id=self._notification_id,
        )

    async def _async_run(self) -> None:
        try:
            async with self.entry.runtime_data.async_paused():
                document = await self._build(
                    lambda fraction, step: self._set(fraction=fraction, step=step)
                )
        except asyncio.CancelledError:
            if not self._stop_requested:
                raise
            self._set(
                running=False,
                step=None,
                fraction=None,
                stopped=True,
                finished=dt_util.now(),
                part=None,
            )
            return
        except Exception as err:  # a button press must not crash the loop
            _LOGGER.exception("Diagnosis failed for %s", self.entry.title)
            self._set(
                running=False,
                step=None,
                fraction=None,
                finished=dt_util.now(),
                error=f"{type(err).__name__}: {err}",
                part=None,
            )
            return
        self._set(
            running=False,
            step=None,
            fraction=1.0,
            finished=dt_util.now(),
            error=None,
            document=document,
            part=None,
            fields_read=_fields(document),
        )
        self._async_offer(document)

    @callback
    def _async_offer(self, document: dict[str, Any]) -> None:
        """Offer the document, as the inverter's diagnosis does (`diagnosis.py`)."""
        from .download import async_download_url

        url = async_download_url(self.hass, self.entry)
        lapses = dt_util.now() + LINK_VALID
        persistent_notification.async_create(
            self.hass,
            f"{self._summary(document)}\n\n"
            # Raw HTML with `target`: `DiagnosisRunner._async_offer_the_document`
            # says why a markdown link does nothing here.
            f'<a href="{url}" target="_blank">Download the document</a>'
            f" — this link stops working at {lapses.strftime('%H:%M')}. After "
            "that, press **Diagnosis: start** again for a fresh one.\n\n"
            "It carries a stand-in in place of anything that could be a serial "
            "number, and your address only if you allowed it. Send it to "
            f"[the diagnosis issue]({DIAGNOSIS_ISSUE_URL}).",
            title=f"Diagnosis finished: {self.entry.title}",
            notification_id=self._notification_id,
        )
        self._lapsed = async_call_later(self.hass, LINK_VALID, self._async_mark_lapsed)

    @callback
    def _async_mark_lapsed(self, _now: datetime) -> None:
        self._lapsed = None
        if self.state.document is None:
            return
        persistent_notification.async_create(
            self.hass,
            f"{self._summary(self.state.document)}\n\nThe download link has "
            "expired. Press **Diagnosis: start** again for a fresh one, and send "
            f"it to [the diagnosis issue]({DIAGNOSIS_ISSUE_URL}).",
            title=f"Diagnosis finished: {self.entry.title}",
            notification_id=self._notification_id,
        )

    @property
    def _notification_id(self) -> str:
        return f"{DOMAIN}_diagnosis_{self.entry.entry_id}"

    @callback
    def _async_cancel_lapse(self) -> None:
        if self._lapsed is not None:
            self._lapsed()
            self._lapsed = None

    @callback
    def async_shutdown(self) -> None:
        """Drop the pending timer and any read in flight when the entry unloads."""
        self._async_cancel_lapse()
        if self._task is not None and not self._task.done():
            self._task.cancel()


def _fields(document: dict[str, Any]) -> int:
    """Count the decoded readings in whichever section the document carries."""
    for key in ("wallbox", "ihomemanager", "logger"):
        section = document.get(key)
        if isinstance(section, dict):
            return len(section.get("readings") or {})
    return 0


def testimony(entry: SungrowConfigEntry) -> tuple[dict[str, str], str]:
    """Return what the owner said, and the address tail they allowed."""
    options = entry.options
    said = {
        "reporter": options.get(CONF_REPORTER) or "anonymous",
        "comment": options.get(CONF_DIAGNOSIS_COMMENT, ""),
    }
    tail = diagnosis.address_tail(
        entry.data.get(CONF_HOST, ""), bool(options.get(CONF_PUBLISH_ADDRESS, False))
    )
    return said, tail


def wallbox_builder(entry: SungrowConfigEntry) -> Builder:
    """Return the read of a wallbox at its own address, over TLS.

    The bands are cut to measured starts (`dump.WALLBOX_TLS_BANDS`): over TLS a
    read must start on a data point's first register. Masked and stood in by
    the library (`diagnosis_document.wallbox_from_dump`), so this document and
    the one `wallbox_direct.py` writes cannot differ in what they publish.
    """

    async def build(progress: Progress) -> dict[str, Any]:
        coordinator = entry.runtime_data.wallbox
        assert coordinator is not None
        device = coordinator.device
        bands = register_dump.WALLBOX_TLS_BANDS
        total = register_dump.block_count(bands)

        def on_block(done: int, _total: int, why: str) -> None:
            progress(done / max(total, 1), f"reading {why} ({done} of {total})")

        raw = await register_dump.async_dump(
            device.async_read_words, on_progress=on_block, bands=bands
        )
        if not register_dump.answered(raw):
            raise NoLink("the wallbox answered none of its registers")
        port = entry.data.get(CONF_PORT)
        said, tail = testimony(entry)
        return diagnosis.wallbox_document(
            command_line=f"{diagnosis.COLLECTED_BY_INTEGRATION} diagnosis",
            read_at=dt_util.utcnow()
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
            user_inputs=said,
            address_tail=tail,
            connection={"protocol": "Modbus TCP inside TLS", "port": port},
            wallbox=diagnosis.wallbox_from_dump(device.unit_id, raw, path="tls"),
            network_names=await async_network_names(
                coordinator.hass, entry.data.get(CONF_HOST, "")
            ),
        )

    return build


def wallbox_summary(document: dict[str, Any]) -> str:
    """Say what a wallbox document holds, in the notification's words."""
    section = document.get("wallbox") or {}
    readings = section.get("readings") or {}
    model = (readings.get("model_name") or {}).get("value") or "wallbox"
    stand_in = section.get("serial_anonymized_hashed") or "anon-…"
    return (
        f"- **{model}**, read at its own address over TLS.\n"
        f"- {len(readings)} values decoded.\n"
        f"- Published as `{stand_in}` — a stand-in, not its serial number."
    )


def unit_247_builder(entry: SungrowConfigEntry, unit: Any, package: Any) -> Builder:
    """Return the read of an iHomeManager or Logger at unit 247.

    `package` is the library's `ihomemanager` or `logger`: its `BANDS`,
    `section` and `document` are what `ihomemanager_direct.py` writes, so a
    document from here and one from the terminal cannot differ. Any text in a
    register no field reads is masked there, in case it is a serial.
    """
    from sungrow_modbus.diagnosis import word_reader

    from .const import CONF_TLS

    async def build(progress: Progress) -> dict[str, Any]:
        bands = package.BANDS
        total = register_dump.block_count(bands)

        def on_block(done: int, _total: int, why: str) -> None:
            progress(done / max(total, 1), f"reading {why} ({done} of {total})")

        raw = await register_dump.async_dump(
            word_reader(unit), on_progress=on_block, bands=bands
        )
        if not register_dump.answered(raw):
            raise NoLink(f"the {package.DOCUMENT} answered none of its registers")
        port = entry.data.get(CONF_PORT)
        section = package.section(raw, port=port)
        del raw
        said, tail = testimony(entry)
        tls = bool(entry.data.get(CONF_TLS, False))
        document: dict[str, Any] = package.document(
            command_line=f"{diagnosis.COLLECTED_BY_INTEGRATION} diagnosis",
            read_at=dt_util.utcnow()
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
            user_inputs=said,
            address_tail=tail,
            connection={
                "protocol": "Modbus TCP inside TLS" if tls else "Modbus TCP",
                "port": port,
            },
            **{package.DOCUMENT: section},
        )
        return document

    return build


def unit_247_summary(document: dict[str, Any]) -> str:
    """Say what an iHomeManager or Logger document holds."""
    kind = str(document.get("document") or "device")
    section = document.get(kind) or {}
    readings = section.get("readings") or {}
    masked = section.get("masked_text") or []
    name = "iHomeManager" if kind == "ihomemanager" else "Logger"
    return (
        f"- **{name}** at unit 247, port {section.get('port')}.\n"
        f"- {len(readings)} values decoded.\n"
        f"- {len(masked)} undocumented text field(s) masked, in case one is a "
        "serial number."
    )
