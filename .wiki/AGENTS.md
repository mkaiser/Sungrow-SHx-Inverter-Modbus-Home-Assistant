# AGENTS.md

## Wiki Schema

This is the schema of the Sungrow Modbus wiki. It follows llmwiki's starter
schema (`@llmwiki/core` 0.1.2), with this project's rules added. The
repository's working notes and **hard rules** are in the root `AGENTS.md`,
and they outrank anything here: ask before every push, do not hand-edit
generated files, preserve history in a migration, and **never publish a real
serial number or address**.

### Page Types

- **entity**: something that exists and can be measured. A device family
  (`device-sh-rt`), a register (`register-13074`), a firmware
  (`firmware-sapphire-h-b001-v000-p023`), or an installation under its
  owner's handle (`installation-fwitten`).
- **concept**: something the measurements taught, which code and tests
  depend on (`contention`, `control-test`, `legacy-id-adoption`).
- **source**: one raw source, summarized, with its facts in a table.
- **summary**: not used here. A source page already is the summary.
- **query**: an **open question**, or a saved answer to one. A claim with no
  source belongs here until a measurement answers it, with `results_count: 0`.

### Directory Structure

- `raw/`: raw documents with no other home in the repository.
- `wiki/`: processed wiki pages.
  - `wiki/entities/`: entity pages
  - `wiki/concepts/`: concept pages
  - `wiki/sources/`: source pages
  - `wiki/queries/`: query pages
  - `wiki/index.md`: master index
  - `wiki/log.md`: change log

**Most raw sources live outside `raw/`, where their tooling writes and reads
them**, and they are never moved:

| Source | Where | Written by |
| --- | --- | --- |
| inverter surveys | `device-survey/results/inverter/*.json` | `sungrow_survey.py --save`, a contributor's upload |
| wallbox documents | `device-survey/results/wallbox/*.json` | the same |
| the YAML package's entity record | `doc/legacy_entity_map.json` | by hand; tests read it |
| register documents | `doc/wallbox_registers.md`, `doc/cross_reference_modbus_manager.md` | by hand |

A source page's `source_path` is relative to `.wiki/`, as llmwiki's ingest
writes it, for example `../device-survey/results/inverter/<file>.json`.

**Never a source:** a survey transcript (`sungrow-scan-*.log`), a snapshot,
or any gitignored file. These carry real serials and addresses.

### Frontmatter Schema

**Required fields:**
- `type`: entity, concept, source, summary or query
- `title`: page title
- `tags`: array of tag strings
- `created`: creation date (YYYY-MM-DD)

**Required on source pages:** `source_path`, and `ingested`.
**Required on query pages:** `query`, and `results_count`.

```yaml
type: entity | concept | source | summary | query
title: string
tags: string[]
created: YYYY-MM-DD
updated: YYYY-MM-DD       # optional
source_path: string       # source pages only, relative to .wiki/
ingested: YYYY-MM-DD      # source pages only
query: string             # query pages only
results_count: number     # query pages only
```

No other keys. Anything more goes in the page body, so llmwiki's own tools
keep reading the pages.

### Naming Conventions

- Filenames are lowercased, extensions are stripped, non-alphanumeric
  characters become hyphens, and leading and trailing hyphens are removed.
- Source pages: `sources/{slug}-summary.md`, where the slug is the source's
  filename. That is the name llmwiki's ingest would give it, so its
  duplicate detection works.
- Entity pages: `entities/{device|register|firmware|installation}-{slug}.md`.
- Concept pages: `concepts/{slug}.md`, named for the claim where possible
  (`failed-read-is-not-refusal`).
- Installations go by the handle in the survey's `user_inputs.reporter`.
  An owner who published as `anonymous` stays anonymous: never connect a
  stand-in serial to a name the document does not carry.

### Writing Rules

- **Every claim cites its evidence**: a source page link, or a repository
  path in backticks (`src/sungrow_modbus/inverter/layout.py`,
  `tests/test_export_scale.py`). A claim with no evidence is a query.
- **Pages state what is true now.** `log.md` is the only history. When a
  measurement overturns a page, rewrite the page and log the ingest.
- **Register numbers, not protocol addresses**, unless the text says
  "protocol".
- **Devices by stand-in** (`anon-86493117545`), never by a real serial. No
  addresses, not even the last two octets.
- **Generated files are linked, never copied**: `doc/compatibility.md`,
  `doc/entity_name_review.md` and the generated `*_descriptions.py`.

### Ingest Workflow

Ingest is part of the change that brings the source in, the way a generated
file is regenerated in the commit that changes its input.

1. Write `sources/{slug}-summary.md`: frontmatter, the facts table, what did
   not answer, any `export_scale` and `control_test` block.
2. Update every entity and concept page that the source touches: its
   installation, model, firmware, and any register it measures. **Where it
   contradicts a page, say so on the page**, and decide which is right from
   the evidence rather than from recency.
3. Answer or narrow any query it bears on.
4. Add the index entries: `- [Title](path) — summary #tag #tag`.
5. Append to `log.md`: `## [YYYY-MM-DD] ingested | <subject>`.

### Lint Rules

llmwiki's rules, enforced in CI by `tests/test_wiki.py` with no extension
needed:

- **broken-links** (error): a link to a `.md` page that does not exist in
  `wiki/`
- **orphan-pages** (error here): a page with no inbound links that is not in
  the index
- **index-completeness** (error here): a page missing from `wiki/index.md`
- **stale-entries** (error): an index entry pointing to a deleted page
- **frontmatter-validation** (error here): the required fields above

And this project's additions:

- **source-exists**: every `source_path` resolves to a tracked file.
- **survey-ingested**: every committed survey has its source page.
- **repo-paths-exist**: a backticked repository path (`src/...`, `doc/...`,
  `tests/...`, ...) names a file or directory that exists.

In VS Code with the llmwiki extension, `@wiki /lint` runs the first five.

### Cross-Referencing Guidelines

- Link wiki pages with standard Markdown links: `[Title](relative/path.md)`,
  relative to the current file.
- **Refer to repository files in backticks, never by link.** llmwiki's lint
  treats any `.md` link as a wiki page, so a link to `doc/architecture.md`
  would be a broken link. The repo-paths-exist rule checks backticked paths
  instead.
- External URLs (http/https) are ignored by lint.
