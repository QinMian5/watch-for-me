# 开发与测试

中文 | [English](development.en.md) · [返回 README](../README.md)

## 目录结构

两个对外的 skill 从 `media-shared` 加载共用资源。所有需要的资源都在 `skills/` 下，沿用 [Nature 的共享包布局](https://github.com/Yuan1z0825/nature-skills/tree/main/skills/nature-shared)：

```text
skills/
├── setup-watch-for-me/
├── watch-for-me/
└── media-shared/
    ├── SKILL.md
    ├── manifest.yaml
    ├── agents/openai.yaml
    ├── media-source-map/
    ├── media-transcription/
    ├── media-render/
    └── references/
```

三个同级目录要一起安装，复制到项目的 `.agents/skills/` 时也一样。`media-shared` 提供另外两个 skill 的依赖，不单独使用。它的 `media-source-map` 模块构建共用的原文底稿（Media Source Map）；`media-transcription` 准备音频、在本地跑转写和说话人识别，并对齐时间戳；`media-render` 校验输出文件夹（Media Bundle），生成阅读副本和阅读页（Media Page）。每个 skill 先加载自己的 manifest 和通用说明，再按当前任务加载需要的参考文档。关键帧（Visual Evidence）的检查只针对视频；笔记按哪种内容类型（Reading Type）组织，和文件格式无关。

## 运行测试

测试放在仓库根目录的 `tests/` 下，不随 skill 安装。开发环境由 `pyproject.toml` 定义，用 uv 管理：

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python -m unittest discover -s tests/media-source-map
uv run python -m unittest discover -s tests/media-transcription
uv run python -m unittest discover -s tests/media-render
uv run python -m unittest discover -s tests/setup-watch-for-me
uv run python -m unittest discover -s tests/installation
```

ty 和 ruff 按 Python 3.12 检查：skill 脚本在 setup 准备的运行环境里执行，其中固定的最低版本是 3.12。torch、pyannote、faster-whisper 和 huggingface_hub 装在 setup 准备的独立环境里，不在开发环境中。

这些测试检查校验、适配器、渲染，以及装好的 skill 能否找到依赖。它们不下载模型，也不衡量转写和说话人识别的质量。它们同样不驱动浏览器：页面交互要对照 [阅读页验收清单](../tests/media-render/page-acceptance.md)（英文）手动检查。setup 会检查实际的运行环境；处理一个录音时，覆盖范围、翻译和说话人归属要对照原始来源核对。
