# Media Render contract

`render_bundle.py` produces `source_map.md` and `media.html`. Agents write only `source_map.json` and `notes.json`, and every change reaches the rendered files through another render.

Bind `MEDIA_RENDER_ROOT` to the absolute path of this module's directory, the one holding its `manifest.yaml`.

```bash
uv run --no-project --with pydantic -- python \
  "$MEDIA_RENDER_ROOT/scripts/render_bundle.py" "$MEDIA_DIR" [--check]
```

The command validates `source_map.json` and `notes.json`, when present, in `MEDIA_DIR`, then writes `source_map.md` and `media.html`. Exit codes: `0` success, possibly with warnings; `1` validation, recheck, write, or internal failure, or a stale file under `--check`; `2` bad arguments. A validation or recheck error leaves the existing rendered files as they were. After `commit/write-failed` the two files may disagree; fix the cause and render again, and `--check` reports any file left stale.

`--check` runs the same pipeline without writing and reports `stale/<file>` when a rendered file differs from what the inputs produce. Use it to review a bundle. While drafting, run the plain command.

## Reading diagnostics

Each diagnostic is one line of plain text on stdout:

```text
severity code file path [ID]：message。改法：fix
```

`改法` is the suggested fix, and it is absent when there is none. Code prefixes are `input/`, `map/`, `notes/`, `artifact/`, `stale/`, `commit/`, and `internal/unclassified`. A successful run ends with a receipt listing the bytes and SHA-256 prefix of each input and output. The receipt describes files; a browser check means opening the page in a browser.

## When to render

- Render after every change to the map or the Notes, including a translation refresh and a speaker rename.
- Render before reading `source_map.md`, so the reading copy is always current.

## Fixing problems

- Fix only the location a diagnostic names, then render again.
- If the error count has not dropped after two consecutive rounds, stop and report the remaining errors.
- Address each warning by editing the Notes or map, or by stating at delivery why it stays. Warnings do not block rendering.
- A bundle from an earlier format fails with `map/unknown-field`; follow [older bundles](../../media-source-map/references/older-bundles.md).
