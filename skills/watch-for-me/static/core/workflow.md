# Workflow

## 1. Render

Render `MEDIA_DIR` with the `media-render` module of [Media Shared](../../../media-shared/SKILL.md). Fix any error it reports.

## 2. Read the whole map

Read `source_map.md` in full: source identity, speakers, limitations, and the complete spoken text in order. Consult `source_map.json` for translations, frames, and limitation details. The map's limitations are the source boundary: describe the coverage that is available and judge completeness within it.

## 3. Review the Reader against the map

Check each **Reader** item under **Verification** in the [output contract](output-contract.md). Correct any problem in `source_map.json` and render again.

## 4. Inventory the content

Through the selected Reading Type, list what the Notes must carry:

- the source's purpose: its central question or practical task
- definitions, and which ideas depend on which
- the main concepts, arguments, steps, positions, or events, with the reasoning that links them
- the examples, numbers, commands, and settings a reader needs to understand or apply the material
- qualifications, disagreements, and open questions
- attributed feedback, decisions, proposed actions, and commitments, when present
- frames that carry information or make the structure clearer
- the `S...` and `F...` anchors for each unit

## 5. Design the organizing path

Open with a short orientation: the source's purpose and how the material fits together. Educational material states its learning outcome; other material states its purpose in its own terms. The orientation is the first unit and cites nothing; the units after it carry the evidence.

Order the units along the chain in the selected reading-type fragment, so each unit builds on the ones before it. In each unit, state the point, explain the reasoning, give the source's example or evidence, keep the conditions that change how it applies, and cite the supporting blocks.

Give foundational and difficult ideas room to be followed; keep simple or repeated material brief.

Close with what the source supports: its conclusions, decision implications, stated next steps, or remaining questions. Educational material may connect the main ideas into a usable mental model; a reflection may end on tentative understanding.

## 6. Select shared frames

When `source_map.json.frames` is non-empty, choose the smallest subset that supports the organizing path, the examples, and visible state changes. Keep IDs and asset paths as they are.

## 7. Write and verify the Notes

Write `MEDIA_DIR/notes.json` by the [Notes schema](../../references/notes-schema.md) in the map's `target_language`. The turn headers in `source_map.md` give only ID ranges, so after drafting, check `source_map.json` and list the single block IDs each paragraph actually relies on. Render as the [render contract](../../../media-shared/media-render/core/render-contract.md) describes, handle every diagnostic, and check each **Notes** item in the output contract.

## 8. Deliver

Report `media.html` and `source_map.md`, along with the limitations that affect understanding, as the output contract describes.
