# Media Notes schema

`notes.json` holds the Media Notes. Its structure records only who said something and where it came from; all content is plain text.

```json
{
  "units": [
    {
      "heading": "An informative heading",
      "paragraphs": [
        {
          "text": "Plain text. Line breaks are kept.",
          "speakers": ["SPK001"],
          "cites": ["S001", "S002"],
          "frames": ["F001"]
        }
      ]
    }
  ]
}
```

- `heading` and `text` are non-empty and written in the map's `target_language`. The Notes have no title: the page takes its title from `media.title`, along with source details such as duration and transcript provenance, so the Notes leave them out.
- The first unit is the orientation and has no `cites` or `frames`, since it summarizes the whole source. Every later unit needs at least one `cites` or `frames` entry across its paragraphs, and a single paragraph in it, such as an overview sentence, may have neither.
- `cites` lists single `S...` IDs, so write out consecutive blocks one by one. `frames` lists `F...` IDs to show beside the paragraph.
- `speakers` lists whose content a paragraph is. Give different views their own paragraphs, list several speakers only for a shared conclusion, and leave an overview without `speakers`. The page shows each label as the shared [speaker evidence contract](../../media-shared/media-source-map/core/source-map-contract.md#audio-and-speaker-evidence) defines, adding `?` to a speaker whose cited blocks are all uncertain. When a passage has no identifiable speaker, say so in the text.
- Text is plain prose with line breaks. Who said it lives in `speakers` and where it came from lives in `cites` and `frames`, so the text holds no names, timestamps, IDs, or markup, and a rename needs only another render.
- Write actions, steps, decisions, commands, and formulas in the text. State an owner or deadline only when the source does, and otherwise say it is unspecified. An owner who is a speaker goes in `speakers`, and the text says "the speaker"; an owner outside the recording is named in the text.
- A conclusion and the source boundary are ordinary units. Describe the practical effect of a missing passage or unresolved speaker, and cite the affected blocks.
- Units are the pyramid's next level down: each is one supporting point within a section. The page shows the Notes in one outline that its Contents repeat: the orientation first, then each map section as a heading with its units under it, then the closing units, such as next steps and the source boundary, on their own.
- Within the reading-type chain, prefer source order: the page places each unit at its earliest cited block at or after the previous unit's time, under that block's section. Put closing units last; a closing unit cites only earlier material or sections more than one apart, so the page keeps it out of any section.
