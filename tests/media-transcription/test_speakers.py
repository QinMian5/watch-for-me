import importlib
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

SCRIPTS = Path(__file__).resolve().parents[2] / "skills/media-shared/media-transcription/scripts"
sys.path.insert(0, str(SCRIPTS))
align = importlib.import_module("align_speakers").align
diarize = importlib.import_module("diarize")
build_result = diarize.build_result
speaker_options = diarize.speaker_options


class SpeakerTests(unittest.TestCase):
    def dia(self, turns: list[dict]) -> dict:
        return {
            "duration_seconds": 10,
            "audio_sha256": "abc",
            "speakers": ["SPK001", "SPK002"],
            "turns": turns,
            "exclusive_turns": [],
        }

    def transcript(self, start: int = 0, end: int = 10000) -> dict:
        return {
            "transcription": [
                {"offsets": {"from": start, "to": end}, "text": "Exact original text."}
            ]
        }

    def test_known_count_overrides_bounds(self) -> None:
        self.assertEqual(speaker_options(2, 3, 5), {"num_speakers": 2})
        self.assertEqual(speaker_options(None, None, None), {})
        with self.assertRaises(ValueError):
            speaker_options(None, 5, 2)

    def test_single_voice(self) -> None:
        result = align(self.transcript(), self.dia([{"start": 0, "end": 10, "speaker": "SPK001"}]))
        self.assertEqual(result["segments"][0]["speaker"], "SPK001")
        self.assertFalse(result["segments"][0]["needs_review"])

    def test_cross_speaker_text_is_not_majority_assigned(self) -> None:
        result = align(
            self.transcript(),
            self.dia(
                [
                    {"start": 0, "end": 9, "speaker": "SPK001"},
                    {"start": 9, "end": 10, "speaker": "SPK002"},
                ]
            ),
        )
        self.assertIsNone(result["segments"][0]["speaker"])
        self.assertEqual(result["segments"][0]["text"], "Exact original text.")
        self.assertFalse(result["segments"][0]["overlap"])

    def test_regular_overlap_survives_exclusive_view(self) -> None:
        dia = self.dia(
            [
                {"start": 0, "end": 10, "speaker": "SPK001"},
                {"start": 4, "end": 5, "speaker": "SPK002"},
            ]
        )
        dia["exclusive_turns"] = [{"start": 0, "end": 10, "speaker": "SPK001"}]
        item = align(self.transcript(), dia)["segments"][0]
        self.assertTrue(item["overlap"])
        self.assertIsNone(item["speaker"])
        self.assertEqual(item["speech_coverage"], 1.0)

    def test_uncovered_speech_is_uncertain(self) -> None:
        item = align(self.transcript(), self.dia([]))["segments"][0]
        self.assertTrue(item["needs_review"])
        self.assertEqual(item["speaker_candidates"], [])

    def test_wrong_timeline_rejected(self) -> None:
        with self.assertRaises(ValueError):
            align(self.transcript(end=12000), self.dia([]))

    def test_small_asr_overshoot_is_clamped(self) -> None:
        item = align(self.transcript(end=10080), self.dia([]))["segments"][0]
        self.assertEqual(item["end"], 10)
        self.assertEqual(item["text"], "Exact original text.")

    def test_zero_duration_text_requires_review(self) -> None:
        item = align(self.transcript(start=5000, end=5000), self.dia([]))["segments"][0]
        self.assertTrue(item["needs_review"])
        self.assertIsNone(item["speaker"])

    def test_exclusive_view_is_clipped_and_retained(self) -> None:
        dia = self.dia([])
        dia["exclusive_turns"] = [{"start": 0, "end": 10, "speaker": "SPK001"}]
        item = align(self.transcript(start=2000, end=3000), dia)["segments"][0]
        self.assertEqual(item["exclusive_evidence"], [{"start": 2, "end": 3, "speaker": "SPK001"}])
        self.assertIsNone(item["speaker"])

    def test_output_ids_follow_first_appearance(self) -> None:
        def turn(start: float, end: float) -> SimpleNamespace:
            return SimpleNamespace(start=start, end=end)

        output = SimpleNamespace(
            speaker_diarization=[(turn(3, 5), "B"), (turn(0, 3), "A")],
            exclusive_speaker_diarization=[(turn(0, 3), "A"), (turn(3, 5), "B")],
        )
        result = build_result(output, 5, "model", "revision", "cpu", {}, "abc")
        self.assertEqual([t["speaker"] for t in result["turns"]], ["SPK001", "SPK002"])


if __name__ == "__main__":
    unittest.main()
