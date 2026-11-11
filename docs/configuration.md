# 配置

中文 | [English](configuration.en.md) · [返回 README](../README.md)

想改语言、输出位置、转写质量或设备配置，再运行一次 `setup-watch-for-me`。请求里给的设置优先于仓库设置，仓库设置优先于用户设置。

| 范围 | 配置文件 |
| --- | --- |
| 用户，macOS/Linux | `${XDG_CONFIG_HOME:-$HOME/.config}/watch-for-me/config.yaml` |
| 用户，Windows | `%APPDATA%\watch-for-me\config.yaml` |
| 仓库 | 仓库根目录下的 `.config/watch-for-me/config.yaml` |

仓库设置里有本机专用的路径和设备，setup 会把这个文件加进仓库的本地 Git 排除列表。仓库设置里相对路径的 `output_root` 从仓库根目录算起；用户设置里相对路径的 `output_root` 从当前工作目录算起。

<details>
<summary>NVIDIA CUDA 的配置示例</summary>

这个例子只用来展示文件格式。setup 会写入你机器上验证过的路径和设备；下面的 `/absolute/...` 路径是占位符。

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

各后端的字段和配置见 [配置参考](../skills/setup-watch-for-me/static/core/config.md)（英文）。

</details>
