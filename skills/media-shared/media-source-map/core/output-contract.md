# Source Map output contract

The durable shared artifacts are:

- `source_map.json`
- `assets/frames/` only when video supplies frames, containing every frame referenced by the map

## Publication

Build the candidate `source_map.json` inside the task-owned workspace with the `build` or `translate` command of `references/assembly.md`; both run the bundled Pydantic validator and write nothing on failure. Publish it to `MEDIA_DIR/source_map.json` when the command succeeds. A map edited by hand, such as an older bundle, is checked with the validator command in `core/workflow.md`.

The validator checks JSON syntax, field schema, timestamps, unique IDs, contiguous block order, source block numbers that increase with order, `source_cues` ranges in source order, complete section membership and bounds, speaker references and acoustic overlap for assigned voices, and portable frame paths. It returns `0` for a valid format and `1` with field-level errors otherwise. It checks internal consistency only: coverage, recognition, speaker identity, translation, and frame selection are judged in workflow steps 4–6, even for a map that validates.

Clean up the task workspace as step 6 of `core/workflow.md` describes; the durable map and shared frame assets stay in `MEDIA_DIR`.
