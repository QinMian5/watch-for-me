# Watch for Me configuration contract

The shared [configuration contract](../../../media-shared/media-source-map/core/configuration.md) defines the locations, precedence, schema, path resolution, and validation that every Watch for Me skill uses. Read it before drafting, then write that schema with resolved values to the selected location.

## Writing the configuration

Repository scope requires an actual repository root. Repository configuration is machine-local because it records platform, browser, device, and backend choices, so setup adds it to the local Git exclude file; the shared `.gitignore` and Git index continue to describe project artifacts. Preserve an explicitly requested absolute output path.

Setup chooses each value as follows:

- `schema_version` is integer `2`.
- `target_language` is the language tag the user confirms.
- `output_root` is the confirmed absolute or relative path.
- `cookie_browser` is a confirmed `yt-dlp` browser selector, or null for local-only use.
- `asr.backend` comes from the platform route in the manifest's `asr_backend` axis, and `asr.quality` from the user.
- `asr.executable`, `asr.model`, `asr.model_cache`, `asr.device`, and `asr.compute_type` come from the selected backend fragment after verification.
- `diarization` comes from the diarization backend fragment, which owns device selection and verification. It may be null while setup is incomplete; speaker attribution then requires setup. Tokens never appear in configuration.

## Profiles

| Backend target | Balanced | Maximum |
| --- | --- | --- |
| whisper.cpp on macOS arm64 | Large V3 Turbo, F16, Metal + Core ML | Large V3, F16, Metal + Core ML |
| faster-whisper with NVIDIA | Large V3 Turbo, CUDA `float16` | Large V3, CUDA `float16` |
| faster-whisper on CPU | Large V3 Turbo, CPU `int8` | Large V3, CPU `float32` |

The maximum CPU profile is intentionally available but resource-heavy; disclose that in the confirmation draft.
