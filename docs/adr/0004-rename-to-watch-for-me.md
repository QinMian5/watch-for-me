---
status: accepted
---

# Rename to Watch for Me and merge the public entry skill

The product, GitHub repository (`QinMian5/media-skills` → `QinMian5/watch-for-me`), plugin, marketplace, and entry skill are all named `watch-for-me`, displayed as Watch for Me. The public skills are `watch-for-me` and `setup-watch-for-me`; `media-shared` stays an internal dependency package. `media-reader` and `media-card` merge into `watch-for-me`, which runs one workflow: the complete Reader first, then the Notes. Source-linked questions, requested excerpts, and speaker renames, including a prompt copied from the page, belong to the same skill.

Media Card becomes Media Notes: `card.json` becomes `notes.json`, the `card/` diagnostic prefix becomes `notes/`, and the page labels the view 「笔记」 in Chinese and Notes in English instead of 「总结」 and Summary. Media Reader keeps its name as a view of the page, shown as 「全文」 and Transcript. Configuration moves from `media-skills/` to `watch-for-me/` in the user and repository locations, and so do the default model and runtime locations that setup proposes. Media-prefixed domain terms (Media Source, Media Source Map, Media Page, Media Bundle), `media-shared`, `media.html`, the `media` output root, and `MEDIA_SHARED_ROOT` keep their names, because they describe the media rather than the product.

## Why

The name says what the product does for a person: the agent watches the recording for you (「替你看完」). The owner wanted one human-facing entry in which transcription and notes are no longer separate; with one workflow, a person no longer chooses between a Reader skill and a Card skill. Notes matches 「笔记」, the Chinese term already chosen for people, where Card had no natural reading.

## Considered options

- **Keep Media Skills.** Accurate but generic, and another repository already uses `media-skills`; this repository was not in the first ten GitHub results for that name.
- **Require a globally unique name.** Collision checks covered GitHub, npm, PyPI, and the skill directories, but uniqueness ranks below a name that expresses the purpose.
- **Keep two public skills with explicit modes** ("transcript only", "notes only"). Every mode adds routing text to the skill and the README for a distinction people seldom need.

## Consequences

`usedeepmark/watch-for-me` is an existing project with the same name and a similar purpose. The owner accepts the shared name; promotion uses `QinMian5/watch-for-me` as the search term, which returns only this repository.

Installed users are not migrated: there are no old skill names, no configuration fallback to `media-skills/`, and no reading of an old `card.json`, extending ADR-0001's no-adapter decision. GitHub redirects the old repository address after the rename, as long as no new repository named `media-skills` is created under the same owner. GitHub Pages project sites do not redirect, so example output is published after the rename.

This supersedes ADR-0001's paragraph on plugin identity and public capabilities, and renames ADR-0003's `card.json` to `notes.json`.
