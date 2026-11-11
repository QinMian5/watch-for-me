---
status: accepted
---

# Render Media Pages from structured data

Agents no longer write documents for people. An agent produces `source_map.json`, the evidence, and an optional `card.json`, a Media Card that cites the map only by `S...` and `F...` IDs. (Renamed by [ADR-0004](0004-rename-to-watch-for-me.md): the Media Card is now Media Notes, and `card.json` is now `notes.json`.) A Python command, `render_bundle.py`, validates both files and deterministically projects a single-file `media.html` for people and a `source_map.md` reading copy for agents. `media.md`, `media-card.md`, `reader.html`, and `audit_reader.py` are retired.

Hand-written Reader Markdown made a model copy a whole transcript into a second document, and `audit_reader.py` then had to prove that nothing had changed: coverage, order, exact text, timestamps, and speaker labels. Projecting from the map guarantees those properties by construction. Agent effort goes to the judgments a tool cannot make, which are the map's content and the Card's organization. Validation and rendering share one pipeline, and a validation or recheck error leaves the existing outputs untouched. Writing the two outputs is not transactional: because they can be rebuilt at any time, a failed write is repaired by rendering again rather than rolled back, and `--check` reports any file left stale.

## Considered options

- **Keep Markdown as the source and convert it to HTML.** The page's search, speaker filter, two-way links, and synchronized scrolling need structured data, so the converter would have to parse prose back into structure, and the audit would stay.
- **Have agents write HTML.** This keeps every copying risk and adds an injection risk for transcript text such as `</script>`.
- **A Card schema for each Reading Type.** A generic `{title, units[{heading, paragraphs[{text, speakers?, cites?, frames?}]}]}` carries the same content. Structure is limited to metadata about who said something and where it came from. Reading Type guidance remains writing guidance.
- **A local server, or a page that writes files.** A single HTML file with no running service is a hard constraint, so the page copies a rename prompt for the agent to apply.

## Consequences

`source_map.md` keeps a Markdown extension for readability, but it is a generated projection and nobody edits it. Both rendered files are disposable and can be rebuilt at any time.

Card text is plain. Commands and formulas are not typeset, and a validator cannot notice an omitted decision or action item. Card text also does not name speakers, so renaming a speaker only requires another render.

`card.json` records neither a map fingerprint nor a language. A map rebuild that reassigns IDs, or a change of target language, must delete the Card in the workflow; the tools cannot detect that a block's content changed under the same ID.

The map drops `speakers[].role`, `speakers[].identity_basis`, and the top-level `glossary`, which the page does not display. It therefore no longer records whether a name was supplied or inferred.

The page's body is rendered at runtime from JSON data islands, so it has no content without JavaScript. Repository tests compare golden files and exercise hostile text; they do not drive a browser. Interaction is checked by hand against the Media Page acceptance list.

## Existing bundles

This extends ADR-0001's decision to provide no adapters for historical bundles. Because the removed fields are rejected as unknown, every existing `source_map.json` fails validation with located errors. With the user's consent, an agent deletes those fields by hand and renders the bundle, preserving the evidence without retranscribing it. Existing `media.md`, `media-card.md`, and `reader.html` files stay where they are and are not read, converted, or deleted. An old Card is not migrated; a new Card means writing `card.json`.
