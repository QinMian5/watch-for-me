# Output folder and reading page

[中文](output.md) | English · [Back to README](../README.en.md)

## Output folder

Watching a video or recording produces an output folder (a Media Bundle):

```text
media/<name>/
├── source_map.json
├── source_map.md     # generated reading copy for agents
├── notes.json        # the notes
├── media.html        # generated page, the one to open
└── assets/frames/    # when video supplies useful frames
```

The original recording stays in place. Converted audio, raw model outputs, and temporary extraction files are removed after the task completes or reports a failure. The folder keeps the source map, the notes, the rendered files, and selected frames.

## Reading page

Open `media.html` in a browser. It is a single file that works offline and needs no server. On a wide screen the notes and the full transcript sit side by side and scroll together; on a narrow screen they are tabs. A script generates both `media.html` and `source_map.md`, and the agent never writes them directly, so you can regenerate them at any time and should not edit them.

The transcript keeps the source order, with natural paragraphs, timestamps, and speaker names or stable anonymous labels. By default each original passage sits beside its translation, and you can switch to either language alone. When the source and target languages match, duplicate translations are omitted. Notes about unclear source material appear where they affect the meaning. You can search both views and filter by speaker.

When a video's images carry information needed to follow it, selected frames appear beside the matching passages and open large on click.

## Notes

Each notes paragraph links to the supporting passages in the transcript, and each passage links back. The structure follows the recording's content type:

| Content type | How the notes are organized |
| --- | --- |
| Conversation (`dialogic`) | Questions, positions, feedback, decisions, supported commitments |
| Explanation (`expository`) | Concepts, argument, mechanisms, examples, qualifications |
| Procedure (`procedural`) | Goal, prerequisites, actions, checks, corrections, result |
| Report (`reportorial`) | Context, chronology, sources, evidence, uncertainty |
| Reflection (`reflective`) | Experiences, interpretations, tensions, emerging intentions |

Educational sources include detailed learning guidance. Conversations keep speakers' views distinct and separate suggestions from commitments. If an action has no stated owner or deadline, the notes say so.

<details>
<summary>Source map, notes, and rendering</summary>

`source_map.json` stores source metadata, complete original and translated blocks, speaker evidence, sections, limitations, and any frames. The transcript and the notes use the same map, so writing the notes does not repeat transcription. A current map can be reused after source identity and language checks.

`notes.json` holds headings and plain-text paragraphs, each of which can list the speakers it belongs to, the `S...` blocks it cites, and the `F...` frames to show beside it. Detailed speaker diagnostics remain in the map.

`write_reader_copy.py` needs only the map and writes `source_map.md` before the notes exist. `render_bundle.py` runs once the notes are written: it validates both files and writes `source_map.md` and `media.html`, and fails when `notes.json` is missing. If validation fails, they report each problem's location and leave the existing files unchanged.

The page title is the map's `media.title`, the source's own title: the platform title for an online video, and for a local file the title you give, its metadata title, or its filename. The title stays as it is, neither translated nor rewritten.

</details>
