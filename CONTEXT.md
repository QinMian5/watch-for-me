---
abstract: Canonical glossary for source-grounded audio and video processing in Watch for Me.
out_of_scope: Requirements, implementation details, architecture decisions, tool configuration, and credentials.
---

# Watch for Me

## Language

**Media Source**:
An audio or video source selected for faithful reading and content-specific organization. Audio supplies spoken and other audible evidence; video may additionally supply visual evidence.
_Avoid_: Video as an umbrella term, Transcript

**Media Source Map**:
The canonical, time-grounded bilingual evidence representation of one Media Source, including source blocks, speaker attribution, sections, confidence, and limitations. Visual Evidence belongs to this same map when available. It comes with a generated text projection for agents to read; the JSON is authoritative.
_Avoid_: separate Audio Evidence Map and Media Source Map, Raw ASR, Reader

**Source Block**:
One paragraph of a Media Source Map: a paragraph within one speaker's turn, with its original text, translation, times, and stable `S...` ID, assembled from a contiguous range of Cues.
_Avoid_: segment, cue, subtitle line

**Cue**:
One numbered piece of normalized timed text from subtitles or ASR, with its time range and, when available, word times. Cues are working evidence for building Source Blocks; the map keeps only each block's first and last Cue.
_Avoid_: Source Block, caption line

**Media Reader**:
The complete readable view of a Media Source Map, deterministically projected from the map within a Media Page and preserving source order, timestamps, speaker attribution, original text, translations, uncertainty, and available Visual Evidence. It has no content of its own beyond the map. People see it as 「全文」 in Chinese and Transcript in the English interface; it is the reviewed map, not Raw ASR.
_Avoid_: media.md, authored transcript, Raw ASR, summary, audio-only transcript format, 逐字稿

**Media Notes**:
The structured, content-shaped organization of one Media Source, citing its Media Source Map only by stable block and frame IDs. Its structure follows the source's communicative form, including feedback and actions when supported by the source. People see it as 「笔记」 in Chinese and Notes in English. Each Media Source has one set of Media Notes, written in the map's target language.
_Avoid_: Media Card, Card, Summary, Card Spec, media-card.md, Media Record, Transcript, meeting-only template

**Media Page**:
The single rendered page of a Media Bundle, derived deterministically from its Media Source Map and Media Notes. It presents the Media Notes beside the Media Reader.
_Avoid_: reader.html, preview, report, authored HTML

**Media Bundle**:
The durable artifacts associated with one Media Source: its Media Source Map, its Media Notes, the outputs deterministically rendered from them (including the Media Page), and any retained Visual Evidence assets.
_Avoid_: separate Audio Bundle and Video Bundle, copied recording, raw ASR directory

**Visual Evidence**:
Source-grounded information carried by a video's images or visible changes, linked to the shared media timeline. Selected frames preserve visual information needed to understand or verify the source.
_Avoid_: required audio artifact, decorative screenshot

**Speaker Attribution**:
The assignment of spoken blocks to named or anonymous speakers by combining Acoustic Diarization, user-supplied identity context, and conversational evidence while preserving uncertainty and overlap.
_Avoid_: guaranteed speaker identity, speaker label

**Acoustic Diarization**:
Local analysis that segments a Media Source's audio by speaker and groups segments believed to come from the same voice. It distinguishes voices but does not by itself establish a person's identity or recover separate audio tracks from overlapping speech.
_Avoid_: transcription, Speaker Attribution, voice identification

**Reading Type**:
The communicative form used to organize media content: dialogic, expository, procedural, reportorial, or reflective. A source has a dominant Reading Type, while a substantial section may use another.
_Avoid_: audio format, media kind, file type

**Media Transcription**:
The preparation of a Media Source's timed evidence for Media Source Map construction: prepared audio, local ASR when no usable timed text exists, Cues normalized from subtitles or ASR, and Acoustic Diarization aligned to those Cues.
_Avoid_: Media Source Map, Media Reader, Media Notes
