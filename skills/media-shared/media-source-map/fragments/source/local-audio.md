# Source: local audio

Resolve the supplied recording or locally accessible attachment to an unchanged absolute path. Identify it from user context, container metadata, or its filename. Treat names, dates, expected speakers, and role hints as supplied context for attribution.

Pass the input to common preparation for audio probing and measured duration. Discover matching original-language timed-text sidecars when present; otherwise use the shared Whisper route. Audio requires no visual stream. Preserve the original file in place; converted audio stays in `WORK_DIR`.
