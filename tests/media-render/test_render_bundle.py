# ruff: noqa: RUF001 - diagnostics use the contract's full-width Chinese punctuation.
"""Exercise render_bundle.py through its command-line seam."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from html.parser import HTMLParser
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2] / "skills/media-shared/media-render"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT / "scripts"))

import render_bundle  # noqa: E402


def block(
    id_: str, order: int, start: str, end: str, speaker: str | None, text: str, **extra: object
) -> dict:
    return {
        "id": id_,
        "order": order,
        "start": start,
        "end": end,
        "speaker": speaker,
        "speaker_candidates": [],
        "speaker_confidence": "high" if speaker else "unknown",
        "overlap": False,
        "attribution_note": None,
        "language": "en",
        "original_text": text,
        "translation": None,
        "confidence": "high",
        **extra,
    }


def interview_map(target_language: str = "zh-CN") -> dict:
    """A fictional interview used as the worked example."""
    blocks = [
        block(
            "S001",
            1,
            "00:00:03",
            "00:00:10",
            "SPK001",
            "Welcome back. Today I'm talking with someone who has shipped agents to production.",
        ),
        block("S002", 2, "00:00:11.500", "00:00:15", None, "placeholder"),
        block(
            "S003",
            3,
            "00:00:15",
            "00:00:20.900",
            "SPK002",
            "Honestly, most of what I know came from things breaking.",
        ),
        block(
            "S004",
            4,
            "00:00:31",
            "00:00:32",
            "SPK001",
            "So where do you start?",
            speaker_confidence="low",
        ),
        block("S005", 5, "00:00:33", "00:00:34", None, "Can I ask a question from the back?"),
        block("S006", 6, "00:00:35", "00:00:40", "SPK002", "Sure, go ahead.", overlap=True),
        block(
            "S007",
            7,
            "00:00:40",
            "00:00:44",
            "SPK002",
            "We use a, uh, shadow eval harness first.",
            confidence="low",
        ),
    ]
    blocks[1].update(
        speaker="SPK002", speaker_confidence="high", original_text="Thanks for having me."
    )
    return {
        "media": {
            "kind": "video",
            "title": "Building Reliable Agents",
            "source_type": "online-video",
            "origin": "https://youtube.com/watch?v=xxxx",
            "source_id": None,
            "duration_seconds": 3492,
            "spoken_languages": ["en"],
            "target_language": target_language,
            "reading_type": "dialogic",
            "transcript_provenance": "platform-manual",
            "asr": None,
        },
        "speakers": [{"id": "SPK001", "name": "Dana Lee"}, {"id": "SPK002", "name": None}],
        "speaker_turns": [
            {"speaker": "SPK001", "start": "00:00:03", "end": "00:00:33"},
            {"speaker": "SPK002", "start": "00:00:11", "end": "00:00:44"},
        ],
        "diarization": {
            "backend": "pyannote.audio",
            "model": "local",
            "revision": "pinned",
            "device": "cpu",
            "speaker_count": 2,
            "audio_sha256": "a" * 64,
            "parameters": {},
        },
        "sections": [
            {
                "title_original": "Interview",
                "title_translation": "访谈",
                "reading_type": "dialogic",
                "start": "00:00:00",
                "end": "00:58:12",
                "block_ids": [item["id"] for item in blocks],
            }
        ],
        "blocks": blocks,
        "frames": [],
        "limitations": [
            {
                "kind": "coverage",
                "start": "00:41:10",
                "end": "00:42:30",
                "detail": "音频中断，内容缺失",
            }
        ],
    }


class BundleCase(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.bundle = Path(temporary.name).resolve() / "bundle"
        self.bundle.mkdir()

    def write_map(self, source_map: dict) -> None:
        (self.bundle / "source_map.json").write_text(
            json.dumps(source_map, ensure_ascii=False), encoding="utf-8"
        )

    def write_notes(self, notes: dict) -> None:
        (self.bundle / "notes.json").write_text(
            json.dumps(notes, ensure_ascii=False), encoding="utf-8"
        )

    def use_fixture(self, with_notes: bool = True) -> None:
        shutil.copy(FIXTURES / "source_map.fixture.json", self.bundle / "source_map.json")
        shutil.copytree(FIXTURES / "assets", self.bundle / "assets")
        if with_notes:
            shutil.copy(FIXTURES / "notes.A-generic.json", self.bundle / "notes.json")

    def render(self, *flags: str) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = render_bundle.main([str(self.bundle), *flags])
        return code, output.getvalue()

    def reader_copy(self) -> str:
        return (self.bundle / "source_map.md").read_text(encoding="utf-8")


class ReaderCopyTests(BundleCase):
    def test_merges_turns_and_marks_uncertainty_like_the_worked_example(self) -> None:
        self.write_map(interview_map())
        code, output = self.render()
        self.assertEqual(code, 0, output)
        sha = hashlib.sha256((self.bundle / "source_map.json").read_bytes()).hexdigest()[:12]
        self.assertEqual(
            self.reader_copy(),
            "# Building Reliable Agents\n"
            "来源：https://youtube.com/watch?v=xxxx ｜ video ｜ 00:58:12 ｜ en→zh-CN ｜ dialogic"
            " ｜ platform-manual\n"
            "说话人：\n"
            "- Dana Lee = SPK001\n"
            "- 说话人 1 = SPK002\n"
            "局限：\n"
            "- 00:41:10–00:42:30 coverage：音频中断，内容缺失\n"
            f"（由 source_map.json 确定性生成，勿手改；sha256 {sha}）\n"
            "\n"
            "[00:00:03–00:00:10] Dana Lee (S001)\n"
            "  Welcome back. Today I'm talking with someone who has shipped agents to production.\n"
            "[00:00:11–00:00:20] 说话人 1 (S002–S003)\n"
            "  Thanks for having me. Honestly, most of what I know came from things breaking.\n"
            "[00:00:31–00:00:32] Dana Lee? (S004)\n"
            "  So where do you start?\n"
            "[00:00:33–00:00:34] 说话人未辨 (S005)\n"
            "  Can I ask a question from the back?\n"
            "[00:00:35–00:00:44] 说话人 1 (S006–S007) 低置信:S007\n"
            "  Sure, go ahead. We use a, uh, shadow eval harness first.\n",
        )

    def test_breaks_turns_on_section_change_and_pause_over_ten_seconds(self) -> None:
        source_map = interview_map()
        source_map["blocks"] = [
            block("S001", 1, "00:00:00", "00:00:10", "SPK001", "One."),
            block("S002", 2, "00:00:20", "00:00:21", "SPK001", "Exactly ten seconds later."),
            block("S003", 3, "00:00:31.001", "00:00:32", "SPK001", "Just over ten seconds later."),
            block("S004", 4, "00:00:33", "00:00:34", "SPK001", "New section."),
        ]
        section = source_map["sections"][0]
        source_map["sections"] = [
            {**section, "end": "00:00:32", "block_ids": ["S001", "S002", "S003"]},
            {**section, "start": "00:00:33", "block_ids": ["S004"]},
        ]
        source_map["speaker_turns"] = [
            {"speaker": "SPK001", "start": "00:00:00", "end": "00:00:34"}
        ]
        self.write_map(source_map)
        code, output = self.render()
        self.assertEqual(code, 0, output)
        self.assertIn("[00:00:00–00:00:21] Dana Lee (S001–S002)\n", self.reader_copy())
        self.assertIn("[00:00:31–00:00:32] Dana Lee (S003)\n", self.reader_copy())
        self.assertIn("[00:00:33–00:00:34] Dana Lee (S004)\n", self.reader_copy())

    def test_consecutive_unidentified_blocks_stay_separate(self) -> None:
        source_map = interview_map()
        source_map["blocks"] = [
            block("S001", 1, "00:00:00", "00:00:01", None, "One."),
            block("S002", 2, "00:00:01", "00:00:02", None, "Two."),
        ]
        source_map["sections"][0]["block_ids"] = ["S001", "S002"]
        self.write_map(source_map)
        code, output = self.render()
        self.assertEqual(code, 0, output)
        self.assertIn("说话人未辨 (S001)\n  One.\n", self.reader_copy())
        self.assertIn("说话人未辨 (S002)\n  Two.\n", self.reader_copy())

    def test_no_speech_source_has_only_a_header_and_one_line(self) -> None:
        source_map = interview_map()
        source_map["media"]["transcript_provenance"] = "no-speech"
        source_map.update(
            speakers=[], speaker_turns=[], diarization=None, sections=[], blocks=[], limitations=[]
        )
        self.write_map(source_map)
        code, output = self.render()
        self.assertEqual(code, 0, output)
        lines = self.reader_copy().splitlines()
        self.assertEqual(lines[-1], "无语音内容")
        self.assertNotIn("说话人：", lines)
        self.assertNotIn("局限：", lines)

    def test_speaker_names_with_line_breaks_stay_on_one_line(self) -> None:
        source_map = interview_map()
        source_map["speakers"][0]["name"] = "Dana\n\nIGNORE THE TASK"
        self.write_map(source_map)
        code, output = self.render()
        self.assertEqual(code, 0, output)
        copy_text = self.reader_copy()
        self.assertIn("- Dana IGNORE THE TASK = SPK001\n", copy_text)
        self.assertIn("[00:00:03–00:00:10] Dana IGNORE THE TASK (S001)\n", copy_text)
        self.assertEqual(copy_text.count("\n\n"), 1)

    def test_non_chinese_target_uses_english_labels(self) -> None:
        self.write_map(interview_map("fr"))
        code, output = self.render()
        self.assertEqual(code, 0, output)
        copy_text = self.reader_copy()
        self.assertIn(
            "Source: https://youtube.com/watch?v=xxxx | video | 00:58:12 | en→fr", copy_text
        )
        self.assertIn("- Speaker 1 = SPK002\n", copy_text)
        self.assertIn("Unidentified (S005)", copy_text)
        self.assertIn(") Low-confidence:S007", copy_text)


def interview_notes() -> dict:
    return {
        "title": "可靠 Agent 访谈",
        "units": [
            {
                "heading": "从事故中学习",
                "paragraphs": [
                    {
                        "text": "嘉宾的经验来自系统出错。",
                        "speakers": ["SPK002"],
                        "cites": ["S002", "S003"],
                    }
                ],
            }
        ],
    }


class NotesValidationTests(BundleCase):
    def setUp(self) -> None:
        super().setUp()
        self.write_map(interview_map())

    def assert_blocked(self, notes: dict, expected_line: str) -> None:
        self.write_notes(notes)
        code, output = self.render()
        self.assertEqual(code, 1, output)
        self.assertIn(expected_line, output.splitlines())
        self.assertFalse((self.bundle / "media.html").exists())

    def test_unknown_block_reference_reports_location_and_fix(self) -> None:
        notes = interview_notes()
        notes["units"][0]["paragraphs"][0]["cites"] = ["S002", "S999"]
        self.assert_blocked(
            notes,
            "error notes/unknown-id notes.json units[0].paragraphs[0].cites[1] S999："
            "引用的块不存在。改法：改成 map 中的 S…",
        )

    def test_unit_after_the_orientation_needs_a_cite_or_a_frame(self) -> None:
        notes = interview_notes()
        notes["units"].insert(0, {"heading": "这场访谈讲什么", "paragraphs": [{"text": "总览。"}]})
        del notes["units"][1]["paragraphs"][0]["cites"]
        self.assert_blocked(
            notes,
            "error notes/unit-without-evidence notes.json units[1]：单元没有任何 cites 或 frames。"
            "改法：至少给一段加上 cites 或 frames",
        )

    def test_orientation_unit_may_have_no_evidence(self) -> None:
        notes = interview_notes()
        notes["units"].insert(0, {"heading": "这场访谈讲什么", "paragraphs": [{"text": "总览。"}]})
        self.write_notes(notes)
        code, output = self.render()
        self.assertEqual(code, 0, output)

    def test_extra_fields_and_empty_content_are_schema_errors(self) -> None:
        for mutate, code_and_path in (
            (lambda c: c.update(summary="x"), "notes/unknown-field notes.json summary"),
            (lambda c: c.update(title=""), "notes/schema notes.json title"),
            (lambda c: c.update(units=[]), "notes/schema notes.json units"),
            (
                lambda c: c["units"][0].update(heading=" "),
                "notes/schema notes.json units[0].heading",
            ),
            (
                lambda c: c["units"][0].update(paragraphs=[]),
                "notes/schema notes.json units[0].paragraphs",
            ),
            (
                lambda c: c["units"][0]["paragraphs"][0].update(text=""),
                "notes/schema notes.json units[0].paragraphs[0].text",
            ),
            (
                lambda c: c["units"][0]["paragraphs"][0].update(cites=["S002-S003"]),
                "notes/schema notes.json units[0].paragraphs[0].cites[0]",
            ),
        ):
            with self.subTest(code_and_path):
                notes = interview_notes()
                mutate(notes)
                self.write_notes(notes)
                code, output = self.render()
                self.assertEqual(code, 1, output)
                self.assertIn(f"error {code_and_path}：", output)

    def test_duplicate_ids_in_one_list_are_errors(self) -> None:
        notes = interview_notes()
        notes["units"][0]["paragraphs"][0]["cites"] = ["S002", "S002"]
        self.write_notes(notes)
        code, output = self.render()
        self.assertEqual(code, 1, output)
        self.assertIn(
            "error notes/duplicate-id notes.json units[0].paragraphs[0].cites[1] S002：", output
        )

    def test_unit_with_only_frames_is_valid_for_a_source_without_speech(self) -> None:
        source_map = interview_map()
        source_map["media"]["transcript_provenance"] = "no-speech"
        source_map.update(
            speakers=[], speaker_turns=[], diarization=None, sections=[], blocks=[], limitations=[]
        )
        source_map["frames"] = [
            {
                "id": "F001",
                "timestamp": "00:00:10",
                "image_path": "assets/frames/a.webp",
                "related_blocks": [],
            }
        ]
        self.write_map(source_map)
        (self.bundle / "assets/frames").mkdir(parents=True)
        (self.bundle / "assets/frames/a.webp").write_bytes(b"x")
        self.write_notes(
            {
                "title": "T",
                "units": [{"heading": "H", "paragraphs": [{"text": "画面", "frames": ["F001"]}]}],
            }
        )
        code, output = self.render()
        self.assertEqual(code, 0, output)

    def warnings_for(self, notes: dict) -> tuple[int, str]:
        self.write_notes(notes)
        return self.render()

    def test_warnings_do_not_block_and_are_counted(self) -> None:
        notes = interview_notes()
        notes["units"][0]["paragraphs"][0]["text"] = "Dana Lee 问了 S001 的问题。"
        notes["units"][0]["paragraphs"][0]["speakers"] = ["SPK001"]
        code, output = self.warnings_for(notes)
        self.assertEqual(code, 0, output)
        lines = output.splitlines()
        self.assertIn(
            "warning notes/speaker-name-in-text notes.json units[0].paragraphs[0]："
            "正文含说话人姓名 Dana Lee。改法：用 speakers 字段归属",
            lines,
        )
        self.assertTrue(
            any(
                line.startswith("warning notes/id-in-text notes.json units[0].paragraphs[0]：")
                for line in lines
            )
        )
        self.assertTrue(
            any(
                line.startswith(
                    "warning notes/speaker-not-cited notes.json "
                    "units[0].paragraphs[0].speakers[0] SPK001："
                )
                for line in lines
            )
        )
        self.assertEqual(lines[-1], "3 warnings")
        self.assertTrue((self.bundle / "media.html").exists())

    def test_speaker_check_is_skipped_without_cites_and_short_names_match_whole_words(self) -> None:
        source_map = interview_map()
        source_map["speakers"][0]["name"] = "Li"
        self.write_map(source_map)
        notes = interview_notes()
        notes["units"][0]["paragraphs"].append(
            {"text": "Living with failure.", "speakers": ["SPK001"]}
        )
        code, output = self.warnings_for(notes)
        self.assertEqual(code, 0, output)
        self.assertNotIn("warning", output)

    def test_uncited_section_warns(self) -> None:
        source_map = interview_map()
        section = source_map["sections"][0]
        source_map["sections"] = [
            {
                **section,
                "title_original": "One",
                "end": "00:00:20.900",
                "block_ids": ["S001", "S002", "S003"],
            },
            {
                **section,
                "title_original": "Two",
                "start": "00:00:31",
                "block_ids": ["S004", "S005", "S006", "S007"],
            },
        ]
        self.write_map(source_map)
        code, output = self.warnings_for(interview_notes())
        self.assertEqual(code, 0, output)
        self.assertIn("warning notes/section-uncited notes.json sections[1]：", output)
        self.assertEqual(output.splitlines()[-1], "1 warning")


class MapValidationTests(BundleCase):
    def test_retired_fields_report_their_location(self) -> None:
        source_map = interview_map()
        retired_speaker_field, retired_top_level = "ro" + "le", "gloss" + "ary"
        source_map["speakers"][0][retired_speaker_field] = "host"
        source_map[retired_top_level] = []
        self.write_map(source_map)
        code, output = self.render()
        self.assertEqual(code, 1, output)
        self.assertIn(
            f"error map/unknown-field source_map.json speakers[0].{retired_speaker_field}：", output
        )
        self.assertIn(f"error map/unknown-field source_map.json {retired_top_level}：", output)
        self.assertEqual(sorted(path.name for path in self.bundle.iterdir()), ["source_map.json"])

    def test_missing_and_malformed_maps_are_reported(self) -> None:
        code, output = self.render()
        self.assertEqual(code, 1)
        self.assertIn("error input/unreadable source_map.json：", output)
        (self.bundle / "source_map.json").write_text("{", encoding="utf-8")
        code, output = self.render()
        self.assertEqual(code, 1)
        self.assertIn("error map/invalid-json source_map.json", output)

    def test_missing_frame_file_is_a_located_error(self) -> None:
        self.use_fixture()
        (self.bundle / "assets/frames/00-03-10-000.webp").unlink()
        code, output = self.render()
        self.assertEqual(code, 1, output)
        self.assertIn("error map/frame-missing source_map.json frames[0].image_path F001：", output)

    def test_frame_symlink_leaving_the_bundle_is_rejected(self) -> None:
        self.use_fixture()
        frame = self.bundle / "assets/frames/00-03-10-000.webp"
        outside = self.bundle.parent / "outside.webp"
        outside.write_bytes(b"x")
        frame.unlink()
        frame.symlink_to(outside)
        code, output = self.render()
        self.assertEqual(code, 1, output)
        self.assertIn("error map/frame-missing source_map.json frames[0].image_path F001：", output)


class IslandReader(HTMLParser):
    """Collect JSON data islands and scripts the way a browser's tokenizer would see them."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.islands: dict[str, str] = {}
        self.tags: list[str] = []
        self.title = ""
        self._current: str | None = None
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        attributes = dict(attrs)
        self._in_title = tag == "title"
        if tag == "script" and attributes.get("type") == "application/json":
            self._current = attributes["id"] or ""
            self.islands[self._current] = ""

    def handle_endtag(self, tag: str) -> None:
        self._current = None
        self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._current:
            self.islands[self._current] += data
        if self._in_title:
            self.title += data


