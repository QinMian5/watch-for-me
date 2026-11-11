# ASR backend: faster-whisper

Use this route when resolved `asr.backend` is `faster-whisper`.

Resolve these configured values directly:

- `ASR_MODEL`: `asr.model`
- `ASR_MODEL_CACHE`: `asr.model_cache`
- `ASR_DEVICE`: `asr.device`
- `ASR_COMPUTE_TYPE`: `asr.compute_type`
- `ASR_QUALITY`: `asr.quality`

Verify that `ASR_MODEL_CACHE` is an absolute path. Use the absolute `TRANSCRIPTION_ROOT` bound by this module's workflow. Run the bundled adapter with faster-whisper supplied by uv's cached command environment:

```bash
uv run --no-project --with faster-whisper --with 'av<19' -- python \
  "$TRANSCRIPTION_ROOT/scripts/transcribe_faster_whisper.py" \
  "$PREPARED_AUDIO" \
  --output-prefix "$WORK_DIR/transcript" \
  --model "$ASR_MODEL" \
  --model-cache "$ASR_MODEL_CACHE" \
  --device "$ASR_DEVICE" \
  --compute-type "$ASR_COMPUTE_TYPE" \
  --quality "$ASR_QUALITY"
```

The adapter performs multilingual source-language transcription with automatic language detection, beam size 5, and backend-owned VAD. Translation into `target_language` happens after the Source Blocks are built.

Treat `$WORK_DIR/transcript.json` and `$WORK_DIR/transcript.srt` as the raw ASR outputs and apply the common verification in `references/whisper.md`.
