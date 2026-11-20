"""The attribution ask is on every surface that is meant to carry it.

The licence is MIT and requires only that the notice travels with a copy. It
does not require visible credit, so the ask for it is a request -- written
once in `doc/attribution.md`, and pointed at from the five places that are
read at five different moments:

- `AGENTS.md`, when an agent works inside this tree;
- a provenance line in each hand-written map's docstring, which travels with
  a *lifted snippet*, as `AGENTS.md` does not;
- a header comment in the YAML package's own files, which is the same line in
  the place it is most often copied from: `modbus_sungrow.yaml` is downloaded
  and pasted into a configuration far more often than this library is read,
  and the three multi-inverter copies inherit the line from it rather than
  carrying one of their own, so dropping it at the source drops it from four
  files at once;
- `llms.txt` and the README, when the repository is fetched over the web
  rather than cloned;
- `CITATION.cff`, when a tool or an agent is asked for a citation.

A request nobody is obliged to honour survives only as long as it is actually
present, and the generated descriptions get their header from
`scripts/generate/descriptions.py`, where it is easy to drop by accident. So
each surface is asserted here, and a new `registers.py` that forgets the line
fails on the commit that adds it.

`doc/attribution.md` itself is prose and is not asserted sentence by
sentence; what is checked is that it exists, names the repository and the
licence, and addresses agents, because those are what the pointers promise.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent

#: The project's own URL, as every surface spells it.
URL = "github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant"

#: The page the ask is written on, once.
PAGE = "doc/attribution.md"

#: The sentence a copied file carries. Hand-written maps have it in their
#: module docstring; the generated descriptions get it from the generator's
#: header strings; the YAML package has it in a header comment, where YAML's
#: only way of carrying a line is.
PROVENANCE = f"From {URL} (MIT)"

#: The credit line `doc/attribution.md` asks a copier to write: the project
#: and its author in the words a person reads, where `PROVENANCE` is the form
#: a search matches.
CREDIT = "Sungrow-SHx-Inverter-Modbus-Home-Assistant by mkaiser"

#: What the YAML package's header names above the URL. It says what the thing
#: is and who wrote it rather than repeating the repository's name, because
#: whoever reads it has the file and not the repository; the name is in the
#: URL on the line below. What must not get lost is the person.
AUTHOR = "by mkaiser"

#: Every map whose docstring must carry `PROVENANCE`: the register maps and
#: the entity descriptions that are *source*. The generated descriptions --
#: derived, number, switch, select, time and button -- are checked through
#: their generator instead, below, because `make gen-check` already fails on a
#: hand edit of the output.
MAPS = [
    *(
        Path("src/sungrow_modbus") / package / "registers.py"
        for package in (
            "hybrid_inverter",
            "battery",
            "string_inverter",
            "wallbox",
            "ihomemanager",
            "logger",
        )
    ),
    *(
        Path("custom_components/sungrow_modbus") / f"{name}_descriptions.py"
        for name in (
            "sensor",
            "battery",
            "wallbox",
            "external",
            "ihomemanager",
            "string_inverter",
        )
    ),
]

#: The YAML package's own files: the source, and the three multi-inverter
#: copies the generator writes from it. Their provenance sits in the leading
#: comment block, which is what a reader sees first and what the generator
#: carries through.
LEGACY = [
    Path("legacy") / name
    for name in (
        "modbus_sungrow.yaml",
        "modbus_sungrow_multiple_inverters_1.yaml",
        "modbus_sungrow_multiple_inverters_2.yaml",
        "modbus_sungrow_multiple_inverters_3.yaml",
    )
]

#: The generated description modules, and the header constant each one's
#: docstring comes from.
GENERATED = {
    "derived": "DERIVED_HEADER",
    "number": "NUMBERS_HEADER",
    "switch": "SWITCHES_HEADER",
    "select": "SELECTS_HEADER",
    "time": "TIMES_HEADER",
    "button": "BUTTONS_HEADER",
}


def _read(relative: str) -> str:
    return (REPO / relative).read_text(encoding="utf-8")


def _leading_comments(text: str) -> str:
    """Return the comment block at the top of a file, where a header belongs.

    Asserted instead of the whole file so that a provenance line buried
    somewhere in two thousand lines of sensors does not pass for a header.
    """
    header = []
    for line in text.splitlines():
        if not line.startswith("#"):
            break
        header.append(line)
    return "\n".join(header)


def test_the_page_exists_and_says_what_the_pointers_promise() -> None:
    """Every other surface sends the reader here, so this is the one page."""
    page = _read(PAGE)

    assert URL in page, f"{PAGE} does not name the repository"
    assert "MIT" in page, f"{PAGE} does not name the licence"
    assert "request" in page.lower(), (
        f"{PAGE} must say the ask is a request, not a licence condition"
    )
    assert re.search(r"\bagent\b", page, re.IGNORECASE), (
        f"{PAGE} must address agents: they are the surface it exists for"
    )
    assert CREDIT in page, (
        f"{PAGE} no longer shows the credit line it asks a copier to write; "
        f"the YAML package's header spells it the same way, and the two are "
        f"only worth asking for if they agree"
    )


@pytest.mark.parametrize(
    "surface", ["AGENTS.md", "README.md", "llms.txt", ".wiki/wiki/index.md"]
)
def test_a_surface_points_at_the_page(surface: str) -> None:
    """Read in the tree, over the web, and at the wiki's entry point."""
    text = _read(surface)

    assert PAGE in text or f"{PAGE.removeprefix('doc/')}" in text, (
        f"{surface} does not point at {PAGE}"
    )
    assert URL in text or surface == "AGENTS.md", (
        f"{surface} does not name the repository, and a reader who has only "
        "this file cannot credit what they cannot name"
    )


