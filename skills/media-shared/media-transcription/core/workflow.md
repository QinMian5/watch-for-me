# Shared media transcription

This workflow owns prepared audio, local ASR, acoustic turn evidence, and their verification. Source acquisition and final semantic/translated blocks belong to the sibling `media-source-map` module.

Bind `TRANSCRIPTION_ROOT` to the absolute path of this module's directory, the one holding its `manifest.yaml`; resolve this module's relative resource paths from that directory. Use the caller's task-owned `WORK_DIR`. Probe audio with `uvx --from static-ffmpeg static_ffprobe`; convert the selected stream once to mono 16 kHz signed PCM, keeping its full length, timing, and silence:

```bash
uvx --from static-ffmpeg static_ffmpeg -hide_banner -loglevel error \
  -i "$AUDIO_INPUT" -map "0:$AUDIO_STREAM_INDEX" -vn -ar 16000 -ac 1 \
  -c:a pcm_s16le "$WORK_DIR/audio.wav"
```

Set `PREPARED_AUDIO` to this WAV and verify its duration against the source. Separate online audio must represent the same selected part and time origin; resolve offsets before combining evidence if durations or origins disagree.

- When the caller has a complete original-language timed-text track, retain its provenance. Convert an `.ass` track to WebVTT with ffmpeg first.
- Otherwise load `references/whisper.md` and the selected ASR fragment. Both backends consume `PREPARED_AUDIO` and return normalized JSON/SRT with source-relative timings.
- Bind `TIMED_TEXT` to the selected `.vtt`/`.srt` track or `$WORK_DIR/transcript.json`, and normalize it into numbered cues:

```bash
uv run --no-project --python 3.12 -- python \
  "$TRANSCRIPTION_ROOT/scripts/normalize_timed_text.py" "$TIMED_TEXT" \
  --output "$WORK_DIR/cues.json"
```

  In a track that shows the rolling-caption pattern it removes the lines each cue carries over from the previous one; any other track keeps repeated lines. It removes cues that only carry a short sound label, such as `[Music]`, keeps caption word timestamps as `words`, and reports `timing` as `word`, `cue`, or `mixed`. A cue without words is only as precise as its cue range. `cues.json` is the transcript for alignment and block assembly; the raw track and its provenance stay as they were.
- Open `references/speakers.md` and run local diarization when the number of speakers is unknown, multiple speakers are expected, or speaker separation is requested. A user-confirmed single speaker may supply one identity without a clustering run.
- Keep text and acoustic outputs separate until alignment. Pass `alignment.json` and `diarization.json` to semantic map construction, which resolves each block's speaker by `references/speakers.md`.

Verify non-empty timed text for speech, ordered finite segment ranges within the measured duration, decoder provenance, and audio/diarization consistency. For silent audio, the observed coverage and limitation are the result. Video without speech may still supply visual evidence through the caller.

All WAV, raw JSON/SRT, raw diarization, and alignment reports remain in `WORK_DIR`. For a complete bundle, the caller retains verified speaker metadata, turn evidence, source blocks, and limitations in the final map. For scoped inspection, return the verified evidence needed for the response without requiring map publication. The caller owns cleanup. Preserve the selected source file and persistent models.