def read_page(bundle: Path) -> IslandReader:
    reader = IslandReader()
    reader.feed((bundle / "media.html").read_text(encoding="utf-8"))
    return reader


HOSTILE = (
    "</script><script>alert(1)</script> $& $1 \\1 <img src=x onerror=alert(2)>"
    " {{MAP_DATA}} & <!-- </style>"
)


class PageTests(BundleCase):
    def test_map_island_projects_only_what_the_page_uses(self) -> None:
        self.use_fixture(with_notes=False)
        code, output = self.render()
        self.assertEqual(code, 0, output)
        page = read_page(self.bundle)
        self.assertNotIn("notes-data", page.islands)
        data = json.loads(page.islands["map-data"])
        self.assertEqual(
            sorted(data), ["blocks", "frames", "limitations", "media", "sections", "speakers"]
        )
        self.assertNotIn("asr", data["media"])
        self.assertEqual(
            [item["id"] for item in data["blocks"]], [f"S{n:03d}" for n in range(1, 19)]
        )
        self.assertEqual([item["id"] for item in data["frames"]], ["F001", "F002"])

    def test_notes_island_appears_only_with_notes_and_the_title_follows_it(self) -> None:
        self.use_fixture()
        code, output = self.render()
        self.assertEqual(code, 0, output)
        page = read_page(self.bundle)
        notes = json.loads((FIXTURES / "notes.A-generic.json").read_text(encoding="utf-8"))
        self.assertEqual(json.loads(page.islands["notes-data"]), notes)
        self.assertEqual(page.title, notes["title"])

    def test_author_text_appears_verbatim_in_the_page(self) -> None:
        self.use_fixture()
        self.assertEqual(self.render()[0], 0)
        raw = (self.bundle / "media.html").read_text(encoding="utf-8")
        source_map = json.loads((FIXTURES / "source_map.fixture.json").read_text(encoding="utf-8"))
        notes = json.loads((FIXTURES / "notes.A-generic.json").read_text(encoding="utf-8"))
        texts = [item["original_text"] for item in source_map["blocks"]]
        texts += [item["translation"] for item in source_map["blocks"]]
        texts += [item["detail"] for item in source_map["limitations"]]
        texts += [paragraph["text"] for unit in notes["units"] for paragraph in unit["paragraphs"]]
        for text in texts:
            encoded = json.dumps(text, ensure_ascii=False)[1:-1]
            self.assertIn(encoded, raw)

    def hostile_bundle(self) -> dict:
        source_map = interview_map()
        source_map["media"]["title"] = HOSTILE
        source_map["speakers"][0]["name"] = HOSTILE
        source_map["blocks"][0]["original_text"] = HOSTILE
        source_map["blocks"][0]["translation"] = HOSTILE
        source_map["limitations"][0]["detail"] = HOSTILE
        self.write_map(source_map)
        notes = interview_notes()
        notes["title"] = HOSTILE
        notes["units"][0]["heading"] = HOSTILE
        notes["units"][0]["paragraphs"][0]["text"] = HOSTILE
        self.write_notes(notes)
        return source_map

    def test_hostile_text_stays_inert_and_round_trips(self) -> None:
        self.hostile_bundle()
        code, output = self.render()
        self.assertEqual(code, 0, output)
        raw = (self.bundle / "media.html").read_text(encoding="utf-8")
        page = read_page(self.bundle)
        self.assertNotIn("<img", raw)
        self.assertNotIn("alert(1)</script>", raw)
        self.assertEqual(page.tags.count("script"), 4)
        self.assertEqual(page.title, HOSTILE)
        data = json.loads(page.islands["map-data"])
        self.assertEqual(data["blocks"][0]["original_text"], HOSTILE)
        self.assertEqual(data["speakers"][0]["name"], HOSTILE)
        self.assertEqual(json.loads(page.islands["notes-data"])["title"], HOSTILE)
        self.assertIn(HOSTILE.split("\n")[0], self.reader_copy())

    def test_output_holds_no_absolute_path_and_is_deterministic(self) -> None:
        self.use_fixture()
        self.assertEqual(self.render()[0], 0)
        first = {
            name: (self.bundle / name).read_bytes() for name in ("media.html", "source_map.md")
        }
        self.assertEqual(self.render()[0], 0)
        for name, content in first.items():
            self.assertEqual((self.bundle / name).read_bytes(), content)
            self.assertNotIn(str(self.bundle).encode(), content)

    def test_interface_language_follows_the_target_language(self) -> None:
        for target, lang, label in (("zh-TW", "zh-CN", "笔记"), ("fr", "en", "Notes")):
            with self.subTest(target=target):
                source_map = interview_map(target)
                self.write_map(source_map)
                self.assertEqual(self.render()[0], 0)
                page = read_page(self.bundle)
                self.assertEqual(json.loads(page.islands["ui-text"])["notes"], label)
                self.assertIn(
                    f'<html lang="{lang}">',
                    (self.bundle / "media.html").read_text(encoding="utf-8"),
                )


