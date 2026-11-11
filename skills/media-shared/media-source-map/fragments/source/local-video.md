# Source: local video

The user provided one readable local video file.

- Resolve the unchanged absolute input path and use it as both the source identity and local visual media path.
- Identify matching `.vtt`, `.srt`, and `.ass` sidecars and retain their paths and available language information as timed-text candidates.
- Use container metadata or the filename as the available source title.
- Pass the input path and sidecar candidates into common source preparation. The common layer probes the media, inventories embedded subtitle streams, selects the transcript route, and reuses an embedded audio stream when ASR is required.
