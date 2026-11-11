# Local Whisper ASR

The transcription workflow loads this reference when no original-language timed-text track qualifies.

Read `asr.backend` from the resolved configuration, select its `asr_backend` route in `manifest.yaml`, and load that fragment. An incomplete backend configuration is handled as `media-source-map/core/configuration.md` describes.

Both routes write:

- `<output-prefix>.json` with a non-empty ordered `transcription` array
- `<output-prefix>.srt` with the same segment text and timing

Each JSON segment contains:

```json
{
  "timestamps": {
    "from": "00:00:00,000",
    "to": "00:00:01,250"
  },
  "offsets": {
    "from": 0,
    "to": 1250
  },
  "text": "..."
}
```

Normalize `transcript.json` as `TIMED_TEXT` and keep the SRT beside it. In `structure.json`, record `media.transcript_provenance: whisper-asr`, and backend, quality, model, device, compute type, detected language, and reported ASR parameters in `media.asr`.

Verify that JSON parses, the array is non-empty, offsets are non-negative and ordered, and each segment ends no earlier than it starts. Compare temporal coverage with measured media duration and record unexplained gaps.

Preserve generated text unchanged in raw JSON and SRT while building the source map.
