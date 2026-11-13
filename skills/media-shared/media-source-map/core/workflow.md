# Ensure a Media Source Map

## 1. Resolve source and destination

Accept a current `source_map.json`, a Media Bundle, a local audio/video file, a locally available audio attachment, or one online video URL. Resolve the configuration needed by that route. An explicit map or bundle supplies its directory and target language unless the request overrides the language. Raw media uses `<output_root>/<media-name>/`, named by **Paths and source facts** in `core/source-preparation.md`; an online video's title comes from the first command of its source fragment.

Bind the directory as `MEDIA_DIR`, the map as `SOURCE_MAP_PATH`, and the absolute path of this module's directory, the one holding its `manifest.yaml`, as `SOURCE_MAP_ROOT`. Resolve this module's relative resource paths from `SOURCE_MAP_ROOT`.

A translation refresh or a new build writes files, so it works in a task workspace. Once `MEDIA_DIR` is known, create a unique `media-source-map.XXXXXX` directory under `MEDIA_DIR/.tmp/` with the platform's secure temporary-directory facility and bind it as `WORK_DIR`.

## 2. Reuse current evidence when valid

Validate an existing map with:

```bash
uv run --no-project --with pydantic -- python \
  "$SOURCE_MAP_ROOT/scripts/validate_source_map.py" "$SOURCE_MAP_PATH"
```

For a raw source, also confirm source identity, duration, and source-specific evidence against the request; a matching title is only a starting point. Reuse a validated map with a matching complete normalized target-language tag. An explicit language change refreshes translations while preserving original text, IDs, times, speaker evidence, and frames: follow **Refresh translations** in `references/assembly.md`, then continue at step 6.

If an explicitly supplied map fails validation, report its located errors and obtain a corrected map or usable raw source. When no map exists, prepare the selected raw source.

## 3. Prepare evidence

Read `core/source-map-contract.md`, `core/source-preparation.md`, and the selected source fragment. Complete acquisition and source preparation, which calls the `media-transcription` module for audio preparation, timestamped text, acoustic turns, and their alignment. Record `media.kind` from the input and stream evidence.

## 4. Build the complete timeline

Infer the dominant Reading Type: expository (explanation/argument), procedural (actions/results), dialogic (exchanges/positions), reportorial (events/evidence), or reflective (experience/interpretation). Preserve substantial section-level changes.

Work in files under `WORK_DIR`, starting from the normalized `$WORK_DIR/cues.json` the transcription workflow returns, and process all substantive speech in order. Read the full text once, as the draft prints it. After that, print only what changed and reread a stretch by block ID when a decision needs it. The full text is read again in the Reader review, from the reading copy.

### Boundaries and speakers

Settle paragraph boundaries and speakers before editing any text, so block IDs and times are fixed once:

```bash
BLOCKS="$SOURCE_MAP_ROOT/scripts/build_blocks.py"
uv run --no-project --python 3.12 -- python "$BLOCKS" draft "$WORK_DIR/cues.json" \
  --alignment "$WORK_DIR/alignment.json" --output "$WORK_DIR/plan.json"
```

Omit `--alignment` when no diarization ran. The draft suggests a block start at each certain speaker change, caption `>>` marker, and, past a minimum length, each sentence end or pause. It prints one line per block: ID, start, time, speaker, word count, the reason for the break, the cues that need speaker review with their candidate voices, and the full text.

Edit `plan.json` so each block is a natural paragraph that does not cross a resolved speaker change. Start a block inside a cue with `C0012@3`, that cue's fourth whitespace-separated word, when a sentence or a recoverable interjection begins there; text without spaces can only split between cues. Set each block's `speaker` by [speaker review](../../media-transcription/references/speakers.md); during the build, the plan is the only place a speaker is chosen. Check the edits with `preview`, which shortens each block to its first and last words (`--full` prints the text again), then assemble:

```bash
uv run --no-project --python 3.12 -- python "$BLOCKS" preview "$WORK_DIR/cues.json" \
  "$WORK_DIR/plan.json" --alignment "$WORK_DIR/alignment.json"
uv run --no-project --python 3.12 -- python "$BLOCKS" assemble "$WORK_DIR/cues.json" \
  "$WORK_DIR/plan.json" --output "$WORK_DIR/blocks.json"
```

Assembly gives each block its `S...` ID, order, start, end, speaker, `source_cues`, and the raw cue text. Leave `blocks.json` as assembled; to move a boundary or change a speaker, edit the plan and assemble again.

### Text and evidence

Read `references/assembly.md`. Record text, fixes, speaker strength, sections, and limitations (this step) and frames (step 5) in `structure.json`, and translations (step 5) in `translations.json`; the assembly script builds the map from them and the blocks.

- Restore punctuation and casing in a block's `text`, keeping each word in its block. Make only evidence-supported recognition corrections, each a `fix` with its evidence.
- Preserve qualifications, names, language switches, uncertainty, and meaningful interruptions. A monologue remains a monologue; question/answer relationships require source evidence.
- For each block holding a cue that needs speaker review, state `speaker_confidence`, and give the `attribution_note` when context decided the speaker. Set `language` and `confidence` where they differ from the defaults.

### Sections and limitations

Locate remaining source limitations; alignment diagnostics stay in the evidence fields. Build sections as the key line of a pyramid: under the source's main message, sections are the few groups of ideas that carry it, each a stretch of related blocks in source order. Start a new section where the source moves on to its next group, so each section gathers several related points under one idea. Give each a neutral source-language title naming that idea, and name its first and last block.

## 5. Translate and add applicable visuals

Read `references/translation.md`. Translate every block and section title into configured `target_language` in `translations.json` when primary language subtags differ; leave the entry out when they match. Preserve exact source anchors, terminology, numbers, units, qualifications, and uncertainty.

For video, read `references/visual-evidence.md`, review the full visual timeline, and retain the smallest complete set covering comprehension-relevant visual units. List each frame's timestamp and related blocks in `structure.json`; the script assigns stable `F...` IDs and relative `assets/frames/` paths, and each extracted frame must be saved at its path. Explain when a reviewed video needs no frames. Audio has `frames: []` and no frame-directory requirement.

## 6. Validate and publish

Apply `core/output-contract.md`, build the candidate map with the assembly script, and publish `SOURCE_MAP_PATH` only after structural and semantic checks succeed. All declared frame files must exist and satisfy the visual contract.

Return `MEDIA_DIR`, `SOURCE_MAP_PATH`, and `SOURCE_MAP_ROOT`. The Reader and the Notes consume the same map and any shared assets as read-only evidence. On success or a reported failure, remove only the exact task workspace, then its empty `.tmp` parent; preserve the original source, durable map and frame assets, and persistent runtimes.
