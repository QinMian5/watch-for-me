# Media Render contract

Two commands project a Media Bundle. Agents write only `source_map.json` and `notes.json`, and every change reaches the generated files through one of these commands.

Bind `MEDIA_RENDER_ROOT` to the absolute path of this module's directory, the one holding its `manifest.yaml`.

## Reading copy

`write_reader_copy.py` needs only `source_map.json`. It validates the map and writes `source_map.md`, the reading copy agents read before and while they write the Notes.

```bash
uv run --no-project --with pydantic -- python \
  "$MEDIA_RENDER_ROOT/scripts/write_reader_copy.py" "$MEDIA_DIR" [--check]
```

Write it whenever the map changes before the Notes exist, such as after a map is published or edited by hand, and before reading `source_map.md`.

## Render

`render_bundle.py` renders a complete bundle. It requires both `source_map.json` and `notes.json`, and fails with `input/unreadable notes.json` when the Notes are missing. Render only once the Notes are written.

```bash
uv run --no-project --with pydantic -- python \
  "$MEDIA_RENDER_ROOT/scripts/render_bundle.py" "$MEDIA_DIR" [--check]
```

The command validates both files, then writes `source_map.md` and `media.html`. The page's `<title>` and heading are `media.title` from the map; the Notes have no title.

## Exit codes and `--check`

Both commands share these exit codes: `0` success, possibly with warnings; `1` validation, recheck, write, or internal failure, or a stale file under `--check`; `2` bad arguments. A validation or recheck error leaves the existing generated files as they were. After `commit/write-failed` the files may disagree; fix the cause and run again, and `--check` reports any file left stale.

`--check` runs the same pipeline without writing and reports `stale/<file>` when a generated file differs from what the inputs produce. Use it to review a bundle. While drafting, run the plain command.

## Reading diagnostics

Each diagnostic is one line of plain text on stdout:

```text
severity code file path [ID]：message。改法：fix
```

`改法` is the suggested fix, and it is absent when there is none. Code prefixes are `input/`, `map/`, `notes/`, `artifact/`, `stale/`, `commit/`, and `internal/unclassified`. A successful run ends with a receipt listing the bytes and SHA-256 prefix of each input and output. The receipt describes files; a browser check means opening the page in a browser.

## When to render

- Render after every change to the map or the Notes once the Notes exist, including a speaker rename.
- A translation refresh changes the map's language, so the Notes are rewritten first; render after that.

## Fixing problems

- Fix only the location a diagnostic names, then run the same command again.
- If the error count has not dropped after two consecutive rounds, stop and report the remaining errors.
- Address each warning by editing the Notes or map, or by stating at delivery why it stays. Warnings do not block rendering.
