# Media Source Map contract

`source_map.json` is the canonical bilingual, time-grounded representation of one audio or video source. The Reader and the Notes read it as it is; presentation belongs to the renderer. `source_map.md` is a generated reading copy of this file for agents; the JSON is authoritative.

Use this shape:

```json
{
  "media": {
    "kind": "video",
    "title": "Example video",
    "source_type": "online-video",
    "origin": "https://example.com/video",
    "source_id": "example-video",
    "duration_seconds": 67,
    "spoken_languages": ["en"],
    "target_language": "zh-CN",
    "reading_type": "expository",
    "transcript_provenance": "platform-manual",
    "asr": null
  },
  "speakers": [],
  "speaker_turns": [],
  "diarization": null,
  "sections": [
    {
      "title_original": "Introduction",
      "title_translation": "介绍",
      "reading_type": "expository",
      "start": "00:00:00",
      "end": "00:01:07",
      "block_ids": ["S001"]
    }
  ],
  "blocks": [
    {
      "id": "S001",
      "order": 1,
      "start": "00:00:01",
      "end": "00:01:07",
      "speaker": null,
      "speaker_candidates": [],
      "speaker_confidence": "unknown",
      "overlap": false,
      "attribution_note": null,
      "language": "en",
      "original_text": "Example source text.",
      "translation": "示例原文。",
      "confidence": "high",
      "source_cues": ["C0001", "C0004"]
    }
  ],
  "frames": [
    {
      "id": "F001",
      "timestamp": "00:00:30",
      "image_path": "assets/frames/00-00-30-000.webp",
      "related_blocks": ["S001"]
    }
  ],
  "limitations": [
    {
      "kind": "coverage",
      "start": "00:00:40",
      "end": "00:00:52",
      "detail": "录音在此中断，这段内容缺失。"
    }
  ]
}
```

When ASR supplies the transcript, `media.asr` records backend, quality, model, device, compute type, detected language, and reported decoding parameters.

Use this ASR shape:

```json
{
  "backend": "faster-whisper",
  "quality": "balanced",
  "model": "large-v3-turbo",
  "device": "cuda",
  "compute_type": "float16",
  "detected_language": "en",
  "parameters": {
    "beam_size": 5,
    "vad_filter": true
  }
}
```

Set `translation` and `title_translation` to a faithful `target_language` translation when normalized primary language subtags differ; use `null` when they match. The complete normalized target-language tag is part of map identity for reuse.

Keep `S...` and `F...` IDs stable. The number in a block's `S...` ID increases strictly with `order`, and gaps are allowed. Store frame relationships once under `frames[].related_blocks`. The renderer decides where a frame appears on the page.

`source_cues` names the first and last normalized cue a block was assembled from. Cue IDs come from `normalize_timed_text.py`, which numbers the same timed-text input the same way every time, so a block can be traced back by normalizing the recorded subtitle or ASR output again; the cue file itself is not kept. Adjacent blocks may share one boundary cue when a block starts inside it. Give every block `source_cues` or none; maps built before the field existed omit it.

Asset paths are relative to `MEDIA_DIR`. Represent incomplete or uncertain coverage in `limitations` and at the affected block through `confidence`. A limitation's `kind` is `coverage`, `transcript`, `translation`, `visual`, `speaker`, or `overlap`; `start` and `end` are null when it applies to the whole source; `detail` is written in `target_language`.

Build the map with `scripts/assemble_source_map.py` as `references/assembly.md` describes, rather than writing this JSON by hand; later corrections edit its values in place. The Pydantic validator at `scripts/validate_source_map.py` is the executable definition of this structural format. Update this contract and its Pydantic models together when the format evolves.

## Timestamp presentation

Keep source timestamps, duration, and acoustic boundaries at their available precision in `source_map.json`. The Media Page shows times as `mm:ss` for a source shorter than one hour and `hh:mm:ss` otherwise. `source_map.md` uses `HH:MM:SS`. Both drop fractional seconds without rounding, so `00:01:23.987` becomes `01:23` on the page and `00:01:23` in the reading copy. A subsecond range may show the same second at both ends; retain its block and stable ID. Frame asset paths and machine-readable timing data remain unchanged.

## Audio and speaker evidence

Use `media.kind: audio` and `source_type: local-audio` for a local audio recording, with `frames: []`. Video uses `kind: video` and `local-video` or `online-video`. Reading Type is independently `dialogic`, `expository`, `procedural`, `reportorial`, or `reflective`, at source and section level. A verified no-speech source uses `transcript_provenance: no-speech` and describes its coverage, with no speech blocks.

Each `speakers` entry has only a stable `id` such as `SPK001` and a nullable `name`. When a role-style address is needed, write it into `name`. Block `speaker` stores the final best-supported ID after acoustic and contextual analysis; null is reserved for speech that remains unattributable. Keep acoustic IDs, candidates, `speaker_confidence`, `attribution_note`, `overlap`, and coverage reasoning in the source map as internal review evidence, independently of transcription confidence. Use that evidence to identify any source limitation that affects meaning.

The rendered label is `name`, then the anonymous "Speaker N" numbered among unnamed speakers in table order, then "Unidentified" for a null block `speaker`. A block whose `speaker_confidence` is `low`, or `unknown` on an assigned speaker, shows `Name?`. These labels follow the interface language of `target_language`.

`speaker_turns` stores verified regular acoustic turns as `{speaker, start, end}`. Different speakers may overlap. Retain this evidence after raw diarization files are removed. `diarization` records `backend: pyannote.audio`, local `model`, pinned `revision`, verified `device`, `speaker_count`, prepared `audio_sha256`, and the actual integer `parameters` passed to the pipeline. A supplied single-speaker identity without a model run has null diarization.

Acoustic turns are time-ordered. Multiple speakers and retained acoustic turns require diarization metadata. An assigned block must intersect that voice's turns. If those turns cover less than 80% of the block duration, record the acoustic and contextual basis for the decision in `attribution_note`, such as a checked pause, boundary, or continuation of the same reply. The threshold triggers review rather than rejecting a supported assignment; the note records the analysis actually performed.

Preserve source order and all substantive content; the workflow's semantic checks establish completeness, attribution, and translation quality.
