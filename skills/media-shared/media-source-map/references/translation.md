# Source-map translation

Translate all Source Blocks and section titles into the resolved `target_language`. Translate each one whose normalized primary language subtag differs from the target's; leave the others untranslated. For each translation:

- give one faithful target-language rendering of the original
- preserve names, technical terms, numbers, units, emphasis, qualification, evidence relationships, and uncertainty
- keep section, block, and sentence order aligned with the source
- translate recurring terms, names, and abbreviations consistently throughout the source

Write the translations to `translations.json` as `references/assembly.md` describes. The map stores the complete normalized target-language tag. A change to that tag refreshes section-title and block translations with the `translate` command while preserving source anchors and frame assets.
