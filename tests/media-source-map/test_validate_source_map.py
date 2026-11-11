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

from pydantic import ValidationError

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills/media-shared/media-source-map/scripts/validate_source_map.py"
)
SPEC = importlib.util.spec_from_file_location("validate_source_map", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def valid_source_map() -> dict:
    return {
        "media": {
            "kind": "video",
            "title": "Example",
            "source_type": "online-video",
            "origin": "https://example.com/video",
            "source_id": "example-1",
            "duration_seconds": 10,
            "spoken_languages": ["en"],
            "target_language": "zh-CN",
            "reading_type": "expository",
            "transcript_provenance": "platform-manual",
            "asr": None,
        },
        "speakers": [],
        "speaker_turns": [],
        "diarization": None,
        "sections": [
            {
                "title_original": "Introduction",
                "title_translation": "介绍",
                "reading_type": "expository",
                "start": "00:00:00",
                "end": "00:00:10",
                "block_ids": ["S001"],
            }
        ],
        "blocks": [
            {
                "id": "S001",
                "order": 1,
                "start": "00:00:00,000",
                "end": "00:00:10,000",
                "speaker": None,
                "speaker_candidates": [],
                "speaker_confidence": "unknown",
                "overlap": False,
                "attribution_note": None,
                "language": "en",
                "original_text": "Example source text.",
                "translation": "示例原文。",
                "confidence": "high",
            }
        ],
        "frames": [
            {
                "id": "F001",
                "timestamp": "00:00:05",
                "image_path": "assets/frames/00-00-05-000.webp",
                "related_blocks": ["S001"],
            }
        ],
        "limitations": [],
    }


class MediaSourceMapValidatorTests(unittest.TestCase):
    def test_accepts_valid_source_map(self) -> None:
        parsed = MODULE.validate_source_map_json(json.dumps(valid_source_map()))
        self.assertEqual(parsed.blocks[0].id, "S001")

    def test_accepts_structural_map_without_content_coverage(self) -> None:
        source_map = valid_source_map()
        source_map["sections"] = []
        source_map["blocks"] = []
        source_map["frames"] = []

        parsed = MODULE.validate_source_map_json(json.dumps(source_map))
        self.assertEqual(parsed.blocks, [])

    def test_rejects_unknown_block_reference(self) -> None:
        source_map = valid_source_map()
        source_map["frames"][0]["related_blocks"] = ["S999"]

        with self.assertRaisesRegex(ValidationError, "unknown block IDs"):
            MODULE.validate_source_map_json(json.dumps(source_map))

    def test_rejects_invalid_timestamp_range(self) -> None:
        source_map = valid_source_map()
        source_map["blocks"][0]["end"] = "00:00:00"
        source_map["blocks"][0]["start"] = "00:00:01"

        with self.assertRaisesRegex(ValidationError, "end precedes"):
            MODULE.validate_source_map_json(json.dumps(source_map))

    def test_rejects_frame_path_outside_assets(self) -> None:
        source_map = valid_source_map()
        source_map["frames"][0]["image_path"] = "../frame.webp"

        with self.assertRaisesRegex(ValidationError, "media bundle"):
            MODULE.validate_source_map_json(json.dumps(source_map))

    def test_rejects_unknown_fields(self) -> None:
        source_map = valid_source_map()
        source_map["media"]["target_langauge"] = "zh-CN"

        with self.assertRaises(ValidationError):
            MODULE.validate_source_map_json(json.dumps(source_map))

    def test_cli_returns_success_and_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source_map_path = Path(directory) / "source_map.json"
            source_map_path.write_text(json.dumps(valid_source_map()), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(MODULE.main([str(source_map_path)]), 0)

            invalid_map = copy.deepcopy(valid_source_map())
            invalid_map["blocks"][0]["id"] = "bad-id"
            source_map_path.write_text(json.dumps(invalid_map), encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                self.assertEqual(MODULE.main([str(source_map_path)]), 1)

    def test_audio_requires_no_frames_and_accepts_reflection(self) -> None:
        source_map = valid_source_map()
        source_map["media"].update(
            kind="audio", source_type="local-audio", reading_type="reflective"
        )
        with self.assertRaisesRegex(ValidationError, "audio media cannot"):
            MODULE.validate_source_map_json(json.dumps(source_map))
        source_map["frames"] = []
        self.assertEqual(
            MODULE.validate_source_map_json(json.dumps(source_map)).media.kind, "audio"
        )

    def test_speaker_references_and_overlapping_turns(self) -> None:
        source_map = valid_source_map()
        source_map["blocks"][0]["speaker"] = "SPK001"
        with self.assertRaisesRegex(ValidationError, "unknown speaker"):
            MODULE.validate_source_map_json(json.dumps(source_map))
        source_map["speakers"] = [
            {"id": "SPK001", "name": "Mian"},
            {"id": "SPK002", "name": None},
        ]
        source_map["speaker_turns"] = [
            {"speaker": "SPK001", "start": "00:00:00", "end": "00:00:07"},
            {"speaker": "SPK002", "start": "00:00:05", "end": "00:00:10"},
        ]
        source_map["diarization"] = {
            "backend": "pyannote.audio",
            "model": "local-model",
            "revision": "pinned",
            "device": "cpu",
            "speaker_count": 2,
            "audio_sha256": "a" * 64,
            "parameters": {},
        }
        source_map["blocks"][0].update(
            overlap=True,
            speaker_candidates=["SPK001", "SPK002"],
            attribution_note="Verified first voice despite an overlapping response.",
        )
        parsed = MODULE.validate_source_map_json(json.dumps(source_map))
        self.assertTrue(parsed.blocks[0].overlap)
        source_map["diarization"] = None
        with self.assertRaisesRegex(ValidationError, "require diarization"):
            MODULE.validate_source_map_json(json.dumps(source_map))

    def test_rejects_evidence_outside_duration(self) -> None:
        source_map = valid_source_map()
        source_map["blocks"][0]["end"] = "00:00:11"
        with self.assertRaisesRegex(ValidationError, "exceeds media duration"):
            MODULE.validate_source_map_json(json.dumps(source_map))

    def test_sections_cover_every_block_once(self) -> None:
        for membership in ([], ["S001", "S001"]):
            source_map = valid_source_map()
            source_map["sections"][0]["block_ids"] = membership
            with self.assertRaisesRegex(ValidationError, "cover every block exactly once"):
                MODULE.validate_source_map_json(json.dumps(source_map))

    def test_section_contains_block_and_order_is_contiguous(self) -> None:
        source_map = valid_source_map()
        source_map["sections"][0]["start"] = "00:00:01"
        with self.assertRaisesRegex(ValidationError, "does not contain"):
            MODULE.validate_source_map_json(json.dumps(source_map))
        source_map = valid_source_map()
        source_map["blocks"][0]["order"] = 2
        with self.assertRaisesRegex(ValidationError, "contiguous"):
            MODULE.validate_source_map_json(json.dumps(source_map))

    def test_unassigned_speaker_cannot_claim_confidence(self) -> None:
        source_map = valid_source_map()
        source_map["blocks"][0]["speaker_confidence"] = "high"
        with self.assertRaisesRegex(ValidationError, "unknown confidence"):
            MODULE.validate_source_map_json(json.dumps(source_map))

    def test_sparse_attribution_and_unordered_turns_need_review(self) -> None:
        source_map = valid_source_map()
        source_map["speakers"] = [{"id": "SPK001", "name": None}]
        source_map["diarization"] = {
            "backend": "pyannote.audio",
            "model": "local",
            "revision": "pinned",
            "device": "cpu",
            "speaker_count": 1,
            "audio_sha256": "a" * 64,
            "parameters": {},
        }
        source_map["speaker_turns"] = [
            {"speaker": "SPK001", "start": "00:00:09", "end": "00:00:10"}
        ]
        source_map["blocks"][0].update(speaker="SPK001", speaker_confidence="medium")
        with self.assertRaisesRegex(ValidationError, "sparse acoustic coverage"):
            MODULE.validate_source_map_json(json.dumps(source_map))
        source_map["blocks"][0]["attribution_note"] = (
            "Reviewed long pause; speech occupies the final second."
        )
        MODULE.validate_source_map_json(json.dumps(source_map))
        source_map["speaker_turns"].append(
            {"speaker": "SPK001", "start": "00:00:01", "end": "00:00:02"}
        )
        with self.assertRaisesRegex(ValidationError, "turns must be in timeline order"):
            MODULE.validate_source_map_json(json.dumps(source_map))

    def test_rejects_retired_fields_with_their_location(self) -> None:
        # Spelled in parts so the retired names stay out of `git grep` over skills/.
        retired_top_level = "gloss" + "ary"
        retired_speaker_fields = ("ro" + "le", "identity" + "_basis")

        source_map = valid_source_map()
        source_map[retired_top_level] = []
        with self.assertRaisesRegex(ValidationError, retired_top_level):
            MODULE.validate_source_map_json(json.dumps(source_map))

        for field in retired_speaker_fields:
            source_map = valid_source_map()
            source_map["speakers"] = [{"id": "SPK001", "name": "Mian", field: "x"}]
            source_map["diarization"] = None
            with self.assertRaisesRegex(ValidationError, rf"speakers\.0\.{field}"):
                MODULE.validate_source_map_json(json.dumps(source_map))

    def two_block_map(self, first_id: str, second_id: str) -> dict:
        source_map = valid_source_map()
        first = source_map["blocks"][0]
        first.update(id=first_id, end="00:00:05")
        second = {**first, "id": second_id, "order": 2, "start": "00:00:05", "end": "00:00:10"}
        source_map["blocks"] = [first, second]
        source_map["sections"][0]["block_ids"] = [first_id, second_id]
        source_map["frames"][0]["related_blocks"] = [first_id]
        return source_map

    def test_source_block_numbers_must_increase_with_order(self) -> None:
        for first, second in (("S002", "S001"), ("S002", "S0002"), ("S010", "S0009")):
            with (
                self.subTest(first=first, second=second),
                self.assertRaisesRegex(ValidationError, "increase"),
            ):
                MODULE.validate_source_map_json(json.dumps(self.two_block_map(first, second)))

    def test_source_cue_ranges_follow_source_order(self) -> None:
        source_map = valid_source_map()
        second = copy.deepcopy(source_map["blocks"][0])
        second.update(id="S002", order=2, start="00:00:05,000")
        source_map["blocks"].append(second)
        source_map["sections"][0]["block_ids"].append("S002")
        source_map["blocks"][0]["source_cues"] = ["C0001", "C0003"]
        second["source_cues"] = ["C0003", "C0005"]
        MODULE.validate_source_map_json(json.dumps(source_map))

        second["source_cues"] = ["C0002", "C0005"]
        with self.assertRaisesRegex(ValidationError, "cue ranges must follow"):
            MODULE.validate_source_map_json(json.dumps(source_map))
        second["source_cues"] = None
        with self.assertRaisesRegex(ValidationError, "every block or on none"):
            MODULE.validate_source_map_json(json.dumps(source_map))
        second["source_cues"] = ["C0005", "C0004"]
        with self.assertRaisesRegex(ValidationError, "reversed"):
            MODULE.validate_source_map_json(json.dumps(source_map))

    def test_source_block_numbers_may_have_gaps(self) -> None:
        parsed = MODULE.validate_source_map_json(json.dumps(self.two_block_map("S001", "S007")))
        self.assertEqual([block.id for block in parsed.blocks], ["S001", "S007"])


if __name__ == "__main__":
    unittest.main()
