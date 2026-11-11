# Configure faster-whisper

Use this route on macOS Intel, Windows, or Linux. Windows and Linux use CUDA when both NVIDIA detection and a CTranslate2 CUDA probe succeed; the remaining systems use CPU.

## Verify the package runtime

The shared `uv` core provides the runtime. Verify faster-whisper and its native dependencies through the same cached command environment used by the shared Media Source Map workflow:

```bash
uv run --no-project --with faster-whisper --with 'av<19' -- python -c \
  'import ctranslate2, faster_whisper, huggingface_hub'
```

`uv` supplies the compatible Python interpreter and reuses downloaded packages on later invocations.

faster-whisper 1.2.1 passes `metadata_errors` to `av.open`, which PyAV 19 removed, so every faster-whisper command keeps `av<19`.

## Select the model

Map confirmed quality to the faster-whisper model alias:

- `balanced` → `large-v3-turbo`
- `maximum` → `large-v3`

Resolve a model-specific `MODEL_CACHE`:

- macOS/Linux: `${XDG_CACHE_HOME:-$HOME/.cache}/watch-for-me/faster-whisper/<model-name>`
- Windows: `%LOCALAPPDATA%\watch-for-me\faster-whisper\<model-name>`

Expand it to an absolute path and create the directory. Construct the selected alias inside `uv run --no-project --with faster-whisper --with 'av<19'`, passing `MODEL_CACHE` as `WhisperModel(..., download_root=MODEL_CACHE)`. faster-whisper resolves its CTranslate2 repository mapping and keeps the selected model inside this Watch for Me cache root.

## Select the verified device profile

- Windows/Linux with working NVIDIA + CTranslate2 CUDA: `device: cuda`, `compute_type: float16`.
- Any CPU balanced profile: `device: cpu`, `compute_type: int8`.
- Any CPU maximum profile: `device: cpu`, `compute_type: float32`.

Use `ctranslate2.get_supported_compute_types(device)` and a model construction probe with the selected alias and `MODEL_CACHE` inside the uv package runtime. Combine the NVIDIA inventory with this runtime probe. When the probe selects the CPU route, present the result and updated draft for confirmation.

## Verify with a speech sample

Resolve `TRANSCRIPTION_ROOT` as `MEDIA_SHARED_ROOT/media-transcription`. Create a unique setup workspace with `mktemp -d` and keep its absolute path as `SETUP_STAGE`. Download the sample into it: `samples/jfk.wav` from `ggml-org/whisper.cpp` at a pinned commit, an 11-second mono 16 kHz PCM clip of public-domain speech served without credentials. Transcribe it with the selected profile through the shared adapter:

```bash
curl -fsSL -o "$SETUP_STAGE/jfk.wav" \
  https://raw.githubusercontent.com/ggml-org/whisper.cpp/b0a11594aec50892a02cd8d129eee2dfe93a8bb8/samples/jfk.wav
uv run --no-project --with faster-whisper --with 'av<19' -- python \
  "$TRANSCRIPTION_ROOT/scripts/transcribe_faster_whisper.py" \
  "$SETUP_STAGE/jfk.wav" \
  --output-prefix "$SETUP_STAGE/sample" \
  --model <model-name> \
  --model-cache "$MODEL_CACHE" \
  --device <device> \
  --compute-type <compute-type> \
  --quality <quality>
```

The profile passes when the adapter exits successfully, `sample.json` parses with the selected `model.device` and `model.compute_type`, its `transcription` list is non-empty with ordered offsets and text containing `country`, and `sample.srt` is non-empty. If a CUDA sample fails, report the cause and verify the CPU profile with the same sample before presenting it. Remove `SETUP_STAGE`, then verify it is absent.

Then write, for example:

```yaml
asr:
  backend: faster-whisper
  quality: balanced
  model: large-v3-turbo
  model_cache: /absolute/cache/path/watch-for-me/faster-whisper/large-v3-turbo
  device: cuda
  compute_type: float16
```

Write the absolute model cache path, verified device, and compute type.

## Cache lifecycle

Reuse `MODEL_CACHE` for the same model. During a quality change, keep the configured model cache until the replacement model passes the sample transcription and the new configuration resolves. Then remove the previous configured model cache listed in the confirmed draft. The shared uv package cache remains available to later Watch for Me and uv commands.
