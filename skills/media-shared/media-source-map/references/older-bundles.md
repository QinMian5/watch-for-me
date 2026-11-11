# Older bundles

A bundle may also hold files from an earlier version: any `.md` other than `source_map.md` and any `.html` other than `media.html`, such as a hand-written transcript or an HTML preview, and an old `card.json`. Leave them exactly as they are, unread.

An older `source_map.json` fails validation with located errors for removed speaker and top-level fields: `map/unknown-field` from the render command, and `Extra inputs are not permitted` from `validate_source_map.py`. Deleting those fields loses their values, so get the user's consent first. Then delete exactly those fields in place, leaving their values out of the rest of the map, and render as the [render contract](../../media-render/core/render-contract.md) describes; the evidence stays and nothing is retranscribed. New Notes mean writing a new `notes.json`.
