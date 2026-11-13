#!/usr/bin/env python3
# ruff: noqa: RUF001 - diagnostics use the contract's full-width Chinese punctuation.
"""Validate a complete Media Bundle and project its source_map.md and media.html."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "media-source-map" / "scripts"))

from notes_model import Diagnostic, Notes, check_notes
from pydantic import ValidationError
from validate_source_map import (
    MediaSourceMap,
    SourceBlock,
    timestamp_milliseconds,
)

ASSETS = Path(__file__).resolve().parents[1] / "assets"
MAP_FILE = "source_map.json"
NOTES_FILE = "notes.json"
READER_COPY_FILE = "source_map.md"
PAGE_FILE = "media.html"
TURN_PAUSE_MS = 10_000
SHA_LENGTH = 12
SLOT = re.compile(r"\{\{([A-Z_]+)\}\}")
CSS_URL = re.compile(r"""url\(\s*["']?([^"')\s]+)""")


def short_sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()[:SHA_LENGTH]


def load_labels(target_language: str) -> dict:
    catalog = json.loads((ASSETS / "labels.json").read_text(encoding="utf-8"))
    return catalog["zh" if target_language.split("-")[0].lower() == "zh" else "en"]


def speaker_labels(source_map: MediaSourceMap, anonymous: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    number = 0
    for speaker in source_map.speakers:
        if speaker.name:
            labels[speaker.id] = one_line(speaker.name)
        else:
            number += 1
            labels[speaker.id] = f"{anonymous} {number}"
    return labels


def is_uncertain(block: SourceBlock) -> bool:
    return block.speaker is not None and block.speaker_confidence in ("low", "unknown")


def clock(timestamp: str) -> str:
    return timestamp.replace(",", ".").partition(".")[0]


def seconds_clock(seconds: int | float) -> str:
    whole = int(seconds)
    return f"{whole // 3600:02d}:{whole % 3600 // 60:02d}:{whole % 60:02d}"


def one_line(text: str) -> str:
    return re.sub(r"\s*\n\s*", " ", text).strip()


def reader_copy_turns(source_map: MediaSourceMap) -> list[list[SourceBlock]]:
    section_of = {
        block_id: index
        for index, section in enumerate(source_map.sections)
        for block_id in section.block_ids
    }
    turns: list[list[SourceBlock]] = []
    for block in source_map.blocks:
        previous = turns[-1][-1] if turns else None
        same_turn = (
            previous is not None
            and block.speaker is not None
            and block.speaker == previous.speaker
            and is_uncertain(block) == is_uncertain(previous)
            and section_of[block.id] == section_of[previous.id]
            and timestamp_milliseconds(block.start) - timestamp_milliseconds(previous.end)
            <= TURN_PAUSE_MS
        )
        if same_turn:
            turns[-1].append(block)
        else:
            turns.append([block])
    return turns


def render_reader_copy(source_map: MediaSourceMap, map_sha: str, labels: dict) -> str:
    text = labels["reader_copy"]
    media = source_map.media
    names = speaker_labels(source_map, labels["page"]["anon"])
    languages = ",".join(media.spoken_languages) or "—"
    source_line = text["separator"].join(
        (
            media.origin,
            media.kind,
            seconds_clock(media.duration_seconds),
            f"{languages}→{media.target_language}",
            media.reading_type,
            media.transcript_provenance,
        )
    )
    lines = [f"# {one_line(media.title)}", text["source"] + source_line]
    if source_map.speakers:
        lines.append(text["speakers"])
        lines += [f"- {names[speaker.id]} = {speaker.id}" for speaker in source_map.speakers]
    if source_map.limitations:
        lines.append(text["limitations"])
        for limitation in source_map.limitations:
            span = ""
            if limitation.start or limitation.end:
                start = clock(limitation.start) if limitation.start else "?"
                end = clock(limitation.end) if limitation.end else "?"
                span = f"{start}–{end} "
            lines.append(
                f"- {span}{limitation.kind}{text['kind_separator']}{one_line(limitation.detail)}"
            )
    lines += [text["generated"].format(sha=map_sha), ""]

    if media.transcript_provenance == "no-speech":
        lines.append(text["no_speech"])
    for turn in reader_copy_turns(source_map):
        first, last = turn[0], turn[-1]
        label = names[first.speaker] if first.speaker else labels["page"]["unknown"]
        if is_uncertain(first):
            label += "?"
        ids = first.id if len(turn) == 1 else f"{first.id}–{last.id}"
        header = f"[{clock(first.start)}–{clock(last.end)}] {label} ({ids})"
        low = [block.id for block in turn if block.confidence == "low"]
        if low:
            header += f" {text['low_confidence']}:{','.join(low)}"
        lines += [header, "  " + " ".join(one_line(block.original_text) for block in turn)]
    return "\n".join(lines) + "\n"


def page_map_data(source_map: MediaSourceMap) -> dict:
    """Only what the page shows: no ASR details, acoustic turns, or speaker candidates."""
    return source_map.model_dump(
        include={
            "media": {
                "title",
                "origin",
                "kind",
                "duration_seconds",
                "spoken_languages",
                "target_language",
                "reading_type",
                "transcript_provenance",
            },
            "speakers": True,
            "sections": True,
            "blocks": {
                "__all__": {
                    "id",
                    "order",
                    "start",
                    "end",
                    "speaker",
                    "speaker_confidence",
                    "original_text",
                    "translation",
                    "confidence",
                }
            },
            "frames": True,
            "limitations": True,
        }
    )


def data_island(element_id: str, value: object) -> str:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    text = text.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    return f'<script type="application/json" id="{element_id}">{text}</script>'


def render_page(
    source_map: MediaSourceMap, notes: Notes, labels: dict
) -> tuple[str, list[Diagnostic]]:
    template = (ASSETS / "template.html").read_text(encoding="utf-8")
    values = {
        "LANG": "zh-CN" if source_map.media.target_language.split("-")[0].lower() == "zh" else "en",
        "TITLE": html.escape(source_map.media.title, quote=True),
        "CSS": (ASSETS / "viewer.css").read_text(encoding="utf-8"),
        "JS": (ASSETS / "viewer.js").read_text(encoding="utf-8"),
        "NOSCRIPT": html.escape(labels["page"]["noscript"]),
        "UI_TEXT": data_island("ui-text", labels["page"]),
        "MAP_DATA": data_island("map-data", page_map_data(source_map)),
        "NOTES_DATA": data_island("notes-data", notes.model_dump(exclude_defaults=True)),
    }
    slots = SLOT.findall(template)
    missing = sorted(set(values) - set(slots))
    unknown = sorted(set(slots) - set(values))
    if missing or unknown:
        return "", [
            Diagnostic(
                "error",
                "artifact/template-slot",
                "template.html",
                "",
                f"模板槽位不匹配：缺 {missing}，多余 {unknown}",
            )
        ]
    # One pass over the template, so author text that looks like a slot is never expanded.
    return SLOT.sub(lambda match: values[match[1]], template), []


class PageScan(HTMLParser):
    RESOURCE_ATTRIBUTES = ("src", "href", "data", "srcset", "poster")

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.islands: dict[str, list[str]] = {}
        self.external: list[str] = []
        self.code: list[str] = []
        self.style: list[str] = []
        self._stack: list[tuple[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        for name, value in attrs:
            if name in self.RESOURCE_ATTRIBUTES and value:
                self.external.append(f"<{tag} {name}={value}>")
        if tag in ("script", "style", "title"):
            element = attributes.get("id") if attributes.get("type") == "application/json" else None
            if element:
                self.islands.setdefault(element, [])
            self._stack.append((tag, element))

    def handle_endtag(self, tag: str) -> None:
        if self._stack and self._stack[-1][0] == tag:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if not self._stack:
            self.code.append(data)
            return
        tag, element = self._stack[-1]
        if element:
            self.islands[element].append(data)
        elif tag == "style":
            self.style.append(data)
        elif tag == "script":
            self.code.append(data)


def recheck(
    page: str, reader_copy: str, source_map: MediaSourceMap, map_sha: str
) -> list[Diagnostic]:
    """Catch data-dependent failures in the candidate artifacts before anything reaches the disk."""

    def problem(code: str, file: str, message: str) -> Diagnostic:
        return Diagnostic("error", f"artifact/{code}", file, "", message)

    found: list[Diagnostic] = []
    scan = PageScan()
    scan.feed(page)
    scan.close()

    leftover = SLOT.findall("".join(scan.code + scan.style))
    if leftover:
        found.append(
            problem("template-slot", PAGE_FILE, f"模板槽位没有替换：{sorted(set(leftover))}")
        )

    css = "".join(scan.style)
    external = scan.external + [
        f"url({url})" for url in CSS_URL.findall(css) if not url.startswith("data:")
    ]
    external += ["@import"] if "@import" in css else []
    if external:
        found.append(problem("external-resource", PAGE_FILE, f"引用了外部资源：{external[:3]}"))

    if set(scan.islands) != {"ui-text", "map-data", "notes-data"}:
        found.append(problem("data-island", PAGE_FILE, f"数据岛不完整：{sorted(scan.islands)}"))
        return found
    try:
        data = json.loads("".join(scan.islands["map-data"]))
        json.loads("".join(scan.islands["notes-data"]))
    except json.JSONDecodeError as exc:
        found.append(problem("data-island", PAGE_FILE, f"数据岛不是合法 JSON：{exc.msg}"))
        return found

    block_ids = [item["id"] for item in data["blocks"]]
    frame_ids = [item["id"] for item in data["frames"]]
    if block_ids != [block.id for block in source_map.blocks] or frame_ids != [
        frame.id for frame in source_map.frames
    ]:
        found.append(
            problem(
                "source-ids",
                PAGE_FILE,
                "数据岛里的 S/F ID 与 map 不一致：每个 ID 要恰好一次且顺序相同",
            )
        )
    for item in data["frames"]:
        path = PurePosixPath(item["image_path"])
        if path.is_absolute() or ".." in path.parts:
            found.append(
                problem("frame-path", PAGE_FILE, f"帧路径不在 bundle 内：{item['image_path']}")
            )

    if f"sha256 {map_sha}" not in reader_copy.split("\n\n", 1)[0]:
        found.append(
            problem("reader-copy-sha", READER_COPY_FILE, "头部 sha256 与 source_map.json 不一致")
        )
    return found


def schema_diagnostics(error: ValidationError, file: str, prefix: str) -> list[Diagnostic]:
    found = []
    for item in error.errors(include_input=False, include_url=False):
        path = ""
        for part in item["loc"]:
            path += f"[{part}]" if isinstance(part, int) else f".{part}" if path else str(part)
        kind = item["type"]
        if kind == "extra_forbidden":
            found.append(
                Diagnostic(
                    "error",
                    f"{prefix}/unknown-field",
                    file,
                    path,
                    "不是当前格式的字段",
                    "删除这个字段",
                )
            )
        elif kind == "json_invalid":
            found.append(Diagnostic("error", f"{prefix}/invalid-json", file, path, item["msg"]))
        else:
            found.append(Diagnostic("error", f"{prefix}/schema", file, path, item["msg"]))
    return found


def missing_frames(bundle: Path, source_map: MediaSourceMap) -> list[Diagnostic]:
    root = bundle.resolve()
    found = []
    for index, frame in enumerate(source_map.frames):
        target = (root / frame.image_path).resolve()
        if not target.is_file() or not target.is_relative_to(root):
            found.append(
                Diagnostic(
                    "error",
                    "map/frame-missing",
                    MAP_FILE,
                    f"frames[{index}].image_path",
                    f"帧文件不存在或在 bundle 外：{frame.image_path}",
                    "恢复这个文件，或从 frames 移除这一帧",
                    frame.id,
                )
            )
    return found


@dataclass
class Build:
    inputs: dict[str, bytes] = field(default_factory=dict)
    artifacts: dict[str, bytes] = field(default_factory=dict)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        return any(item.severity == "error" for item in self.diagnostics)


def load_map(bundle: Path, result: Build) -> MediaSourceMap | None:
    try:
        result.inputs[MAP_FILE] = (bundle / MAP_FILE).read_bytes()
    except OSError as exc:
        result.diagnostics.append(
            Diagnostic(
                "error",
                "input/unreadable",
                MAP_FILE,
                "",
                f"无法读取：{exc.strerror}",
                "先生成 source_map.json",
            )
        )
        return None
    try:
        return MediaSourceMap.model_validate_json(result.inputs[MAP_FILE])
    except ValidationError as exc:
        result.diagnostics += schema_diagnostics(exc, MAP_FILE, "map")
        return None


def build_reader_copy(bundle: Path) -> Build:
    """The reading copy needs only the map, so agents can read it before the Notes exist."""
    result = Build()
    source_map = load_map(bundle, result)
    if source_map is not None:
        reader_copy = render_reader_copy(
            source_map,
            short_sha(result.inputs[MAP_FILE]),
            load_labels(source_map.media.target_language),
        )
        result.artifacts[READER_COPY_FILE] = reader_copy.encode("utf-8")
    return result


def build_bundle(bundle: Path) -> Build:
    result = Build()
    source_map = load_map(bundle, result)
    if source_map is None:
        return result

    result.diagnostics += missing_frames(bundle, source_map)
    notes = None
    try:
        result.inputs[NOTES_FILE] = (bundle / NOTES_FILE).read_bytes()
        notes = Notes.model_validate_json(result.inputs[NOTES_FILE])
    except OSError as exc:
        result.diagnostics.append(
            Diagnostic(
                "error",
                "input/unreadable",
                NOTES_FILE,
                "",
                f"无法读取：{exc.strerror}",
                "先写 notes.json，材料齐全后再渲染",
            )
        )
    except ValidationError as exc:
        result.diagnostics += schema_diagnostics(exc, NOTES_FILE, "notes")
    else:
        result.diagnostics += check_notes(notes, source_map)
    if result.failed or notes is None:
        return result

    labels = load_labels(source_map.media.target_language)
    map_sha = short_sha(result.inputs[MAP_FILE])
    reader_copy = render_reader_copy(source_map, map_sha, labels)
    page, slot_errors = render_page(source_map, notes, labels)
    result.diagnostics += slot_errors
    if not result.failed:
        result.diagnostics += recheck(page, reader_copy, source_map, map_sha)
    if not result.failed:
        result.artifacts[READER_COPY_FILE] = reader_copy.encode("utf-8")
        result.artifacts[PAGE_FILE] = page.encode("utf-8")
    return result


def stale_artifacts(bundle: Path, artifacts: dict[str, bytes]) -> list[Diagnostic]:
    found = []
    for name, content in artifacts.items():
        path = bundle / name
        if not path.is_file() or path.read_bytes() != content:
            found.append(
                Diagnostic(
                    "error",
                    f"stale/{name}",
                    name,
                    "",
                    "与当前输入渲染的结果不一致",
                    "重新运行 render_bundle.py",
                )
            )
    return found


def receipt(build: Build, heading: str) -> list[str]:
    entries = [*build.inputs.items(), *build.artifacts.items()]
    width = max(len(name) + len(str(len(content))) for name, content in entries) + 2
    lines = [heading]
    for name, content in entries:
        lines.append(
            f"  {name}{str(len(content)).rjust(width - len(name))} bytes  {short_sha(content)}"
        )
    return lines


def commit(bundle: Path, artifacts: dict[str, bytes]) -> list[Diagnostic]:
    temporary: list[Path] = []
    try:
        for name, content in artifacts.items():
            # mkstemp creates the file exclusively, so a planted name or symlink is never
            # written through.
            descriptor, path = tempfile.mkstemp(prefix=f".{name}.", suffix=".tmp", dir=bundle)
            temporary.append(Path(path))
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
        for name, path in zip(artifacts, temporary, strict=True):
            os.replace(path, bundle / name)
    except OSError as exc:
        return [
            Diagnostic(
                "error",
                "commit/write-failed",
                "",
                "",
                f"写入失败：{exc.strerror}",
                "修好原因后重跑；两个产物可能已不一致，重跑即恢复",
            )
        ]
    finally:
        for path in temporary:
            path.unlink(missing_ok=True)
    return []


def build_parser(description: str | None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("bundle", type=Path, help="Media Bundle directory")
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare with the rendered files on disk without writing",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    build_artifacts: Callable[[Path], Build] = build_bundle,
    description: str | None = __doc__,
) -> int:
    parser = build_parser(description)
    args = parser.parse_args(argv)
    bundle: Path = args.bundle
    if not bundle.is_dir():
        parser.error(f"not a directory: {bundle}")

    try:
        build = build_artifacts(bundle)
        if not build.failed:
            if args.check:
                build.diagnostics += stale_artifacts(bundle, build.artifacts)
            else:
                build.diagnostics += commit(bundle, build.artifacts)
    except Exception as exc:  # A crash must still report one stable diagnostic and no stack.
        print(f"error internal/unclassified：{type(exc).__name__}。")
        return 1

    for item in build.diagnostics:
        print(item.line())
    if build.failed:
        return 1
    if build.diagnostics:
        print()
    print("\n".join(receipt(build, "checked" if args.check else "rendered")))
    warnings = sum(item.severity == "warning" for item in build.diagnostics)
    if warnings:
        print(f"{warnings} warning" + ("s" if warnings > 1 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
