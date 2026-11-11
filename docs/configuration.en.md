# Configuration

[中文](configuration.md) | English · [Back to README](../README.en.md)

Run `setup-watch-for-me` again to change the language, output location, quality, or device profile. Settings supplied in your request override repository settings, which override user settings.

| Scope | Configuration file |
| --- | --- |
| User, macOS/Linux | `${XDG_CONFIG_HOME:-$HOME/.config}/watch-for-me/config.yaml` |
| User, Windows | `%APPDATA%\watch-for-me\config.yaml` |
| Repository | `.config/watch-for-me/config.yaml` at the repository root |

Repository settings contain machine-specific paths and devices. Setup excludes that exact file through the repository's local Git exclusions. A relative repository `output_root` is resolved from the repository root; a relative user `output_root` is resolved from the working directory.

<details>
<summary>Example configuration for NVIDIA CUDA</summary>

This example shows the file format. Setup records the paths and devices verified on your machine; the `/absolute/...` paths below are placeholders.

```yaml
schema_version: 2
target_language: zh-CN
output_root: media
cookie_browser: null
asr:
  backend: faster-whisper
  quality: balanced
  model: large-v3-turbo
  model_cache: /absolute/cache/watch-for-me/faster-whisper/large-v3-turbo
  device: cuda
  compute_type: float16
diarization:
  backend: pyannote.audio
  executable: /absolute/data/watch-for-me/pyannote/runtime/bin/python
  model: /absolute/data/watch-for-me/pyannote/community-1
  revision: 3533c8cf8e369892e6b79ff1bf80f7b0286a54ee
  device: cuda
```

See the [configuration reference](../skills/setup-watch-for-me/static/core/config.md) for backend-specific fields and profiles.

</details>