class AssetTests(unittest.TestCase):
    def test_assets_never_use_inner_html_or_external_resources(self) -> None:
        for name in ("template.html", "viewer.js", "viewer.css"):
            text = (ROOT / "assets" / name).read_text(encoding="utf-8")
            with self.subTest(name=name):
                self.assertNotIn("innerHTML", text)
                self.assertNotIn("outerHTML", text)
                self.assertNotIn("insertAdjacentHTML", text)
                self.assertNotIn("document.write", text)
                self.assertNotIn("fetch(", text)

    def test_both_label_catalogs_have_the_same_complete_keys(self) -> None:
        catalog = json.loads((ROOT / "assets/labels.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(catalog), ["en", "zh"])
        for group in ("page", "reader_copy"):
            self.assertEqual(set(catalog["zh"][group]), set(catalog["en"][group]), group)
            for language in catalog:
                for key, value in catalog[language][group].items():
                    self.assertTrue(value, (language, group, key))

    def test_viewer_uses_only_keys_the_catalog_defines(self) -> None:
        catalog = json.loads((ROOT / "assets/labels.json").read_text(encoding="utf-8"))["en"][
            "page"
        ]
        viewer = (ROOT / "assets/viewer.js").read_text(encoding="utf-8")
        used = set(re.findall(r"\bt\('(\w+)'", viewer))
        self.assertTrue(used)
        self.assertEqual(used - set(catalog), set())

    def test_rename_prompt_rules_cover_old_labels_in_both_languages(self) -> None:
        catalog = json.loads((ROOT / "assets/labels.json").read_text(encoding="utf-8"))
        for language in catalog:
            rules = " ".join(catalog[language]["page"]["promptRules"])
            for field in (
                "speakers[].name",
                "limitations[].detail",
                "blocks[].attribution_note",
                "notes.json",
                "render_bundle.py",
            ):
                self.assertIn(field, rules, language)


class ReceiptAndCommitTests(BundleCase):
    def test_receipt_lists_inputs_and_artifacts_with_size_and_hash(self) -> None:
        self.use_fixture()
        code, output = self.render()
        self.assertEqual(code, 0, output)
        lines = output.splitlines()
        self.assertEqual(lines[0], "rendered")
        names = ("source_map.json", "notes.json", "source_map.md", "media.html")
        for line, name in zip(lines[1:5], names, strict=True):
            content = (self.bundle / name).read_bytes()
            self.assertEqual(
                line.split(),
                [name, str(len(content)), "bytes", hashlib.sha256(content).hexdigest()[:12]],
            )
        self.assertEqual(len({line.index(" bytes") for line in lines[1:5]}), 1)

    def test_receipt_omits_a_missing_notes(self) -> None:
        self.use_fixture(with_notes=False)
        self.assertNotIn("notes.json", self.render()[1])

    def test_an_error_leaves_old_artifacts_byte_identical(self) -> None:
        self.use_fixture()
        self.assertEqual(self.render()[0], 0)
        before = {
            name: (self.bundle / name).read_bytes() for name in ("media.html", "source_map.md")
        }
        notes = json.loads((self.bundle / "notes.json").read_text(encoding="utf-8"))
        notes["units"][0]["paragraphs"][0]["cites"] = ["S999"]
        self.write_notes(notes)
        code, output = self.render()
        self.assertEqual(code, 1, output)
        self.assertIn("error notes/unknown-id", output)
        for name, content in before.items():
            self.assertEqual((self.bundle / name).read_bytes(), content)

    def test_leaves_no_temporary_files(self) -> None:
        self.use_fixture()
        self.assertEqual(self.render()[0], 0)
        self.assertEqual(
            sorted(path.name for path in self.bundle.iterdir()),
            ["assets", "media.html", "notes.json", "source_map.json", "source_map.md"],
        )

    def test_planted_temporary_symlinks_are_never_written_through(self) -> None:
        self.use_fixture()
        victim = self.bundle.parent / "victim.txt"
        victim.write_text("keep me", encoding="utf-8")
        for name in ("source_map.md", "media.html"):
            (self.bundle / f".{name}.{os.getpid()}.tmp").symlink_to(victim)

        code, output = self.render()
        self.assertEqual(code, 0, output)
        self.assertEqual(victim.read_text(encoding="utf-8"), "keep me")
        for name in ("source_map.md", "media.html"):
            self.assertFalse((self.bundle / name).is_symlink(), name)
            self.assertTrue((self.bundle / f".{name}.{os.getpid()}.tmp").is_symlink(), name)

    def test_missing_bundle_directory_is_a_usage_error(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            render_bundle.main([str(self.bundle / "absent")])
        self.assertEqual(raised.exception.code, 2)

    def test_a_crash_reports_one_diagnostic_and_no_stack(self) -> None:
        self.use_fixture()
        with mock.patch.object(
            render_bundle, "render_reader_copy", side_effect=RuntimeError("secret")
        ):
            code, output = self.render()
        self.assertEqual(code, 1)
        self.assertIn("error internal/unclassified", output)
        self.assertNotIn("secret", output)
        self.assertNotIn("Traceback", output)

    def test_commit_failure_is_reported(self) -> None:
        self.use_fixture()
        with mock.patch.object(
            render_bundle.os, "replace", side_effect=PermissionError(13, "Permission denied")
        ):
            code, output = self.render()
        self.assertEqual(code, 1, output)
        self.assertIn("error commit/write-failed", output)
        self.assertEqual(
            sorted(path.name for path in self.bundle.iterdir()),
            ["assets", "notes.json", "source_map.json"],
        )

    def test_a_partial_commit_is_reported_detected_and_repaired_by_rerunning(self) -> None:
        self.use_fixture()
        self.assertEqual(self.render()[0], 0)
        source_map = json.loads((self.bundle / "source_map.json").read_text(encoding="utf-8"))
        source_map["speakers"][0]["name"] = "Dana L."
        self.write_map(source_map)
        (self.bundle / "media.html").unlink()
        (self.bundle / "media.html").mkdir()

        code, output = self.render()
        self.assertEqual(code, 1, output)
        self.assertIn("error commit/write-failed", output)
        self.assertIn("Dana L.", self.reader_copy())
        code, output = self.render("--check")
        self.assertEqual(code, 1, output)
        self.assertIn("error stale/media.html", output)
        self.assertNotIn("stale/source_map.md", output)

        (self.bundle / "media.html").rmdir()
        self.assertEqual(self.render()[0], 0)
        self.assertEqual(self.render("--check")[0], 0)


class CheckModeTests(BundleCase):
    def test_check_passes_after_render_and_writes_nothing(self) -> None:
        self.use_fixture()
        self.assertEqual(self.render()[0], 0)
        code, output = self.render("--check")
        self.assertEqual(code, 0, output)
        self.assertEqual(output.splitlines()[0], "checked")

    def test_check_never_creates_artifacts(self) -> None:
        self.use_fixture()
        code, output = self.render("--check")
        self.assertEqual(code, 1)
        self.assertIn("error stale/source_map.md", output)
        self.assertIn("error stale/media.html", output)
        self.assertFalse((self.bundle / "media.html").exists())

    def test_check_reports_stale_after_a_map_change(self) -> None:
        self.use_fixture()
        self.assertEqual(self.render()[0], 0)
        before = (self.bundle / "media.html").read_bytes()
        source_map = json.loads((self.bundle / "source_map.json").read_text(encoding="utf-8"))
        source_map["speakers"][0]["name"] = "Dana L."
        self.write_map(source_map)
        code, output = self.render("--check")
        self.assertEqual(code, 1, output)
        self.assertIn("error stale/source_map.md source_map.md：", output)
        self.assertIn("error stale/media.html media.html：", output)
        self.assertEqual((self.bundle / "media.html").read_bytes(), before)

    def test_check_reports_stale_after_only_a_notes_change(self) -> None:
        self.use_fixture()
        self.assertEqual(self.render()[0], 0)
        notes = json.loads((self.bundle / "notes.json").read_text(encoding="utf-8"))
        notes["title"] = "新标题"
        self.write_notes(notes)
        code, output = self.render("--check")
        self.assertEqual(code, 1, output)
        self.assertIn("error stale/media.html", output)
        self.assertNotIn("stale/source_map.md", output)


class ArtifactRecheckTests(BundleCase):
    def patched_assets(self, **replacements: str) -> mock._patch:
        assets = self.bundle.parent / "assets-copy"
        shutil.copytree(ROOT / "assets", assets)
        template = assets / "template.html"
        text = template.read_text(encoding="utf-8")
        for old, new in replacements.items():
            text = text.replace(old, new)
        template.write_text(text, encoding="utf-8")
        return mock.patch.object(render_bundle, "ASSETS", assets)

    def test_missing_template_slot_blocks_the_commit(self) -> None:
        self.use_fixture()
        with self.patched_assets(**{"{{MAP_DATA}}": ""}):
            code, output = self.render()
        self.assertEqual(code, 1, output)
        self.assertIn("error artifact/template-slot", output)
        self.assertFalse((self.bundle / "media.html").exists())

    def test_external_resource_in_the_template_blocks_the_commit(self) -> None:
        self.use_fixture()
        with self.patched_assets(
            **{"</head>": '<script src="https://example.com/x.js"></script></head>'}
        ):
            code, output = self.render()
        self.assertEqual(code, 1, output)
        self.assertIn("error artifact/external-resource", output)

    def test_block_lost_from_the_data_island_blocks_the_commit(self) -> None:
        self.use_fixture()
        real = render_bundle.page_map_data

        def lossy(source_map: render_bundle.MediaSourceMap) -> dict:
            data = real(source_map)
            data["blocks"].pop()
            return data

        with mock.patch.object(render_bundle, "page_map_data", lossy):
            code, output = self.render()
        self.assertEqual(code, 1, output)
        self.assertIn("error artifact/source-ids", output)


class GoldenTests(BundleCase):
    """Byte-compare the fixture bundle.

    To accept an intended change, run the media-render tests with UPDATE_GOLDEN=1 and review
    the diff of tests/media-render/golden/.
    """

    def test_fixture_bundle_matches_golden_files_byte_for_byte(self) -> None:
        self.use_fixture()
        code, output = self.render()
        self.assertEqual(code, 0, output)
        for name in ("source_map.md", "media.html"):
            actual = (self.bundle / name).read_bytes()
            golden = FIXTURES.parent / "golden" / name
            if os.environ.get("UPDATE_GOLDEN"):
                golden.write_bytes(actual)
            with self.subTest(name=name):
                self.assertEqual(actual, golden.read_bytes())


if __name__ == "__main__":
    unittest.main()
