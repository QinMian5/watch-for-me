from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills/media-shared/media-transcription/scripts/transcribe_faster_whisper.py"
)
SPEC = importlib.util.spec_from_file_location("transcribe_faster_whisper", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FasterWhisperAdapterTests(unittest.TestCase):
    def test_timestamp_includes_hours_and_milliseconds(self) -> None:
        self.assertEqual(MODULE.milliseconds_to_timestamp(3_661_001), "01:01:01,001")

    def test_normalizes_segments_without_changing_text(self) -> None:
        segments = [
            SimpleNamespace(start=0.0, end=1.25, text=" Hello"),
            SimpleNamespace(start=1.25, end=2.0, text="世界"),
        ]
        normalized = MODULE.normalize_segments(segments)
        self.assertEqual(normalized[0]["text"], " Hello")
        self.assertEqual(normalized[0]["offsets"], {"from": 0, "to": 1250})
        self.assertEqual(normalized[1]["timestamps"]["to"], "00:00:02,000")

    def test_rejects_out_of_order_segments(self) -> None:
        segments = [
            SimpleNamespace(start=2.0, end=3.0, text="later"),
            SimpleNamespace(start=1.0, end=2.0, text="earlier"),
        ]
        with self.assertRaisesRegex(ValueError, "out of order"):
            MODULE.normalize_segments(segments)

    def test_writes_matching_json_and_srt(self) -> None:
        segments = [SimpleNamespace(start=0.0, end=1.25, text=" Hello")]
        info = SimpleNamespace(
            language="en",
            language_probability=0.99,
            duration=1.25,
            duration_after_vad=1.25,
        )
        payload = MODULE.build_payload(
            input_path=Path("sample.wav"),
            segments=segments,
            info=info,
            model="large-v3-turbo",
            device="cpu",
            compute_type="int8",
            quality="balanced",
        )

        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "transcript"
            json_path, srt_path = MODULE.write_outputs(prefix, payload)
            parsed = json.loads(json_path.read_text(encoding="utf-8"))
            srt = srt_path.read_text(encoding="utf-8")

        self.assertEqual(parsed["transcription"][0]["text"], " Hello")
        self.assertIn("00:00:00,000 --> 00:00:01,250", srt)
        self.assertTrue(srt.endswith("\n"))

    def test_transcribe_passes_runtime_configuration(self) -> None:
        class FakeWhisperModel:
            init_args: Any = None
            transcribe_args: Any = None

            def __init__(self, model: str, **kwargs: object) -> None:
                self.__class__.init_args = (model, kwargs)

            def transcribe(
                self, input_path: str, **kwargs: object
            ) -> tuple[list[SimpleNamespace], SimpleNamespace]:
                self.__class__.transcribe_args = (input_path, kwargs)
                segments = [SimpleNamespace(start=0.0, end=1.0, text=" test")]
                info = SimpleNamespace(
                    language="en",
                    language_probability=0.9,
                    duration=1.0,
                    duration_after_vad=1.0,
                )
                return segments, info

        fake_module = SimpleNamespace(WhisperModel=FakeWhisperModel)
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            input_path = directory_path / "sample.wav"
            input_path.write_bytes(b"test")
            args = SimpleNamespace(
                input_path=input_path,
                output_prefix=directory_path / "transcript",
                model="large-v3-turbo",
                model_cache=directory_path / "model-cache",
                device="cuda",
                compute_type="float16",
                quality="balanced",
            )
            with patch.dict(sys.modules, {"faster_whisper": fake_module}):
                json_path, srt_path = MODULE.transcribe(args)

            self.assertTrue(json_path.is_file())
            self.assertTrue(srt_path.is_file())

        self.assertEqual(
            FakeWhisperModel.init_args,
            (
                "large-v3-turbo",
                {
                    "device": "cuda",
                    "compute_type": "float16",
                    "download_root": str(directory_path / "model-cache"),
                },
            ),
        )
        self.assertEqual(
            FakeWhisperModel.transcribe_args[1],
            {"task": "transcribe", "beam_size": 5, "vad_filter": True},
        )


if __name__ == "__main__":
    unittest.main()
