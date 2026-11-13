# Grounding rules

Answer a source-linked question, or transcribe or translate a requested excerpt, at the scope the user asked for. A scoped answer needs no complete map, new Reader, or unrelated model setup.

## Scope and evidence

When a bundle exists, read `source_map.md` first, writing it with the reading-copy command of the [media-render](../media-render/manifest.yaml) module if needed, and `notes.json` when the question concerns the Notes. Consult `source_map.json` for translations, frames, and other evidence details, and the original recording when the question needs context beyond them. Otherwise inspect the supplied passage or recording interval, with enough adjacent context to resolve its meaning. Reuse verified timestamps and source IDs; cite the original recording's time range when no IDs exist. If neither exists, identify the supplied passage by its own wording.

When extraction or transcription is needed, create a task-owned temporary directory as `WORK_DIR` and load the [media-transcription](../media-transcription/manifest.yaml) module, plus the matching source fragment in [media-source-map](../media-source-map/manifest.yaml) when the source must first be acquired. Bind `MEDIA_DIR` to the bundle's directory when one exists. For acquisition or transcription, resolve configuration by `media-source-map/core/configuration.md`, bind `SOURCE_MAP_ROOT` as step 1 of its workflow does, and probe the audio stream as its `core/source-preparation.md` does. Preserve source-relative timing, supported speaker attribution, and uncertainty. Limit coverage claims to the material inspected. Remove the task-owned intermediates after delivery or reported failure.

Use an explicitly requested response language, otherwise the map's target language when available, otherwise the user's language. Leave existing bundle artifacts unchanged unless the user asks to update them.

## Answering questions

1. Find the source passages that support the answer, and the Notes claims the question concerns.
2. Answer from that evidence first.
3. Cite verified timestamp ranges and existing `S...` block IDs when available.
4. Include existing `F...` frame IDs when visual evidence contributes.
5. Label an inference across blocks, or a synthesis beyond the speaker's explicit statements, as analysis and name the supporting anchors.
6. Label requested external context `External` and cite it separately.
7. State any missing evidence or uncertainty that limits the answer.

## Requested excerpts

Transcribe or translate only the selected passage. Preserve its order, qualifications, interruptions, and supported speaker changes. Pair each original paragraph with its translation when needed; retain the original-only form when source and target languages match. Report any unresolved boundary or missing passage, so the excerpt claims only the coverage it has.

Preserve names, numbers, units, symbols, and technical literals from the original evidence. Treat a frame as evidence from one exact time and scope its interpretation to the visible state.

Identify source material with timestamps and stable IDs, for example `00:46:52–00:50:23 S042–S044` or `00:18:30 F004, S018`.
