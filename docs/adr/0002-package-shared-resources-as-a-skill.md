---
status: accepted
---

# Package shared resources beside public Skills

The owner requested Nature's `skills/nature-shared` layout for Media. Place all shared resources in `skills/media-shared/`, with an internal support `SKILL.md`, an on-demand manifest, and `agents/openai.yaml` disabling implicit standalone invocation. The package is a dependency of `media-reader`, `media-card`, and `setup-media-skills`, not another user-facing workflow. (Since [ADR-0004](0004-rename-to-watch-for-me.md), those are `watch-for-me` and `setup-watch-for-me`, deployed as three sibling directories.)

The source-map and transcription modules retain their separate manifests, references, scripts, and tests within this package. Public routers reach the package through sibling-relative links; commands bind absolute resource roots from the installed files. This makes a skills-only deployment self-contained without changing the output schema, local model paths, or audio/video processing responsibilities.

llm-wiki deploys the same four sibling directories under `.agents/skills/`. Packaging tests copy only those directories to an unrelated temporary location, resolve every manifest route and entry-point link, and launch the bundled command interfaces from outside the installation.

The reference is [Nature Shared at revision 9ea7330](https://github.com/Yuan1z0825/nature-skills/tree/9ea7330a17813a15421fe843778a776c258b9001/skills/nature-shared), inspected on 2026-09-14. This adopts its dependency packaging and selective loading, not its journal-specific content or workflow.
