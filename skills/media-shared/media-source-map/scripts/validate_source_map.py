#!/usr/bin/env python3
"""Validate the structural format of a Media Source Map."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from itertools import pairwise
from pathlib import Path, PurePosixPath
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

Timestamp = Annotated[
    str,
    Field(pattern=r"^\d{2,}:[0-5]\d:[0-5]\d(?:[.,]\d{3})?$"),
]
LanguageTag = Annotated[
    str,
    Field(pattern=r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$"),
]
SourceBlockId = Annotated[str, Field(pattern=r"^S\d{3,}$")]
FrameId = Annotated[str, Field(pattern=r"^F\d{3,}$")]
NonEmptyString = Annotated[str, Field(min_length=1)]
ReadingType = Literal["expository", "procedural", "dialogic", "reportorial", "reflective"]
SpeakerId = Annotated[str, Field(pattern=r"^SPK\d{3,}$")]
CueId = Annotated[str, Field(pattern=r"^C\d{4,}$")]


def timestamp_milliseconds(value: str) -> int:
    clock, separator, fraction = value.replace(",", ".").partition(".")
    hours, minutes, seconds = (int(part) for part in clock.split(":"))
    milliseconds = int(fraction) if separator else 0
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + milliseconds


class SourceMapModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class AsrMetadata(SourceMapModel):
    backend: Literal["whisper.cpp", "faster-whisper"]
    quality: Literal["balanced", "maximum"]
    model: NonEmptyString
    device: NonEmptyString
    compute_type: NonEmptyString
    detected_language: LanguageTag | None
    parameters: dict[str, Any]


class MediaMetadata(SourceMapModel):
    kind: Literal["audio", "video"]
    title: NonEmptyString
    source_type: Literal["online-video", "local-video", "local-audio"]
    origin: NonEmptyString
    source_id: NonEmptyString | None
    duration_seconds: int | float = Field(ge=0)
    spoken_languages: list[LanguageTag]
    target_language: LanguageTag
    reading_type: ReadingType
    transcript_provenance: Literal[
        "platform-manual",
        "platform-auto",
        "sidecar",
        "embedded",
        "whisper-asr",
        "no-speech",
    ]
    asr: AsrMetadata | None

    @model_validator(mode="after")
    def check_kind(self) -> Self:
        if (self.source_type == "local-audio") != (self.kind == "audio"):
            raise ValueError("media kind must match the source type")
        return self


class Speaker(SourceMapModel):
    id: SpeakerId
    name: NonEmptyString | None


class SpeakerTurn(SourceMapModel):
    speaker: SpeakerId
    start: Timestamp
    end: Timestamp

    @model_validator(mode="after")
    def check_range(self) -> Self:
        if timestamp_milliseconds(self.end) <= timestamp_milliseconds(self.start):
            raise ValueError("speaker turn must have positive duration")
        return self


class DiarizationMetadata(SourceMapModel):
    backend: Literal["pyannote.audio"]
    model: NonEmptyString
    revision: NonEmptyString
    device: Literal["cpu", "cuda", "mps"]
    speaker_count: int = Field(ge=0)
    audio_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    parameters: dict[str, int]


class Section(SourceMapModel):
    title_original: NonEmptyString
    title_translation: NonEmptyString | None
    reading_type: ReadingType
    start: Timestamp
    end: Timestamp
    block_ids: list[SourceBlockId]

    @model_validator(mode="after")
    def check_range(self) -> Self:
        if timestamp_milliseconds(self.end) < timestamp_milliseconds(self.start):
            raise ValueError("section end precedes section start")
        return self


class SourceBlock(SourceMapModel):
    id: SourceBlockId
    order: int = Field(ge=1)
    start: Timestamp
    end: Timestamp
    speaker: SpeakerId | None
    speaker_candidates: list[SpeakerId]
    speaker_confidence: Literal["high", "medium", "low", "unknown"]
    overlap: bool
    attribution_note: str | None
    language: LanguageTag
    original_text: NonEmptyString
    translation: NonEmptyString | None
    confidence: Literal["high", "medium", "low"]
    source_cues: Annotated[list[CueId], Field(min_length=2, max_length=2)] | None = None

    @model_validator(mode="after")
    def check_range(self) -> Self:
        if timestamp_milliseconds(self.end) < timestamp_milliseconds(self.start):
            raise ValueError("block end precedes block start")
        if self.source_cues and int(self.source_cues[0][1:]) > int(self.source_cues[1][1:]):
            raise ValueError("block source_cues are reversed")
        return self


class Frame(SourceMapModel):
    id: FrameId
    timestamp: Timestamp
    image_path: NonEmptyString
    related_blocks: list[SourceBlockId]

    @field_validator("image_path")
    @classmethod
    def check_image_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("image_path must stay inside the media bundle")
        if path.parts[:2] != ("assets", "frames") or len(path.parts) < 3:
            raise ValueError("image_path must be under assets/frames/")
        return value


class Limitation(SourceMapModel):
    kind: Literal["coverage", "transcript", "translation", "visual", "speaker", "overlap"]
    start: Timestamp | None
    end: Timestamp | None
    detail: NonEmptyString

    @model_validator(mode="after")
    def check_range(self) -> Self:
        if (
            self.start is not None
            and self.end is not None
            and timestamp_milliseconds(self.end) < timestamp_milliseconds(self.start)
        ):
            raise ValueError("limitation end precedes limitation start")
        return self


class MediaSourceMap(SourceMapModel):
    media: MediaMetadata
    speakers: list[Speaker]
    speaker_turns: list[SpeakerTurn]
    diarization: DiarizationMetadata | None
    sections: list[Section]
    blocks: list[SourceBlock]
    frames: list[Frame]
    limitations: list[Limitation]

    @model_validator(mode="after")
    def check_references(self) -> Self:
        block_ids = [block.id for block in self.blocks]
        frame_ids = [frame.id for frame in self.frames]
        block_orders = [block.order for block in self.blocks]
        speaker_ids = [speaker.id for speaker in self.speakers]

        if self.media.kind == "audio" and self.frames:
            raise ValueError("audio media cannot contain video frames")
        if len(speaker_ids) != len(set(speaker_ids)):
            raise ValueError("speaker IDs must be unique")
        known_speakers = set(speaker_ids)
        if self.diarization is None and (len(speaker_ids) > 1 or self.speaker_turns):
            raise ValueError("multiple speakers or acoustic turns require diarization metadata")
        turn_starts = [timestamp_milliseconds(turn.start) for turn in self.speaker_turns]
        if turn_starts != sorted(turn_starts):
            raise ValueError("speaker turns must be in timeline order")
        if self.diarization is not None and self.diarization.speaker_count != len(speaker_ids):
            raise ValueError("diarization speaker count disagrees with speaker table")
        for block in self.blocks:
            if block.speaker is None and block.speaker_confidence != "unknown":
                raise ValueError("an unassigned speaker must have unknown confidence")
            referenced = set(block.speaker_candidates)
            if block.speaker is not None:
                referenced.add(block.speaker)
            if referenced - known_speakers:
                raise ValueError("block references an unknown speaker")
            if self.diarization is not None and block.speaker is not None:
                start, end = (
                    timestamp_milliseconds(block.start),
                    timestamp_milliseconds(block.end),
                )
                ranges = sorted(
                    (
                        max(start, timestamp_milliseconds(turn.start)),
                        min(end, timestamp_milliseconds(turn.end)),
                    )
                    for turn in self.speaker_turns
                    if turn.speaker == block.speaker
                    and timestamp_milliseconds(turn.start) < end
                    and timestamp_milliseconds(turn.end) > start
                )
                if not ranges:
                    raise ValueError("assigned speaker has no acoustic turn at the block range")
                coverage, right = 0, start
                for left, stop in ranges:
                    coverage += max(0, stop - max(left, right))
                    right = max(right, stop)
                if coverage < 0.8 * (end - start) and not (block.attribution_note or "").strip():
                    raise ValueError("sparse acoustic coverage requires an attribution review note")
        for turn in self.speaker_turns:
            if turn.speaker not in known_speakers:
                raise ValueError("turn references an unknown speaker")
        duration_ms = self.media.duration_seconds * 1000
        for item in [*self.blocks, *self.sections, *self.speaker_turns]:
            if timestamp_milliseconds(item.end) > duration_ms + 1:
                raise ValueError("evidence range exceeds media duration")
        if any(timestamp_milliseconds(frame.timestamp) > duration_ms + 1 for frame in self.frames):
            raise ValueError("frame timestamp exceeds media duration")
        starts = [timestamp_milliseconds(block.start) for block in self.blocks]
        if starts != sorted(starts) or block_orders != sorted(block_orders):
            raise ValueError("blocks must be in timeline order")
        if block_orders != list(range(1, len(self.blocks) + 1)):
            raise ValueError("block orders must be contiguous from one")
        cue_ranges = [block.source_cues for block in self.blocks]
        if any(cue_ranges) and not all(cue_ranges):
            raise ValueError("source_cues must be present on every block or on none")
        if all(cue_ranges) and any(
            int(right[0][1:]) < int(left[1][1:])
            for left, right in pairwise(r for r in cue_ranges if r)
        ):
            raise ValueError("block cue ranges must follow source order, sharing at most one cue")

        if len(block_ids) != len(set(block_ids)):
            raise ValueError("block IDs must be unique")
        block_numbers = [int(block_id[1:]) for block_id in block_ids]
        if any(left >= right for left, right in pairwise(block_numbers)):
            raise ValueError("source block numbers must increase with order")
        if len(frame_ids) != len(set(frame_ids)):
            raise ValueError("frame IDs must be unique")
        if len(block_orders) != len(set(block_orders)):
            raise ValueError("block order values must be unique")

        known_blocks = set(block_ids)
        by_id = {block.id: block for block in self.blocks}
        section_blocks = []
        for section in self.sections:
            unknown = set(section.block_ids) - known_blocks
            if unknown:
                raise ValueError(f"section references unknown block IDs: {sorted(unknown)}")
            section_blocks.extend(section.block_ids)
            for block_id in section.block_ids:
                block = by_id[block_id]
                if timestamp_milliseconds(block.start) < timestamp_milliseconds(
                    section.start
                ) or timestamp_milliseconds(block.end) > timestamp_milliseconds(section.end):
                    raise ValueError("section range does not contain its block")
        if section_blocks != block_ids:
            raise ValueError("sections must cover every block exactly once in timeline order")
        for frame in self.frames:
            unknown = set(frame.related_blocks) - known_blocks
            if unknown:
                raise ValueError(f"frame references unknown block IDs: {sorted(unknown)}")
        return self


def validate_source_map_json(content: str | bytes) -> MediaSourceMap:
    """Validate JSON content and return the typed source map."""
    return MediaSourceMap.model_validate_json(content)


def validate_source_map_file(path: Path) -> MediaSourceMap:
    """Validate one source-map file and return the typed source map."""
    return validate_source_map_json(path.read_bytes())


def format_validation_error(error: ValidationError) -> str:
    lines: list[str] = []
    for item in error.errors(include_input=False, include_url=False):
        location = ".".join(str(part) for part in item["loc"]) or "source_map"
        lines.append(f"{location}: {item['msg']}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the structural format of a Media Source Map."
    )
    parser.add_argument("source_map", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        validate_source_map_file(args.source_map)
    except (OSError, UnicodeError) as exc:
        print(f"source map could not be read: {exc}", file=sys.stderr)
        return 1
    except ValidationError as exc:
        print(format_validation_error(exc), file=sys.stderr)
        return 1

    print(f"Valid Media Source Map: {args.source_map}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
