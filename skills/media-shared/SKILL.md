---
name: media-shared
description: Shared source-map, transcription, and render modules that Watch for Me and Setup Watch for Me load by path.
disable-model-invocation: true
---

# Media Shared

The Watch for Me skills load this package by path. Bind `MEDIA_SHARED_ROOT` to the absolute directory containing this `SKILL.md`, so every module resolves from the installed package rather than the working directory.

Load the module the calling skill names: read its `manifest.yaml`, then its `always_load` files, then only the branches the task selects. When the module finishes, continue in the calling skill, which owns configuration changes, semantic review, and final QA.

- **media-source-map** ([manifest](media-source-map/manifest.yaml)) builds, validates, reuses, or translates one Media Source Map and returns `MEDIA_DIR`, `SOURCE_MAP_PATH`, and `SOURCE_MAP_ROOT`.
- **media-transcription** ([manifest](media-transcription/manifest.yaml)) prepares audio, runs local Whisper and acoustic diarization, and resolves speakers inside the caller's task-owned `WORK_DIR`. Source preparation and scoped source inspection call it.
- **media-render** ([manifest](media-render/manifest.yaml)) validates the bundle in the caller's `MEDIA_DIR`, writes the `source_map.md` reading copy from the map, and renders `media.html` once the Notes exist.

Watch for Me links two references here directly: [grounding rules](references/grounding-rules.md) for source-linked questions and requested excerpts, and [renaming speakers](media-render/references/renaming-speakers.md) for a rename, including a prompt copied from the page.

## Installation

Install this directory beside `watch-for-me` and `setup-watch-for-me`, so every module resolves inside the same `skills/` tree.
