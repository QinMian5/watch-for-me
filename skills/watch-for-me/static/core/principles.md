# Principles

The render command projects every source block and frame once, in order, with its stored text and times. The agent's work is what a tool cannot judge: whether the map's paragraphs, translations, and speaker decisions are faithful to the source, and whether the Notes carry its content and reasoning.

## Reader

- Fix every problem by editing values in `source_map.json` in place: text, translation, speaker and its evidence, confidence, and limitations. Block boundaries and IDs stay as published. Write the reading copy again after each fix.
- Keep `S...` and `F...` IDs stable, so links, Notes citations, and follow-up questions keep working.
- Record gaps and passages whose meaning stays unclear in `limitations`, where the page shows them, grouping recurring ones together.
- Speaker labels follow the shared [speaker evidence contract](../../../media-shared/media-source-map/core/source-map-contract.md#audio-and-speaker-evidence).

A finished Reader lets a person understand the complete spoken content without replaying the recording, place each passage on the timeline, inspect the visuals that aid understanding, and return to stable source blocks in follow-up questions.

## Notes

The Notes let a reader understand the source's central content and reasoning without replaying it, tell participants' views apart where they matter, and follow each consequential claim, step, or decision back to its evidence. The selected Reading Type shapes the structure.

- Write in the map's target language, using its stored translations.
- Carry the reasoning, qualifications, uncertainty, and details that control understanding or application. Compress greetings, repetition, transitions, and filler.
- Ground every substantive paragraph in the blocks that support it, through the fields in the [Notes schema](../../references/notes-schema.md).
- Keep the Notes to the source. Agent analysis and external content go in the conversation.
- Learning goals belong to educational material; conversations, reports, and reflections keep their own purpose.

Choose frames that clarify structure, comparison, state, action, or evidence, and list each on the first paragraph it supports. Frames have no captions, so write text that stands without one.

## Reproduced content

Keep reproduced content in the local artifact, for the user's own source or clearly lawful content. In chat, quote briefly and point to the artifact.
