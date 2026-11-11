# Speaker evidence and attribution

Resolve these configured values and pass the verified device explicitly:

- `DIARIZATION_PYTHON`: `diarization.executable`
- `DIARIZATION_MODEL`: `diarization.model`
- `DIARIZATION_REVISION`: `diarization.revision`
- `DIARIZATION_DEVICE`: `diarization.device`

Missing model access, an unverified runtime, or an unavailable configured device is handled as `media-source-map/core/configuration.md` describes; transcription stays on the configured device. The local model groups voices; user identity hints and conversational evidence map those groups to names.

Use a supplied actual speaker count as `--num-speakers`. Otherwise pass supplied bounds as `--min-speakers` and/or `--max-speakers`; omit them to estimate automatically. A participant roster supplies names, not a speaker count.

```bash
"$DIARIZATION_PYTHON" "$TRANSCRIPTION_ROOT/scripts/diarize.py" "$PREPARED_AUDIO" \
  --model "$DIARIZATION_MODEL" --revision "$DIARIZATION_REVISION" \
  --device "$DIARIZATION_DEVICE" --output "$WORK_DIR/diarization.json"

uv run --no-project --python 3.12 -- python \
  "$TRANSCRIPTION_ROOT/scripts/align_speakers.py" \
  "$WORK_DIR/cues.json" "$WORK_DIR/diarization.json" \
  --output "$WORK_DIR/alignment.json"
```

The normalized diarization contains stable `SPK...` IDs, regular turns that preserve simultaneous speech, exclusive turns for boundary review, model provenance, and a prepared-audio hash. The alignment report supplies, per cue ID, provisional assignments, candidate voices, and clipped turn views. `needs_review`, a null assignment, and the 80% coverage threshold mark places for further judgment; final speaker decisions come from the review below. Decoder overshoot up to 100 ms is clamped to measured duration; larger mismatches fail validation. Zero-duration cues retain their text and require review.

## Resolve each block's speaker

In a source-map build, the speaker is decided per block while reviewing block boundaries: the block's `speaker` goes in the block plan, and its strength and reasoning in `structure.json`.

For each natural turn, combine the acoustic evidence with the words spoken, adjacent questions and answers, continuity of the speaker's account, self-reference, and user-supplied names and roles. Select the best-supported speaker. Context can resolve a brief competing voice, a pause, or an imprecise subtitle boundary. Use focused listening, reliable word timestamps, or bounded retranscription where the combined evidence still conflicts, restoring source offsets after retranscription.

Map voices to names using supplied identity context and consistent conversational evidence. Keep acoustic IDs stable. When a name is unnecessary or unavailable, leave `name` null so the speaker keeps a stable anonymous label; when a role-style address is needed, write it into `name`. Record the strength and reasoning of an inferred assignment only in `speaker_confidence` and `attribution_note`, independently of text confidence. Reserve null for speech that remains unattributable after this analysis. Gender, accent, or apparent authority alone do not establish identity.

Preserve natural turns, interruptions, responses, and substantive qualifications. Split a recoverable interjection from the surrounding speaker's turn, then merge timing-only fragments into readable paragraphs. A brief uncertain interjection leaves the surrounding paragraph's speaker in place. Retain overlap and any unrecovered speech in the source-map evidence; diarization does not separate mixed audio.