@pytest.mark.parametrize("path", MAPS, ids=lambda p: p.name)
def test_a_hand_written_map_carries_its_provenance(path: Path) -> None:
    """The line that travels with a lifted snippet, where the maps are."""
    text = (REPO / path).read_text(encoding="utf-8")
    docstring = text[: text.index('"""', 3)] if text.startswith('"""') else ""

    assert PROVENANCE in docstring, (
        f"{path} has no provenance line in its module docstring. A copy of "
        f"this file is the likeliest way its contents leave the project; see "
        f"{PAGE}."
    )


@pytest.mark.parametrize("path", LEGACY, ids=lambda p: p.name)
def test_the_yaml_package_carries_its_provenance(path: Path) -> None:
    """The file people download, and the one most often lifted from."""
    header = _leading_comments((REPO / path).read_text(encoding="utf-8"))

    assert PROVENANCE in header, (
        f"{path} has no provenance line in its header comment. This is the "
        f"most-copied file in the repository; the generated copies get the "
        f"line from `legacy/modbus_sungrow.yaml`, so if that is what is "
        f"missing, add it there and rerun "
        f"`scripts/generate/generate_second_inverter_config.py 1` (and 2, 3). "
        f"See {PAGE}."
    )
    assert AUTHOR in header, (
        f"{path}'s header no longer names who wrote it. The URL carries the "
        f"repository's name; this line is what tells a reader there is a "
        f"person behind the addresses -- see {PAGE}."
    )


@pytest.mark.parametrize("name, constant", sorted(GENERATED.items()))
def test_a_generated_description_carries_it_from_the_generator(
    name: str, constant: str
) -> None:
    """The output has it, and has it because the generator writes it."""
    generator = _read("scripts/generate/descriptions.py")
    start = generator.index(f"{constant} = ")
    header = generator[start : generator.index('\n"""\n', start)]

    assert PROVENANCE in header, (
        f"{constant} does not write the provenance line, so "
        f"{name}_descriptions.py loses it on the next `make gen`"
    )
    assert PROVENANCE in _read(
        f"custom_components/sungrow_modbus/{name}_descriptions.py"
    ), f"{name}_descriptions.py is out of date with {constant}; run `make gen`"


def test_the_citation_file_is_readable_by_a_tool() -> None:
    """What a tool or an agent reads when asked to cite this."""
    citation = yaml.safe_load(_read("CITATION.cff"))

    assert citation["cff-version"] == "1.2.0"
    assert citation["license"] == "MIT"
    assert URL in citation["repository-code"]
    assert any(
        author.get("family-names") == "Kaiser" for author in citation["authors"]
    ), "CITATION.cff names no author"


def test_the_citation_file_carries_no_email_address() -> None:
    """CFF permits one; the maintainer's address is not published here.

    The same rule as the diagnoses: what belongs to a person does not go into
    anything this repository tracks, and a citation file is read by machines
    that scrape.
    """
    assert "@" not in _read("CITATION.cff").replace("@llmwiki", ""), (
        "CITATION.cff contains what looks like an email address"
    )
