# ASR backend: whisper.cpp

Use this route when resolved `asr.backend` is `whisper.cpp`.

Resolve:

- `WHISPER_CLI`: `asr.executable`
- `WHISPER_MODEL`: `asr.model`
- `ASR_QUALITY`: `asr.quality`

The setup route places the fixed Silero model beside the selected Whisper model. Set:

```bash
VAD_MODEL="$(dirname "$WHISPER_MODEL")/ggml-silero-v6.2.0.bin"
```

Verify that `WHISPER_CLI`, `WHISPER_MODEL`, and `VAD_MODEL` exist. Transcribe the shared prepared PCM waveform:

```bash
"$WHISPER_CLI" \
  -m "$WHISPER_MODEL" \
  -f "$PREPARED_AUDIO" \
  -l auto -osrt -oj -of "$WORK_DIR/transcript" -mc 32 \
  --vad -vm "$VAD_MODEL" \
  -vt 0.65 -vspd 300 -vsd 100 -vp 10 -vo 0.00 -sns \
  > "$WORK_DIR/transcript.log" 2>&1
```

whisper.cpp prints every segment and its progress; the log keeps them out of the conversation. On a non-zero exit, read the end of the log.

The selected model owns the `balanced` versus `maximum` quality difference. VAD parameters live in this backend fragment.

Treat `$WORK_DIR/transcript.json` and `$WORK_DIR/transcript.srt` as raw outputs and apply the common verification in `references/whisper.md`. Retain the model filename and raw whisper.cpp metadata in source-map ASR provenance.
