# Configuration

Resolve the configuration fields required by the selected source-map route. The precedence is:

1. values explicitly supplied in the current request
2. repository configuration at `<repo>/.config/watch-for-me/config.yaml`
3. user configuration

Use `${XDG_CONFIG_HOME:-$HOME/.config}/watch-for-me/config.yaml` on macOS and Linux, and `%APPDATA%\watch-for-me\config.yaml` on Windows. Inside a Git repository, use its top level as `<repo>` and include the repository layer. Outside Git, apply the request and user layers. Overlay values key by key and remember which layer supplied `output_root`.

The resolved configuration contains:

```yaml
schema_version: 2
target_language: zh-CN
output_root: media
cookie_browser: chrome
asr:
  backend: faster-whisper
  quality: balanced
  model: large-v3-turbo
  model_cache: /absolute/cache/path/watch-for-me/faster-whisper/large-v3-turbo
  device: cuda
  compute_type: float16
diarization:
  backend: pyannote.audio
  executable: /absolute/watch-for-me/pyannote/runtime/bin/python
  model: /absolute/watch-for-me/pyannote/community-1
  revision: 3533c8cf8e369892e6b79ff1bf80f7b0286a54ee
  device: cuda
```

`asr.backend` is `whisper.cpp` or `faster-whisper`; `asr.quality` is `balanced` or `maximum`. `asr.model` is a faster-whisper model alias or a local whisper.cpp model path; `asr.device` and `asr.compute_type` record verified runtime facts. The selected backend fragment owns its support paths, VAD, and decoding settings.

Apply configuration in stages:

- A complete `source_map.json` or media bundle supplies its own location and target language. Current-request `target_language` can request a translation refresh. Source preparation fields are resolved when the map needs to be built.
- A raw local source requires `target_language` and `output_root` to locate its bundle. Source preparation resolves complete ASR configuration after timed-text discovery selects ASR.
- A raw online source also requires `cookie_browser` for metadata and timed-text discovery. Source preparation resolves complete ASR configuration after it selects ASR.

For ASR, validate `asr.backend`, `asr.quality`, `asr.model`, `asr.device`, and `asr.compute_type` together. The `whisper.cpp` backend also requires `asr.executable` as an existing absolute `whisper-cli` path. The `faster-whisper` backend requires `asr.model_cache` as its absolute, model-specific cache root.

For unknown/multiple speakers or requested speaker separation, validate the complete `diarization` block: pyannote backend, existing absolute executable, complete local model directory, pinned revision, and verified `cpu`, `cuda`, or `mps` device. Device selection and reconfiguration belong to `setup-watch-for-me`. A user-confirmed single speaker may be attributed from supplied identity context without model execution.

When a field the selected route needs is missing or fails validation, run `setup-watch-for-me` before continuing. If setup leaves diarization incomplete, tell the user, build blocks with a null `speaker`, and record a `speaker` limitation.

## Path resolution

- An explicit output path in the current request is resolved as the request states; a relative path is relative to the current working directory.
- A relative `output_root` supplied by repository configuration is relative to the repository root.
- A relative `output_root` supplied by user configuration is relative to the current working directory.
- A `whisper.cpp` `asr.executable` is resolved as its existing absolute path.
- A faster-whisper `asr.model_cache` is resolved as its absolute path and passed to the adapter through `--model-cache`.

Configuration stores the browser selector used by `yt-dlp`; cookie data remains in the browser profile. Set `COOKIE_BROWSER` from `cookie_browser` for the online-video route.

`target_language` controls translations, translated section titles, and explanatory labels stored in `source_map.json`. Normalize language tags to lowercase and replace `_` with `-`. Compare primary subtags to decide whether a source block needs translation. Compare the complete normalized target-language tag when deciding whether an existing source map can be reused unchanged. When an explicit map or bundle is supplied without a target-language override, use the map's stored target language.
