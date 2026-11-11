# Output contract

A finished run leaves this Media Bundle:

```text
<media-name>/
├── source_map.json
├── notes.json
├── source_map.md
├── media.html
└── assets/frames/     # only when the map contains video frames
```

The agent writes `source_map.json` and `notes.json`; `source_map.md` and `media.html` are generated and disposable. The page opens on the Notes beside the Reader.

## Verification

The render command exits `0`, so every `cites`, `frames`, and `speakers` ID exists and every Notes unit after the orientation has evidence. Each warning is handled as the [render contract](../../../media-shared/media-render/core/render-contract.md) describes. Rendering guarantees coverage, order, exact text, times, and label consistency; meaning is what this review checks.

### Reader

Confirm against the map:

- Speaker labels reflect the map's final contextual decisions, as readable names or stable anonymous labels.
- Paragraphs follow natural turns with readable punctuation, and recoverable interjections stand as their own turns.
- Translations are faithful and render each recurring term the same way.
- Coverage and meaning-critical limitations agree with the source, and diagnostic evidence stays in the map.

### Notes

Confirm:

- The orientation and units cover the central content of the whole available map.
- The selected lens shapes the structure: educational material teaches coherently, and other material keeps its own purpose. Every included field earns its place.
- Central concepts, reasoning, procedures, examples, and qualifications are explained well enough to understand from the Notes alone.
- Each substantive paragraph cites the blocks that actually support it.
- In dialogic material, speakers and positions stay distinct, and so do feedback, decisions, suggestions, and commitments. Action owners and deadlines come from the source or are marked unspecified; an owner who is a speaker is in `speakers`.
- In tutorials and demonstrations, the order of steps, the reasons for important actions, and visible success states survive.
- Uncertainty, disagreement, and source limitations stay visible where they affect interpretation.

A source limitation bounds the bundle: record the affected range in the map, and complete the Reader and the Notes for the coverage that is available.

## Delivery

Name `media.html` for people and `source_map.md` for agents. Report a browser check only when you opened the page in a browser; otherwise say the page was not checked in one.
