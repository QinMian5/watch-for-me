from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills/media-shared/media-source-map/scripts/summarize_online_source.py"
)
SPEC = importlib.util.spec_from_file_location("summarize_online_source", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

SIGNED = "https://media.example/videoplayback?signature=SECRET"


def source_info() -> dict:
    def track(ext: str) -> dict:
        return {"ext": ext, "url": SIGNED}

    return {
        "id": "abc123",
        "title": "Example talk",
        "extractor": "youtube",
        "webpage_url": "https://www.youtube.com/watch?v=abc123",
        "duration": 1758,
        "language": "en-US",
        "availability": "public",
        "license": "Creative Commons Attribution license (reuse allowed)",
        "description": "x" * 900,
        "chapters": [{"start_time": 0.0, "end_time": 60.0, "title": "Intro"}],
        "thumbnails": [{"url": SIGNED}],
        "subtitles": {"en": [track("vtt")], "fr": [track("vtt")]},
        "automatic_captions": {
            "en-orig": [track("vtt"), track("srt")],
            "en": [track("vtt")],
            "de": [track("vtt")],
            "ja": [track("vtt")],
        },
        "formats": [
            {"format_id": "sb0", "ext": "mhtml", "format_note": "storyboard", "url": SIGNED},
            {
                "format_id": "140-0",
                "ext": "m4a",
                "vcodec": "none",
                "acodec": "mp4a.40.2",
                "language": "de-DE",
                "format_note": "German (DE), medium",
                "url": SIGNED,
            },
            {
                "format_id": "233-0",
                "ext": "mp4",
                "vcodec": "none",
                "acodec": None,
                "language": "ja",
                "format_note": "日本語 - dubbed-auto",
                "url": SIGNED,
            },
            {
                "format_id": "140-17",
                "ext": "m4a",
                "vcodec": "none",
                "acodec": "mp4a.40.2",
                "abr": 129.5,
                "language": "en-US",
                "format_note": "English (US) original (default), medium",
                "filesize": 28451100,
                "url": SIGNED,
                "http_headers": {"User-Agent": "x"},
            },
            {
                "format_id": "136",
                "ext": "mp4",
                "vcodec": "avc1.64001F",
                "acodec": "none",
                "resolution": "1280x720",
                "fps": 30,
                "filesize_approx": 41832073,
                "url": SIGNED,
            },
        ],
    }


class SummarizeOnlineSourceTests(unittest.TestCase):
    def test_keeps_identity_and_original_language_candidates(self) -> None:
        summary = MODULE.summarize(source_info())

        self.assertEqual(summary["id"], "abc123")
        self.assertEqual(summary["duration"], 1758)
        self.assertEqual(summary["license"], source_info()["license"])
        self.assertEqual(summary["subtitles"]["manual"], {"en": ["vtt"]})
        self.assertEqual(
            summary["subtitles"]["automatic"], {"en-orig": ["vtt", "srt"], "en": ["vtt"]}
        )
        self.assertEqual(
            summary["subtitles"]["omitted_other_languages"], {"manual": 1, "automatic": 2}
        )
        self.assertEqual(summary["chapters"], [{"start": 0.0, "title": "Intro"}])

    def test_keeps_original_audio_and_video_formats_without_urls(self) -> None:
        summary = MODULE.summarize(source_info())
        formats = summary["formats"]

        self.assertEqual([f["format_id"] for f in formats["audio"]], ["140-17"])
        self.assertEqual([f["format_id"] for f in formats["video"]], ["136"])
        self.assertEqual(formats["omitted"], {"storyboard": 1, "other_language_audio": 2})
        self.assertEqual(formats["audio"][0]["filesize"], 28451100)
        self.assertEqual(formats["video"][0]["filesize"], 41832073)
        self.assertNotIn("signature", json.dumps(summary))
        self.assertNotIn("http_headers", json.dumps(summary))

    def test_unknown_language_keeps_every_candidate(self) -> None:
        info = source_info()
        info["language"] = None

        summary = MODULE.summarize(info)

        self.assertEqual(len(summary["subtitles"]["automatic"]), 4)
        self.assertEqual(summary["formats"]["omitted"]["other_language_audio"], 1)

    def test_undetermined_language_keeps_every_candidate(self) -> None:
        info = source_info()
        info["language"] = "und"

        summary = MODULE.summarize(info)

        self.assertEqual(len(summary["subtitles"]["automatic"]), 4)
        self.assertEqual(summary["formats"]["omitted"]["other_language_audio"], 1)

    def test_undetermined_audio_track_is_kept_for_known_language(self) -> None:
        info = source_info()
        info["formats"].append(
            {"format_id": "a-und", "ext": "m4a", "vcodec": "none", "language": "und"}
        )

        audio = MODULE.summarize(info)["formats"]["audio"]

        self.assertIn("a-und", [f["format_id"] for f in audio])

    def test_single_format_source_uses_top_level_format(self) -> None:
        info = {
            "id": "clip",
            "title": "Direct clip",
            "format_id": "mp4",
            "ext": "mp4",
            "vcodec": "h264",
            "acodec": "aac",
            "url": SIGNED,
        }

        formats = MODULE.summarize(info)["formats"]

        self.assertEqual([f["format_id"] for f in formats["video"]], ["mp4"])
        self.assertNotIn("signature", json.dumps(formats))

    def test_truncates_long_description(self) -> None:
        summary = MODULE.summarize(source_info())

        self.assertEqual(len(summary["description"]), MODULE.DESCRIPTION_LIMIT)
        self.assertTrue(summary["description_truncated"])

    def test_main_prints_one_compact_json_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.json"
            path.write_text(json.dumps(source_info()), encoding="utf-8")
            stdout = io.StringIO()
            argv = ["summarize_online_source.py", str(path)]
            with mock.patch.object(sys, "argv", argv), redirect_stdout(stdout):
                code = MODULE.main()

        self.assertEqual(code, 0)
        self.assertEqual(len(stdout.getvalue().strip().splitlines()), 1)
        self.assertEqual(json.loads(stdout.getvalue())["title"], "Example talk")


if __name__ == "__main__":
    unittest.main()
