"""Template rendering helpers for the Sungrow SHx integration.

The legacy YAML package expresses derived sensors, binary sensors,
selects and numbers as Jinja templates that reference other
``sensor.*``/``binary_sensor.*`` state ids. Rather than hand-port them
all, we rewrite ``states('sensor.X')``-style lookups to a bounded
``data['X']`` dictionary access and evaluate with a minimal Jinja
environment that implements the HA filters the templates actually use
(``is_number``, ``bitwise_and``).

Entity ids in HA are slugified from the entity name. We apply the
same slugification so that a description whose ``name`` is
``"Battery power"`` becomes ``"battery_power"`` in the context dict,
matching the ``states('sensor.battery_power')`` calls used in the
YAML.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Final

import jinja2

_LOGGER: Final = logging.getLogger(__name__)


# Matches states('sensor.X'), states('binary_sensor.X'), etc. — both
# quote styles, with optional whitespace.
_STATES_RE: Final = re.compile(
    r"""states\(\s*['"](?P<domain>[a-z_]+)\.(?P<slug>[a-z0-9_]+)['"]\s*\)"""
)


def slugify(name: str) -> str:
    """Slugify to match HA entity-id behavior closely enough for our purposes."""
    normalized = unicodedata.normalize("NFKD", name)
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii").lower()
    ascii_str = re.sub(r"[^a-z0-9]+", "_", ascii_str)
    return ascii_str.strip("_")


def _bitwise_and(a: Any, b: Any) -> int:
    try:
        return int(a) & int(b)
    except (TypeError, ValueError):
        return 0


def _is_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        try:
            float(value)
        except ValueError:
            return False
        return True
    return False


def _build_env() -> jinja2.Environment:
    env = jinja2.Environment(
        autoescape=False,
        undefined=jinja2.ChainableUndefined,
        enable_async=False,
    )
    env.filters["bitwise_and"] = _bitwise_and
    env.filters["is_number"] = _is_number
    env.tests["number"] = _is_number
    return env


_ENV: Final = _build_env()


def rewrite_template(source: str) -> str:
    """Rewrite ``states('domain.slug')`` references to ``data['slug']``.

    The domain prefix is dropped because sensor, binary_sensor and
    similar entity-id domains are merged into a single ``data`` dict
    keyed by slug when we render.
    """

    def _replace(match: re.Match[str]) -> str:
        slug = match.group("slug")
        return f"data.get({slug!r}, 'unknown')"

    return _STATES_RE.sub(_replace, source)


class RewrittenTemplate:
    """Pre-compiled Jinja template with ``states()`` rewritten."""

    __slots__ = ("_raw", "_rewritten", "_template")

    def __init__(self, source: str) -> None:
        self._raw = source
        self._rewritten = rewrite_template(source)
        try:
            self._template = _ENV.from_string(self._rewritten)
        except jinja2.TemplateSyntaxError:
            _LOGGER.debug(
                "Could not compile rewritten template:\n%s\n--- rewritten ---\n%s",
                source,
                self._rewritten,
            )
            raise

    def render(self, data: dict[str, Any], extra: dict[str, Any] | None = None) -> Any:
        """Render with the provided data dict."""
        context: dict[str, Any] = {"data": data, "fallback": None}
        if extra:
            context.update(extra)
        try:
            return self._template.render(**context)
        except Exception as err:  # noqa: BLE001 - template errors shouldn't crash HA
            _LOGGER.debug("Template render failed: %s\n%s", err, self._raw)
            return None


__all__ = ["RewrittenTemplate", "rewrite_template", "slugify"]
