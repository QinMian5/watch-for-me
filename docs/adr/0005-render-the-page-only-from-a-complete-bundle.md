---
status: accepted
---

# Render the page only from a complete bundle

`render_bundle.py` used to treat `notes.json` as optional. The workflow rendered before the Notes existed, only to get the `source_map.md` reading copy, and every such render also wrote a Reader-only `media.html`. That intermediate page needed its own code paths in the renderer and the viewer, and its title came from the map while a finished page took it from the Notes.

The reading copy depends only on the map, so it gets its own command, `write_reader_copy.py`. Agents run it whenever the map changes before the Notes exist. `render_bundle.py` now requires `notes.json`, fails with `input/unreadable` without it, and runs once the map and the Notes are both complete. It still writes both files, so a finished bundle stays consistent after one render.

A finished bundle has one title, the source's own `media.title`. It names the page and the reading copy. The Notes lose their `title` field, so they carry only content.

## Considered options

- **Have the assembly script write the reading copy when it builds a map.** Hand edits to the map, such as a Reader review fix, would still need a separate command, so the command is needed anyway.
- **Have agents read `source_map.json` directly before the Notes exist.** The map carries translations and evidence fields, which makes reading a long source in full much more expensive than reading the merged turns of the reading copy.

## Consequences

A translation refresh no longer renders between refreshing the map and rewriting the Notes, so the page never pairs new translations with stale Notes.
