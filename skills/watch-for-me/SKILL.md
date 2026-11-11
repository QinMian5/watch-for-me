---
name: watch-for-me
description: Watch local audio, local video, online video, or a Media Bundle for the user, turning it into a complete timestamped bilingual transcript and source-linked notes on one offline page. Use for transcripts, translations, summaries, meeting feedback and action items, lectures and study guides, demonstrations, reports, and voice notes; also for source-linked questions, requested excerpts, and speaker renames, including a prompt copied from the page.
metadata:
  version: "1.0.0"
---

# Watch for Me

Watch for Me turns one recording into a Media Bundle. Its page, `media.html`, shows the Notes, written to `notes.json` and organized by how the source develops its content, beside the complete Reader, which the shared render command projects from the Media Source Map. Every Notes unit after the orientation cites the map's blocks and frames.

- **A recording or bundle to watch**: follow the workflow below.
- **Question or excerpt**: follow the [grounding rules](../media-shared/references/grounding-rules.md) at the requested scope.
- **Speaker rename**, including a prompt copied from the page: follow [renaming speakers](../media-shared/media-render/references/renaming-speakers.md).

On follow-ups, reuse established choices and loaded guidance; load more only when the scope changes.

## Workflow

### 1. Load the core

Read [manifest.yaml](manifest.yaml), then read every file listed under `always_load` in order.

### 2. Ensure a Media Source Map

Load the `media-source-map` module of [Media Shared](../media-shared/SKILL.md). State the selected route in one short line: validated map, translation refresh, or new build. Continue with the returned `MEDIA_DIR` and `SOURCE_MAP_PATH`.

### 3. Select the lens and references

Select the primary and any secondary reading-type fragment by the `reading_type` axis in [manifest.yaml](manifest.yaml), and load each `references.on_demand` entry whose condition applies.

### 4. Review the Reader, then write the Notes

Follow the workflow (`static/core/workflow.md`) through the selected lens: the Reader first, then the Notes.
