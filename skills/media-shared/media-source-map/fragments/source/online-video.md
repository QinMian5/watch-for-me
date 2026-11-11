# Source: online video

The user provided one online video URL that `yt-dlp` can inspect.

- Preserve the original URL as the source identity and keep downloads in the task-owned workspace.
- Set `COOKIE_BROWSER` from the resolved `cookie_browser` configuration. Cookie data remains in the selected browser profile.
- Run `yt-dlp` with its `default` extra, which supplies the YouTube challenge solver, and with Node.js as the JavaScript runtime that executes it.
- Read the source title before resolving the task paths:

```bash
uvx --from "yt-dlp[default]" yt-dlp --js-runtimes node \
  --cookies-from-browser "$COOKIE_BROWSER" --no-playlist --print "%(title)s" "$URL"
```

- Save the full metadata in `WORK_DIR` and read its summary:

```bash
uvx --from "yt-dlp[default]" yt-dlp --js-runtimes node \
  --cookies-from-browser "$COOKIE_BROWSER" --no-playlist --dump-single-json "$URL" > "$WORK_DIR/source.json"
uv run --no-project -- python "$SOURCE_MAP_ROOT/scripts/summarize_online_source.py" "$WORK_DIR/source.json"
```

- The summary gives title, stable extractor ID, duration, license, chapters, original-language subtitle candidates, and original-audio and video formats, with manual subtitles and automatic captions kept distinct. It leaves out URLs, translated tracks, dubbed audio, and storyboards, and counts what it left out. When the source language is unknown, it keeps every candidate. `source.json` keeps the full inventory until task cleanup; query a specific field from it when the summary is not enough, and never print the whole file.
- When common source preparation selects a manual subtitle, download its exact language tag:

```bash
uvx --from "yt-dlp[default]" yt-dlp --js-runtimes node \
  --cookies-from-browser "$COOKIE_BROWSER" --no-playlist -q --no-progress --skip-download \
  --write-subs --sub-langs "$LANGUAGE_TAG" --sub-format "vtt/srt/best" \
  -o "$WORK_DIR/source.%(id)s.%(ext)s" "$URL"
```

- When it selects an automatic caption, download that candidate separately:

```bash
uvx --from "yt-dlp[default]" yt-dlp --js-runtimes node \
  --cookies-from-browser "$COOKIE_BROWSER" --no-playlist -q --no-progress --skip-download \
  --write-auto-subs --sub-langs "$LANGUAGE_TAG" --sub-format "vtt/srt/best" \
  -o "$WORK_DIR/source.%(id)s.%(ext)s" "$URL"
```

- The subtitle lands at `$WORK_DIR/source.<id>.<LANGUAGE_TAG>.<ext>`.
- Materialize the selected visual format by ID. The command prints only the downloaded path, plus any warnings or errors:

```bash
uvx --from "yt-dlp[default]" yt-dlp --js-runtimes node \
  --cookies-from-browser "$COOKIE_BROWSER" --no-playlist -q --no-progress \
  --print after_move:filepath -f "$VIDEO_FORMAT_ID" \
  -o "$WORK_DIR/visual.%(format_id)s.%(ext)s" "$URL"
```

- When separate audio is required, materialize its selected format by ID:

```bash
uvx --from "yt-dlp[default]" yt-dlp --js-runtimes node \
  --cookies-from-browser "$COOKIE_BROWSER" --no-playlist -q --no-progress \
  --print after_move:filepath -f "$AUDIO_FORMAT_ID" \
  -o "$WORK_DIR/audio.%(format_id)s.%(ext)s" "$URL"
```

- If a selected media format fails, choose another suitable format from the summary and record the fallback.
