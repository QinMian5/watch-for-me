# Older bundles

A bundle may also hold files from an earlier version: any `.md` other than `source_map.md` and any `.html` other than `media.html`, such as a hand-written transcript or an HTML preview, and an old `card.json`. Leave them exactly as they are, unread.

An older `source_map.json` fails validation with located errors for removed speaker and top-level fields: `map/unknown-field` from the render command, and `Extra inputs are not permitted` from `validate_source_map.py`. Deleting those fields loses their values, so get the user's consent first. Then delete exactly those fields in place, leaving their values out of the rest of the map; the evidence stays and nothing is retranscribed. Write the reading copy as the [render contract](../../media-render/core/render-contract.md) describes, and render once `notes.json` exists. New Notes mean writing a new `notes.json`.

An older `notes.json` fails with `notes/unknown-field notes.json title`. The page takes its title from `media.title` now, so delete that one field, leave the rest of the Notes as they are, and mention the deletion at delivery.
