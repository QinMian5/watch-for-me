# ruff: noqa: RUF001 - diagnostics use the contract's full-width Chinese punctuation.
"""Pydantic model and map cross-checks for one Media Notes (notes.json)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from validate_source_map import FrameId, MediaSourceMap, SourceBlockId, SpeakerId

Text = Annotated[str, Field(pattern=r"\S")]


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    file: str
    path: str
    message: str
    fix: str | None = None
    subject: str | None = None

    def line(self) -> str:
        head = " ".join(
            part for part in (self.severity, self.code, self.file, self.path, self.subject) if part
        )
        return f"{head}：{self.message}。" + (f"改法：{self.fix}" if self.fix else "")


class NotesModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Paragraph(NotesModel):
    text: Text
    speakers: list[SpeakerId] = []
    cites: list[SourceBlockId] = []
    frames: list[FrameId] = []


class Unit(NotesModel):
    heading: Text
    paragraphs: list[Paragraph] = Field(min_length=1)


class Notes(NotesModel):
    units: list[Unit] = Field(min_length=1)


def _error(
    code: str, path: str, message: str, fix: str | None = None, subject: str | None = None
) -> Diagnostic:
    return Diagnostic("error", code, "notes.json", path, message, fix, subject)


def _warning(
    code: str, path: str, message: str, fix: str | None = None, subject: str | None = None
) -> Diagnostic:
    return Diagnostic("warning", code, "notes.json", path, message, fix, subject)


def _name_pattern(name: str) -> re.Pattern[str]:
    """Match a name without firing inside a longer Latin word such as Li in Living."""
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(name)}(?![A-Za-z0-9])")


_ID_IN_TEXT = re.compile(r"(?<![A-Za-z0-9])[SF]\d{3,}(?![A-Za-z0-9])")


def _check_ids(
    path: str, field: str, values: list[str], known: set[str], kind: str, fix: str
) -> list[Diagnostic]:
    found: list[Diagnostic] = []
    seen: set[str] = set()
    for index, value in enumerate(values):
        location = f"{path}.{field}[{index}]"
        if value in seen:
            found.append(
                _error("notes/duplicate-id", location, "同一列表内重复", "删除重复项", value)
            )
        seen.add(value)
        if value not in known:
            found.append(_error("notes/unknown-id", location, f"引用的{kind}不存在", fix, value))
    return found


def check_notes(notes: Notes, source_map: MediaSourceMap) -> list[Diagnostic]:
    """Check schema-valid Notes against its map; errors block rendering, warnings do not."""
    blocks = {block.id: block for block in source_map.blocks}
    frames = {frame.id for frame in source_map.frames}
    names = {speaker.id: speaker.name for speaker in source_map.speakers}
    errors: list[Diagnostic] = []
    warnings: list[Diagnostic] = []
    cited: set[str] = set()

    for unit_index, unit in enumerate(notes.units):
        unit_path = f"units[{unit_index}]"
        # The first unit is the orientation, which summarizes the whole source and may cite nothing.
        if unit_index > 0 and not any(
            paragraph.cites or paragraph.frames for paragraph in unit.paragraphs
        ):
            errors.append(
                _error(
                    "notes/unit-without-evidence",
                    unit_path,
                    "单元没有任何 cites 或 frames",
                    "至少给一段加上 cites 或 frames",
                )
            )
        for paragraph_index, paragraph in enumerate(unit.paragraphs):
            path = f"{unit_path}.paragraphs[{paragraph_index}]"
            errors += _check_ids(
                path,
                "cites",
                paragraph.cites,
                set(blocks),
                "块",
                "改成 map 中的 S…",
            )
            errors += _check_ids(path, "frames", paragraph.frames, frames, "帧", "改成 map 中的 F…")
            errors += _check_ids(
                path, "speakers", paragraph.speakers, set(names), "说话人", "改成 map 中的 SPK…"
            )
            cited.update(paragraph.cites)

            cited_speakers = {blocks[id_].speaker for id_ in paragraph.cites if id_ in blocks}
            if paragraph.cites:
                for index, speaker in enumerate(paragraph.speakers):
                    if speaker in names and speaker not in cited_speakers:
                        warnings.append(
                            _warning(
                                "notes/speaker-not-cited",
                                f"{path}.speakers[{index}]",
                                "这个说话人不是所引块的说话人",
                                "改正 speakers 或 cites",
                                speaker,
                            )
                        )
            for name in names.values():
                if name and _name_pattern(name).search(paragraph.text):
                    warnings.append(
                        _warning(
                            "notes/speaker-name-in-text",
                            path,
                            f"正文含说话人姓名 {name}",
                            "用 speakers 字段归属",
                        )
                    )
            for match in _ID_IN_TEXT.findall(paragraph.text):
                warnings.append(
                    _warning(
                        "notes/id-in-text",
                        path,
                        f"正文含 ID {match}",
                        "用 cites 或 frames 表达引用",
                    )
                )

    for index, section in enumerate(source_map.sections):
        if section.block_ids and not cited.intersection(section.block_ids):
            warnings.append(
                _warning(
                    "notes/section-uncited",
                    f"sections[{index}]",
                    f"map 分段“{section.title_original}”整段未被引用",
                    "补充相关内容的引用，或在交付时说明原因",
                )
            )
    return errors + warnings
