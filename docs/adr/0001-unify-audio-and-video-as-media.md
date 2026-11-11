---
status: accepted
---

# Unify audio and video as media

Audio and video share a Media Source Map, readable output format, content-type routing, configuration, and output root. The shared workflow owns audio preparation, local transcription, acoustic diarization, speaker attribution, semantic blocks, translation, and evidence validation; video additionally activates visual review and frame evidence within the same timeline and bundle.

The initially considered audio-specific evidence map would duplicate most of the existing video workflow and allow their contracts to drift. Media kind therefore selects applicable evidence capabilities, while Reading Type independently selects how content is organized. Audio sources do not require frames; video sources retain full visual-coverage review, including an explicit explanation when no useful frames are retained.

The plugin and marketplace use the `media-skills` identity. The public capabilities are `setup-media-skills`, `media-reader`, and `media-card`; a general organization request composes Reader and Card over the same map. _Superseded by [ADR-0004](0004-rename-to-watch-for-me.md): the identity is now `watch-for-me`, and the public skills are `setup-watch-for-me` and `watch-for-me`._

The Skills use the current Media names and schema. They do not provide old-name aliases, legacy configuration fallback, or adapters for historical bundles. A structural rename preserves existing content without retranscribing it.
