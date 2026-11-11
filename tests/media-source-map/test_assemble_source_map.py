# ruff: noqa: RUF001 - tests use full-width CJK punctuation.
from __future__ import annotations

import copy
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/media-shared/media-source-map/scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures/assemble"
GOLDEN = ROOT / "tests/media-render/fixtures/source_map.fixture.json"


def load_module(name: str):  # noqa: ANN201 - a loaded script module
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = load_module("assemble_source_map")
BLOCKS = load_module("build_blocks")


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def assembled_blocks() -> list[dict]:
    """Blocks as build_blocks.py assemble writes them for the fixture cues and plan."""
    cues = load("cues.json")["transcription"]
    return BLOCKS.assemble(load("plan.json"), cues, BLOCKS.tokenize(cues))


def golden() -> dict:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def without_cue_ranges(source_map: dict) -> dict:
    result = copy.deepcopy(source_map)
    for block in result["blocks"]:
        block.pop("source_cues")
    return result


class AssembleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.blocks = assembled_blocks()
        # Tests drop the speaker evidence by setting these to None.
        self.alignment: Any = load("alignment.json")
        self.diarization: Any = load("diarization.json")
        self.structure = load("structure.json")
        self.translations = load("translations.json")

    def assemble(self) -> dict:
        return MODULE.assemble(
            self.blocks,
            MODULE.Structure.model_validate(self.structure),
            MODULE.Translations.model_validate(self.translations),
            self.alignment,
            self.diarization,
        )

    def assert_fails(self, fragment: str) -> None:
        with self.assertRaises(MODULE.AssemblyError) as caught:
            self.assemble()
        self.assertIn(fragment, str(caught.exception))

    def override(self, block_id: str) -> dict:
        return next(item for item in self.structure["blocks"] if item["id"] == block_id)

    def block(self, block_id: str) -> dict:
        return next(item for item in self.blocks if item["id"] == block_id)

    def test_reproduces_the_golden_map(self) -> None:
        source_map = self.assemble()
        self.assertEqual(without_cue_ranges(source_map), golden())
        self.assertEqual(source_map["blocks"][1]["source_cues"], ["C0002", "C0003"])
        self.assertEqual(self.assemble(), source_map)

    def test_cli_writes_a_valid_map(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            blocks = Path(directory) / "blocks.json"
            blocks.write_text(json.dumps(self.blocks))
            output = Path(directory) / "source_map.json"
            with redirect_stdout(io.StringIO()) as stdout:
                code = MODULE.main(
                    [
                        "build",
                        str(blocks),
                        str(FIXTURES / "structure.json"),
                        str(FIXTURES / "translations.json"),
                        "--alignment",
                        str(FIXTURES / "alignment.json"),
                        "--diarization",
                        str(FIXTURES / "diarization.json"),
                        "--output",
                        str(output),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertIn("Assembled 18 blocks", stdout.getvalue())
            self.assertEqual(without_cue_ranges(json.loads(output.read_text())), golden())

    def test_cli_reports_errors_without_writing(self) -> None:
        self.structure["blocks"].append({"id": "S099", "confidence": "low"})
        with tempfile.TemporaryDirectory() as directory:
            blocks = Path(directory) / "blocks.json"
            blocks.write_text(json.dumps(self.blocks))
            structure = Path(directory) / "structure.json"
            structure.write_text(json.dumps(self.structure))
            output = Path(directory) / "source_map.json"
            with redirect_stderr(io.StringIO()) as stderr:
                code = MODULE.main(
                    [
                        "build",
                        str(blocks),
                        str(structure),
                        str(FIXTURES / "translations.json"),
                        "--alignment",
                        str(FIXTURES / "alignment.json"),
                        "--diarization",
                        str(FIXTURES / "diarization.json"),
                        "--output",
                        str(output),
                    ]
                )
            self.assertEqual(code, 1)
            self.assertIn("unknown block IDs ['S099']", stderr.getvalue())
            self.assertFalse(output.exists())

    def test_each_block_override_appears_once(self) -> None:
        self.structure["blocks"].append({"id": "S006"})
        self.assert_fails("may appear once")

    def test_text_may_only_restore_punctuation(self) -> None:
        self.override("S013")["text"] = "Okay. Let's go with the server-side key. That's decided."
        self.assert_fails("only punctuation")

    def test_fix_must_match_exactly_once(self) -> None:
        self.structure["fixes"][0]["find"] = "missing phrase"
        self.assert_fails("occurs 0 times")
        self.setUp()
        self.structure["fixes"][0]["find"] = "the"
        self.assert_fails("occurs")

    def test_alignment_must_be_keyed_by_cue(self) -> None:
        del self.alignment["segments"][0]["cue"]
        self.assert_fails("needs a cue ID")

    def test_translations_pair_with_every_block_and_section(self) -> None:
        del self.translations["blocks"]["S004"]
        self.assert_fails("missing ['S004']")
        self.setUp()
        self.translations["sections"]["S002"] = "多余"
        self.assert_fails("unexpected ['S002']")

    def test_same_language_target_has_no_translations(self) -> None:
        self.structure["media"]["target_language"] = "en-GB"
        self.translations = {}
        source_map = self.assemble()
        self.assertTrue(all(block["translation"] is None for block in source_map["blocks"]))
        self.assertTrue(all(s["title_translation"] is None for s in source_map["sections"]))

    def test_section_title_language_follows_the_source(self) -> None:
        self.structure["blocks"].append({"id": "S001", "language": "fr"})
        self.structure["media"]["target_language"] = "fr"
        del self.translations["blocks"]["S001"]
        source_map = self.assemble()
        self.assertIsNone(source_map["blocks"][0]["translation"])
        self.assertEqual(source_map["sections"][0]["title_translation"], "重试为何造成重复扣款")

    def test_without_diarization_a_single_speaker_is_assigned(self) -> None:
        self.alignment = self.diarization = None
        self.structure["speakers"] = [{"id": "SPK001", "name": "Dana Lee"}]
        for block in self.blocks:
            block["speaker"] = None
        for plan in self.structure["blocks"]:
            for key in ("speaker_confidence", "attribution_note"):
                plan.pop(key, None)
        source_map = self.assemble()
        self.assertEqual({block["speaker"] for block in source_map["blocks"]}, {"SPK001"})
        self.assertIsNone(source_map["diarization"])

    def test_unsettled_speaker_needs_a_stated_confidence(self) -> None:
        del self.override("S006")["speaker_confidence"]
        self.assert_fails("block S006: C0007 need speaker review")

    def test_speaker_against_certain_evidence_needs_a_stated_confidence(self) -> None:
        self.block("S001")["speaker"] = "SPK002"
        self.assert_fails("block S001: C0001 need speaker review")

    def test_speaker_is_decided_only_in_the_plan(self) -> None:
        self.structure["blocks"].append({"id": "S001", "speaker": "SPK002"})
        with self.assertRaises(MODULE.ValidationError):
            self.assemble()

    def test_small_decoder_overshoot_is_clamped(self) -> None:
        self.block("S018")["end"] = "00:07:10.080"
        self.assertEqual(self.assemble()["blocks"][-1]["end"], "00:07:10")
        self.block("S018")["end"] = "00:07:10.200"
        with self.assertRaises(MODULE.ValidationError):
            self.assemble()

    def test_section_ends_at_the_latest_member_end(self) -> None:
        self.block("S017")["end"] = "00:07:10.000"
        self.block("S018")["end"] = "00:07:09.500"
        source_map = self.assemble()
        self.assertEqual(source_map["blocks"][-1]["end"], "00:07:09.500")
        self.assertEqual(source_map["sections"][-1]["end"], "00:07:10")

    def test_unresolved_block_keeps_its_single_candidate(self) -> None:
        self.alignment["segments"][-1]["speaker_candidates"] = ["SPK003"]
        source_map = self.assemble()
        self.assertEqual(source_map["blocks"][-1]["speaker_candidates"], ["SPK003"])
        self.assertEqual(source_map["blocks"][0]["speaker_candidates"], [])

    def test_translate_replaces_only_translations(self) -> None:
        source_map = self.assemble()
        original = copy.deepcopy(source_map)
        source_map["media"]["target_language"] = "ja"
        translations = {
            "blocks": {block["id"]: "訳" for block in source_map["blocks"]},
            "sections": {section["block_ids"][0]: "題" for section in source_map["sections"]},
        }
        MODULE.apply_translations(source_map, MODULE.Translations.model_validate(translations))
        for before, after in zip(original["blocks"], source_map["blocks"], strict=True):
            self.assertEqual({**before, "translation": "訳"}, after)

    def test_unknown_structure_fields_are_rejected(self) -> None:
        self.override("S006")["speeker"] = "SPK001"
        with self.assertRaises(MODULE.ValidationError):
            self.assemble()


class NoSpeechAndUnspacedTextTests(unittest.TestCase):
    def empty_structure(self, provenance: str) -> object:
        structure = load("structure.json")
        structure["media"] |= {"transcript_provenance": provenance, "spoken_languages": []}
        structure |= {"speakers": [], "blocks": [], "fixes": [], "sections": [], "frames": []}
        return MODULE.Structure.model_validate(structure)

    def test_verified_no_speech_source_builds_without_blocks(self) -> None:
        source_map = MODULE.assemble([], self.empty_structure("no-speech"), MODULE.Translations())
        self.assertEqual(source_map["blocks"], [])
        self.assertEqual(source_map["sections"], [])

    def test_no_blocks_needs_no_speech_provenance(self) -> None:
        with self.assertRaises(MODULE.AssemblyError) as caught:
            MODULE.assemble([], self.empty_structure("whisper-asr"), MODULE.Translations())
        self.assertIn("no-speech", str(caught.exception))

    def test_unspaced_scripts_compare_by_character(self) -> None:
        self.assertEqual(MODULE.words("你好世界"), MODULE.words("你好，世界。"))
        self.assertEqual(MODULE.words("きょうはいい天気"), MODULE.words("きょうは、いい天気。"))
        self.assertNotEqual(MODULE.words("你好世界"), MODULE.words("你好，地球。"))
        self.assertNotEqual(MODULE.words("the rapist"), MODULE.words("therapist"))
        self.assertNotEqual(MODULE.words("कि"), MODULE.words("कु"))
        self.assertEqual(MODULE.words("नमस्ते दुनिया"), MODULE.words("नमस्ते, दुनिया।"))
        self.assertEqual(
            MODULE.words("Hello world, 你好世界"), ["hello", "world", "你", "好", "世", "界"]
        )


if __name__ == "__main__":
    unittest.main()
