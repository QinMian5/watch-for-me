#!/usr/bin/env python3
"""Assemble a Media Source Map from assembled blocks, an agent-written structure, and translations.

The blocks come from `build_blocks.py assemble`, which fixes block IDs, times, cue ranges, and
the raw cue text, and its speaker from the block plan. The structure restores punctuation,
records evidence-backed word fixes and review decisions, and lists sections, frames, and
limitations. Everything else is copied.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_source_map import (
    CueId,
    Limitation,
    MediaMetadata,
    MediaSourceMap,
    ReadingType,
    SourceBlockId,
    SpeakerId,
    Timestamp,
    format_validation_error,
    timestamp_milliseconds,
)

Text = Annotated[str, Field(min_length=1)]
OVERSHOOT_MS = 100


class AssemblyError(Exception):
    pass


class PlanModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AssembledBlock(BaseModel):
    """One block as written by build_blocks.py assemble."""

    id: SourceBlockId
    order: int
    start: Timestamp
    end: Timestamp
    speaker: SpeakerId | None
    source_cues: Annotated[list[CueId], Field(min_length=2, max_length=2)]
    original_text: str


class SpeakerPlan(PlanModel):
    id: SpeakerId
    name: Text | None = None


class BlockPlan(PlanModel):
    id: SourceBlockId
    text: Text | None = None
    speaker_confidence: Literal["high", "medium", "low", "unknown"] | None = None
    speaker_candidates: list[SpeakerId] | None = None
    overlap: bool | None = None
    attribution_note: str | None = None
    language: str | None = None
    confidence: Literal["high", "medium", "low"] = "high"


class FixPlan(PlanModel):
    block: SourceBlockId
    find: Text
    replace: str
    reason: Text


class SectionPlan(PlanModel):
    title: Text
    blocks: Annotated[list[SourceBlockId], Field(min_length=2, max_length=2)]
    reading_type: ReadingType | None = None


class FramePlan(PlanModel):
    timestamp: Timestamp
    related_blocks: list[SourceBlockId]
    image_path: Text | None = None


class Structure(PlanModel):
    media: MediaMetadata
    speakers: list[SpeakerPlan] = []
    blocks: list[BlockPlan] = []
    fixes: list[FixPlan] = []
    sections: list[SectionPlan]
    frames: list[FramePlan] = []
    limitations: list[Limitation] = []


class Translations(PlanModel):
    blocks: dict[SourceBlockId, Text] = {}
    sections: dict[SourceBlockId, Text] = {}


BLOCKS = TypeAdapter(list[AssembledBlock])


def stamp(ms: int, sep: str = ":") -> str:
    seconds, fraction = divmod(ms, 1000)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    base = sep.join(f"{part:02d}" for part in (hours, minutes, seconds))
    if sep != ":":
        return f"{base}{sep}{fraction:03d}"
    return base if fraction == 0 else f"{base}.{fraction:03d}"


# Scripts written without spaces between words: each character is its own token.
UNSPACED = re.compile("[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def words(text: str) -> list[str]:
    """Word tokens ignoring case, punctuation, and apostrophes, keeping combining marks."""
    tokens, current = [], ""
    for char in re.sub("['\u2019]", "", text.lower()):
        if UNSPACED.match(char):
            tokens += [current, char] if current else [char]
            current = ""
        elif char.isalnum() or char == "_" or unicodedata.category(char).startswith("M"):
            current += char
        elif current:
            tokens.append(current)
            current = ""
    return [*tokens, current] if current else tokens


def primary(tag: str) -> str:
    return tag.lower().replace("_", "-").split("-")[0]


def cue_number(cue_id: str) -> int:
    return int(cue_id[1:])


def load_alignment(alignment: dict | None) -> dict[str, dict]:
    if alignment is None:
        return {}
    segments = alignment.get("segments", [])
    if any(not segment.get("cue") for segment in segments):
        raise AssemblyError("alignment: every segment needs a cue ID; align cues.json")
    return {segment["cue"]: segment for segment in segments}


def block_text(block: AssembledBlock, plan: BlockPlan | None) -> str:
    if plan is None or plan.text is None:
        return block.original_text
    if words(plan.text) != words(block.original_text):
        raise AssemblyError(
            f"block {block.id}: text may change only punctuation, case, and spacing; "
            "use a fix for word changes"
        )
    return plan.text


def apply_fixes(texts: dict[str, str], fixes: list[FixPlan]) -> None:
    for fix in fixes:
        if fix.block not in texts:
            raise AssemblyError(f"fix: unknown block {fix.block}")
        count = texts[fix.block].count(fix.find)
        if count != 1:
            raise AssemblyError(f"fix in {fix.block}: {fix.find!r} occurs {count} times, not once")
        texts[fix.block] = texts[fix.block].replace(fix.find, fix.replace)


def build_blocks(
    structure: Structure,
    assembled: list[AssembledBlock],
    aligned: dict[str, dict],
    sole_speaker: str | None,
) -> list[dict]:
    plans = {plan.id: plan for plan in structure.blocks}
    if len(plans) != len(structure.blocks):
        raise AssemblyError("structure.blocks: each block ID may appear once")
    unknown = set(plans) - {block.id for block in assembled}
    if unknown:
        raise AssemblyError(f"structure.blocks: unknown block IDs {sorted(unknown)}")
    texts = {block.id: block_text(block, plans.get(block.id)) for block in assembled}
    apply_fixes(texts, structure.fixes)
    language = structure.media.spoken_languages[0] if structure.media.spoken_languages else None
    duration_ms = round(structure.media.duration_seconds * 1000)
    blocks = []
    for block in assembled:
        plan = plans.get(block.id) or BlockPlan(id=block.id)
        first, last = (cue_number(cue) for cue in block.source_cues)
        evidence = [item for cue, item in aligned.items() if first <= cue_number(cue) <= last]
        speaker = block.speaker or sole_speaker
        # A decision the acoustic evidence does not settle needs its strength stated.
        unsettled = [
            item["cue"]
            for item in evidence
            if item.get("needs_review") or item.get("speaker_candidates", []) != [speaker]
        ]
        if unsettled and plan.speaker_confidence is None:
            raise AssemblyError(
                f"block {block.id}: {', '.join(unsettled)} need speaker review; "
                "give speaker_confidence, and attribution_note when context decided it"
            )
        candidates = sorted({c for item in evidence for c in item.get("speaker_candidates", [])})
        end = timestamp_milliseconds(block.end)
        if duration_ms < end <= duration_ms + OVERSHOOT_MS:
            end = duration_ms  # decoder overshoot is clamped to the measured duration
        if not texts[block.id].strip():
            raise AssemblyError(f"block {block.id}: text is empty after fixes")
        blocks.append(
            {
                "id": block.id,
                "order": block.order,
                "start": stamp(timestamp_milliseconds(block.start)),
                "end": stamp(end),
                "speaker": speaker,
                "speaker_candidates": plan.speaker_candidates
                if plan.speaker_candidates is not None
                else ([] if candidates == [speaker] else candidates),
                "speaker_confidence": plan.speaker_confidence or ("high" if speaker else "unknown"),
                "overlap": plan.overlap
                if plan.overlap is not None
                else any(item.get("overlap", False) for item in evidence),
                "attribution_note": plan.attribution_note,
                "language": plan.language or language,
                "original_text": texts[block.id],
                "translation": None,
                "confidence": plan.confidence,
                "source_cues": block.source_cues,
            }
        )
    return blocks


def build_sections(structure: Structure, blocks: list[dict]) -> list[dict]:
    index = {block["id"]: number for number, block in enumerate(blocks)}
    sections = []
    for plan in structure.sections:
        first, last = plan.blocks
        if first not in index or last not in index:
            raise AssemblyError(f"section {plan.title!r}: unknown block in {first}-{last}")
        members = blocks[index[first] : index[last] + 1]
        if not members:
            raise AssemblyError(f"section {plan.title!r}: block range {first}-{last} is reversed")
        sections.append(
            {
                "title_original": plan.title,
                "title_translation": None,
                "reading_type": plan.reading_type or structure.media.reading_type,
                "start": members[0]["start"],
                "end": stamp(max(timestamp_milliseconds(block["end"]) for block in members)),
                "block_ids": [block["id"] for block in members],
            }
        )
    return sections


def build_speakers(structure: Structure, diarization: dict | None) -> tuple[list, list, Any]:
    names = {plan.id: plan.name for plan in structure.speakers}
    if diarization is None:
        return [{"id": i, "name": n} for i, n in names.items()], [], None
    unknown = set(names) - set(diarization["speakers"])
    if unknown:
        raise AssemblyError(f"speakers: {sorted(unknown)} are not in the diarization")
    speakers = [{"id": i, "name": names.get(i)} for i in diarization["speakers"]]
    turns = [
        {
            "speaker": turn["speaker"],
            "start": stamp(round(turn["start"] * 1000)),
            "end": stamp(round(turn["end"] * 1000)),
        }
        for turn in diarization["turns"]
    ]
    keys = ("backend", "model", "revision", "device", "speaker_count", "audio_sha256", "parameters")
    return speakers, turns, {key: diarization[key] for key in keys}


def build_frames(structure: Structure) -> list[dict]:
    frames = []
    for number, plan in enumerate(structure.frames, 1):
        ms = timestamp_milliseconds(plan.timestamp)
        frames.append(
            {
                "id": f"F{number:03d}",
                "timestamp": plan.timestamp,
                "image_path": plan.image_path or f"assets/frames/{stamp(ms, '-')}.webp",
                "related_blocks": plan.related_blocks,
            }
        )
    times = [timestamp_milliseconds(plan.timestamp) for plan in structure.frames]
    if times != sorted(times):
        raise AssemblyError("frames must be listed in timeline order")
    return frames


def apply_translations(source_map: dict, translations: Translations) -> None:
    """Fill block and section-title translations, requiring exactly the needed keys."""
    target = primary(source_map["media"]["target_language"])
    blocks = {block["id"]: block for block in source_map["blocks"]}
    needed = {i for i, block in blocks.items() if primary(block["language"]) != target}
    titled = {section["block_ids"][0]: section for section in source_map["sections"]}
    # Section titles are written in the source's main language, whatever their first block is.
    spoken = source_map["media"]["spoken_languages"]
    needed_titles = {
        i for i in titled if primary(spoken[0] if spoken else blocks[i]["language"]) != target
    }
    for label, given, wanted in (
        ("blocks", set(translations.blocks), needed),
        ("sections", set(translations.sections), needed_titles),
    ):
        if wanted - given:
            raise AssemblyError(f"translations.{label}: missing {sorted(wanted - given)}")
        if given - wanted:
            raise AssemblyError(f"translations.{label}: unexpected {sorted(given - wanted)}")
    for block_id, block in blocks.items():
        block["translation"] = translations.blocks.get(block_id)
    for first, section in titled.items():
        section["title_translation"] = translations.sections.get(first)


def assemble(
    blocks: list,
    structure: Structure,
    translations: Translations,
    alignment: dict | None = None,
    diarization: dict | None = None,
) -> dict:
    assembled = BLOCKS.validate_python(blocks)
    if not assembled and structure.media.transcript_provenance != "no-speech":
        raise AssemblyError("blocks: none assembled; only a verified no-speech source may be empty")
    speakers, turns, diarization_meta = build_speakers(structure, diarization)
    sole = speakers[0]["id"] if diarization is None and len(speakers) == 1 else None
    built = build_blocks(structure, assembled, load_alignment(alignment), sole)
    source_map = {
        "media": structure.media.model_dump(mode="json"),
        "speakers": speakers,
        "speaker_turns": turns,
        "diarization": diarization_meta,
        "sections": build_sections(structure, built),
        "blocks": built,
        "frames": build_frames(structure),
        "limitations": [item.model_dump(mode="json") for item in structure.limitations],
    }
    apply_translations(source_map, translations)
    MediaSourceMap.model_validate_json(json.dumps(source_map))
    return source_map


def read_json(path: Path | None) -> Any:  # noqa: ANN401 - JSON of any shape
    return None if path is None else json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="assemble and validate source_map.json")
    build.add_argument("blocks", type=Path, help="blocks.json from build_blocks.py assemble")
    build.add_argument("structure", type=Path)
    build.add_argument("translations", type=Path)
    build.add_argument("--alignment", type=Path)
    build.add_argument("--diarization", type=Path)
    build.add_argument("--output", type=Path, required=True)

    translate = commands.add_parser("translate", help="replace the translations of a map")
    translate.add_argument("source_map", type=Path)
    translate.add_argument("translations", type=Path)
    translate.add_argument("--target-language", required=True)
    translate.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        translations = Translations.model_validate_json(args.translations.read_bytes())
        if args.command == "build":
            structure = Structure.model_validate_json(args.structure.read_bytes())
            source_map = assemble(
                read_json(args.blocks),
                structure,
                translations,
                read_json(args.alignment),
                read_json(args.diarization),
            )
            summary = (
                f"Assembled {len(source_map['blocks'])} blocks, "
                f"{len(source_map['sections'])} sections, {len(source_map['frames'])} frames, "
                f"{len(structure.fixes)} fixes"
            )
        else:
            source_map = read_json(args.source_map)
            source_map["media"]["target_language"] = args.target_language
            apply_translations(source_map, translations)
            MediaSourceMap.model_validate_json(json.dumps(source_map))
            summary = f"Translated {len(source_map['blocks'])} blocks to {args.target_language}"
    except ValidationError as exc:
        print(format_validation_error(exc), file=sys.stderr)
        return 1
    except (AssemblyError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    write_json(args.output, source_map)
    print(f"{summary} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
