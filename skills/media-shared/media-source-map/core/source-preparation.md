# Prepare a Media Source

Probe one audio/video input, identify its source, and prepare its shared audio timeline. Video also supplies a visual input.

## Paths and source facts

Resolve `MEDIA_DIR` as `<output_root>/<media-name>/`. Use the online source title or supplied local title/file stem. Replace control characters and `/`, `\\`, `:`, `*`, `?`, `"`, `<`, `>`, and `|` with `-`, collapse repeated hyphens, and trim surrounding spaces, dots, and hyphens; use `media` if empty. Preserve collection/part identity and detect title collisions before writing into an existing bundle directory.

Create `WORK_DIR` as step 1 of `core/workflow.md` describes once `MEDIA_DIR` is resolved. Keep original local inputs unchanged and place downloads, conversions, raw ASR, diarization, and alignment artifacts only in this workspace.

Use `uvx --from static-ffmpeg static_ffmpeg` and `uvx --from static-ffmpeg static_ffprobe` for media operations. These commands cache platform binaries; obtain binary paths with `static_ffmpeg_paths` when a downstream command needs an explicit path.

Run the selected source fragment, then probe the acquired or local `MEDIA_PATH`:

```bash
uvx --from static-ffmpeg static_ffprobe -v error \
  -show_format -show_streams -of json "$MEDIA_PATH"
```

Record the title by the `media.title` rule of `core/source-map-contract.md`, original URL/absolute path, source ID when available, measured duration, `kind: audio|video`, and actual stream metadata. An audio source requires a decodable audio stream. A video source requires a decodable visual stream and records whether it contains audio. Treat a cover-art image in an audio container as audio.

## Text and acoustic evidence

Inventory platform manual/automatic captions, matching `.vtt`/`.srt`/`.ass` sidecars, and text subtitle streams. A usable track matches the original spoken language, has non-empty ordered timed cues, covers substantive speech, and exposes missing ranges. Prefer a complete manual original-language track, then a complete automatic track. Translated subtitles are auxiliary evidence; original speech comes from an original-language track or ASR.

Extract a selected embedded subtitle using its probed stream index:

```bash
uvx --from static-ffmpeg static_ffmpeg -i "$MEDIA_PATH" \
  -map "0:$SUBTITLE_STREAM_INDEX" -c:s webvtt "$WORK_DIR/subtitle.vtt"
```

Use the qualifying track when one exists; otherwise the transcript comes from ASR. Record the source as `media.transcript_provenance`: `platform-manual`, `platform-auto`, `sidecar`, `embedded`, or `whisper-asr`. Audio is still required for acoustic speaker attribution even when subtitles supply text. Reuse the source's audio or acquire a matching online audio format when needed.

Read `../media-transcription/manifest.yaml` and its always-loaded workflow. Pass `AUDIO_INPUT`, its probed `AUDIO_STREAM_INDEX`, `WORK_DIR`, the selected track or the ASR route, and configured runtime values. Complete shared audio preparation, applicable ASR, diarization, and alignment; speakers are decided per block in step 4 of `core/workflow.md`.

## Completion and lifecycle

Preparation leaves for step 4 of `core/workflow.md`: source metadata, measured duration, the visual input for video, `cues.json` and its provenance, `alignment.json` and `diarization.json` when diarization ran, and located limitations. Retain channel/format facts when a fallback changes what was analyzed.

Preparation completes with verified text/acoustic timing across substantive speech, a decodable visual input for video, and explicit gaps or silent ranges. No-speech media records its coverage with no speech blocks. A video that cannot supply visual evidence stays a video, with that limitation recorded.

Publication and cleanup belong to step 6 of `core/workflow.md`.
