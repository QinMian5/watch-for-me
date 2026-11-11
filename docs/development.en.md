# Development and tests

[中文](development.md) | English · [Back to README](../README.en.md)

## Layout

The two public skills load shared resources from `media-shared`. All required resources are under `skills/`, following [Nature's shared-package layout](https://github.com/Yuan1z0825/nature-skills/tree/main/skills/nature-shared):

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

Install all three sibling directories together, including when copying skills into a project's `.agents/skills/`. `media-shared` supplies the other skills' dependencies and is not intended for direct use. Its `media-source-map` module builds the shared evidence; `media-transcription` prepares audio, runs local transcription and speaker detection, and aligns their timestamps; `media-render` validates a bundle and generates its reading copy and page. Each skill loads its manifest and common instructions, then the references needed for the current task. Visual review applies to video; the content type used to organize the notes is independent of file format.

## Run the tests

Tests live in the repository-root `tests/` and are not installed with the skills. `pyproject.toml` defines the development environment, managed with uv:

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

ty and ruff check against Python 3.12: the skill scripts run in the runtimes setup prepares, and the lowest pinned one is 3.12. torch, pyannote, faster-whisper, and huggingface_hub live in the separate environments setup prepares, not in the development environment.

These tests check validation, adapters, rendering, and whether the installed skills can reach their dependencies. They do not download models or measure transcription and speaker detection quality. They also do not drive a browser: page interaction is checked by hand against the [Media Page acceptance list](../tests/media-render/page-acceptance.md). Setup checks the actual runtimes; processing a recording requires checking coverage, translation, and speaker attribution against that source.
