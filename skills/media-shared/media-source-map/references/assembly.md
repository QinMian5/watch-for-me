# Assemble the source map

`scripts/assemble_source_map.py` builds `source_map.json` from `blocks.json`, two small files you write, and the speaker evidence. You decide meaning; the script copies text, times, IDs, cue ranges, and evidence. Do not write `original_text` again or write a one-off assembly script.

Keep every file below in `WORK_DIR`. `blocks.json` is the output of `build_blocks.py assemble` from `core/workflow.md`. `alignment.json` and `diarization.json` are the files from speaker review; leave them out when diarization did not run. A verified no-speech source uses a `blocks.json` holding `[]`, with no sections.

## 1. Write `structure.json`

```json
{
  "media": { "kind": "video", "title": "...", "...": "every media field of the contract" },
  "speakers": [{ "id": "SPK001", "name": "Dana Lee" }],
  "blocks": [
    { "id": "S002", "text": "Okay. Let's go with the server-side key." },
    {
      "id": "S003",
      "speaker_confidence": "low",
      "attribution_note": "Overlaps S002; assigned from the addressed question.",
      "confidence": "medium"
    }
  ],
  "fixes": [
    { "block": "S001", "find": "idem potency", "replace": "idempotency", "reason": "ASR split the word." }
  ],
  "sections": [{ "title": "Why retries double-charge", "blocks": ["S001", "S003"] }],
  "frames": [{ "timestamp": "00:03:10", "related_blocks": ["S003"] }],
  "limitations": []
}
```

- `media` holds the complete media fields of the contract.
- `speakers` gives names only. With diarization, the table and its IDs come from `diarization.json`; without it, list at most one speaker here, and it fills blocks whose plan speaker is null.
- `blocks` lists only the blocks whose fields differ from the defaults below, once each, by their assembled `S...` ID.
- A block's text is its assembled cue text. Give `text` to restore punctuation, capitalization, and spacing. It must keep the same words in the same order, counting each Chinese or Japanese character as a word; the script rejects anything else.
- Each word correction is a `fix` inside one block. `find` must occur exactly once in the block text, after any `text`. Give the evidence in `reason`. An empty `replace` deletes the matched text.
- `speaker` comes from the plan in `blocks.json`; change it in the plan and assemble again.
- A block holding a cue that the alignment marks `needs_review`, or whose voice differs from the block's speaker, must state `speaker_confidence`; the script names those cues otherwise.
- Defaults: `speaker_candidates` and `overlap` follow the alignment evidence of the block's cues, with candidates left empty when they only repeat the assigned speaker; `speaker_confidence` is `high` for an assigned speaker and `unknown` for null; `confidence` is `high`; `language` is the first spoken language. A block end up to 100 ms past the measured duration is clamped to it.
- A section names its first and last block and covers the blocks between them. `reading_type` defaults to the media value.
- Frames are listed in timeline order and get `F001`, `F002`, ... IDs and `assets/frames/HH-MM-SS-mmm.webp` paths. Give `image_path` when the file is named differently.

## 2. Write `translations.json`

```json
{
  "blocks": { "S001": "...", "S002": "..." },
  "sections": { "S001": "重试为何造成重复扣款" }
}
```

Translate every block and section title as `references/translation.md` describes. Section titles are keyed by the section's first block and are in the first of `media.spoken_languages`. When a block's language, or that title language, shares a primary subtag with the target language, leave the entry out. The script reports any missing or extra entry. When nothing needs translation, write `{}`.

## 3. Build

```bash
uv run --no-project --with pydantic -- python \
  "$SOURCE_MAP_ROOT/scripts/assemble_source_map.py" build \
  "$WORK_DIR/blocks.json" "$WORK_DIR/structure.json" "$WORK_DIR/translations.json" \
  [--alignment "$WORK_DIR/alignment.json" --diarization "$WORK_DIR/diarization.json"] \
  --output "$WORK_DIR/source_map.json"
```

The command checks text and fixes, block overrides, and translation pairs, then validates the result with the Pydantic models of `validate_source_map.py`. It prints one summary line, or located errors and exit code `1` without writing. Correct `structure.json` or `translations.json` and build again. The same inputs always produce the same map.

## Refresh translations

To change the target language of a published map, copy it to `$WORK_DIR/published.json` and rewrite its reader-visible notes, each `limitations[].detail` and `attribution_note`, in the new language. Write a new `translations.json` for its block IDs, set `TARGET_LANGUAGE` to the requested normalized tag, and run:

```bash
uv run --no-project --with pydantic -- python \
  "$SOURCE_MAP_ROOT/scripts/assemble_source_map.py" translate \
  "$WORK_DIR/published.json" "$WORK_DIR/translations.json" \
  --target-language "$TARGET_LANGUAGE" --output "$WORK_DIR/source_map.json"
```

The command changes only `media.target_language`, block translations, and section-title translations, and validates the result.
