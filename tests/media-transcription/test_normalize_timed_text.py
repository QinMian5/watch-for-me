import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "skills/media-shared/media-transcription/scripts"
sys.path.insert(0, str(SCRIPTS))
normalize = importlib.import_module("normalize_timed_text").normalize
align = importlib.import_module("align_speakers").align

ROLLING_VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.000 --> 00:00:02.310 align:start position:0%
\x20
hello<00:00:00.560><c> everyone</c><00:00:00.960><c> welcome</c>

00:00:02.310 --> 00:00:02.320 align:start position:0%
hello everyone welcome
\x20

00:00:02.320 --> 00:00:05.000 align:start position:0%
hello everyone welcome
to<00:00:02.800><c> the</c><00:00:03.100><c> show</c>

00:00:05.000 --> 00:00:05.010 align:start position:0%
to the show
\x20

00:00:05.010 --> 00:00:06.000 align:start position:0%
to the show
[Music]
"""

SRT = """1
00:00:01,000 --> 00:00:03,000
<i>We built the server</i>

2
00:00:03,000 --> 00:00:05,500
and then we
shipped it.

3
00:00:05,500 --> 00:00:06,000
shipped it.
&gt;&gt; Really?
"""


class NormalizeTimedTextTests(unittest.TestCase):
    def run_normalize(self, name: str, content: str) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / name
            path.write_text(content, encoding="utf-8")
            return normalize(path)

    def test_rolling_captions_keep_each_word_once_with_word_times(self) -> None:
        result = self.run_normalize("captions.en.vtt", ROLLING_VTT)
        cues = result["transcription"]
        self.assertEqual([cue["id"] for cue in cues], ["C0001", "C0002"])
        self.assertEqual([cue["text"] for cue in cues], ["hello everyone welcome", "to the show"])
        self.assertEqual(result["timing"], "word")
        self.assertEqual(result["non_speech_cues_removed"], 1)
        self.assertEqual(
            [(w["text"], w["from"], w["to"]) for w in cues[1]["words"]],
            [("to", 2320, 2800), ("the", 2800, 3100), ("show", 3100, 5000)],
        )

    def test_text_split_from_its_timing_line_stays_with_the_cue(self) -> None:
        stripped = ROLLING_VTT.replace("\x20\n", "\n")
        self.assertEqual(
            self.run_normalize("a.vtt", stripped)["transcription"],
            self.run_normalize("a.vtt", ROLLING_VTT)["transcription"],
        )

    def test_whitespace_only_separators_and_notes_do_not_merge_cues(self) -> None:
        srt = "1\n00:00:00,000 --> 00:00:01,000\nHi\n \n2\n00:00:01,000 --> 00:00:02,000\nBye\n\t\n"
        self.assertEqual(
            [(c["text"], c["offsets"]) for c in self.run_normalize("ws.srt", srt)["transcription"]],
            [("Hi", {"from": 0, "to": 1000}), ("Bye", {"from": 1000, "to": 2000})],
        )
        vtt = (
            "WEBVTT\n\nNOTE checked by hand\nsecond note line\n\n"
            "intro\n00:00:00.000 --> 00:00:01.000\nHello\n\n"
            "NOTE between cues\n\n00:00:01.000 --> 00:00:02.000\nWorld\n"
        )
        self.assertEqual(
            [c["text"] for c in self.run_normalize("notes.vtt", vtt)["transcription"]],
            ["Hello", "World"],
        )

    def test_srt_without_word_times_keeps_cue_precision(self) -> None:
        cues = self.run_normalize("sidecar.srt", SRT)["transcription"]
        self.assertEqual(
            [cue["text"] for cue in cues],
            ["We built the server", "and then we shipped it.", "shipped it. >> Really?"],
        )
        self.assertNotIn("words", cues[0])
        self.assertEqual(cues[2]["offsets"], {"from": 5500, "to": 6000})

    def test_speech_said_again_is_kept_without_rolling_timing(self) -> None:
        content = (
            "1\n00:00:01,000 --> 00:00:02,000\nThank you.\n\n"
            "2\n00:00:20,000 --> 00:00:21,000\nThank you.\n\n"
            "3\n00:00:21,000 --> 00:00:22,000\nThank you.\n\n"
            "4\n00:00:30,000 --> 00:00:32,000\nThank you.\nAnd goodbye.\n"
        )
        result = self.run_normalize("repeat.srt", content)
        self.assertEqual(
            [cue["text"] for cue in result["transcription"]],
            ["Thank you.", "Thank you.", "Thank you.", "Thank you. And goodbye."],
        )
        self.assertEqual(result["repeated_lines_removed"], 0)

    def test_only_short_sound_labels_are_removed(self) -> None:
        texts = [
            "(Laughter)",
            "[Music]",
            "♪ ♪",
            "(sighs heavily)",
            "(I never said that.)",
            "[inaudible 00:12]",
            "(No.)",
        ]
        content = "".join(
            f"{i}\n00:00:{i:02d},000 --> 00:00:{i:02d},500\n{text}\n\n"
            for i, text in enumerate(texts, start=1)
        )
        result = self.run_normalize("labels.srt", content)
        self.assertEqual(
            [cue["text"] for cue in result["transcription"]],
            ["(I never said that.)", "[inaudible 00:12]", "(No.)"],
        )
        self.assertEqual(result["non_speech_cues_removed"], 4)

    def test_a_track_without_rolling_transitions_keeps_repeated_lines(self) -> None:
        content = (
            "1\n00:00:01,000 --> 00:00:02,000\nNo.\n\n"
            "2\n00:00:02,000 --> 00:00:04,000\nNo.\nI disagree.\n"
        )
        result = self.run_normalize("plain.srt", content)
        self.assertEqual(
            [cue["text"] for cue in result["transcription"]], ["No.", "No. I disagree."]
        )

    def test_inline_timestamps_carry_across_lines_of_a_cue(self) -> None:
        content = (
            "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n"
            "Hello<00:00:02.000> there\nfriend<00:00:03.000> again\n"
        )
        cue = self.run_normalize("lines.vtt", content)["transcription"][0]
        self.assertEqual(
            [(w["text"], w["from"], w["to"]) for w in cue["words"]],
            [
                ("Hello", 1000, 2000),
                ("there", 2000, 2000),
                ("friend", 2000, 3000),
                ("again", 3000, 5000),
            ],
        )

    def test_backward_inline_timestamps_fall_back_to_cue_timing(self) -> None:
        content = (
            "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nHello<00:00:04.000> there<00:00:02.000> now\n"
        )
        result = self.run_normalize("backward.vtt", content)
        self.assertNotIn("words", result["transcription"][0])
        self.assertEqual(result["timing"], "cue")

    def test_whisper_json_is_numbered_without_changing_text(self) -> None:
        payload = {
            "transcription": [
                {"offsets": {"from": 0, "to": 900}, "text": " So  it begins"},
                {"offsets": {"from": 900, "to": 1500}, "text": "   "},
                {"offsets": {"from": 1500, "to": 2000}, "text": " again"},
            ]
        }
        result = self.run_normalize("transcript.json", json.dumps(payload))
        self.assertEqual(result["timing"], "cue")
        self.assertEqual(
            [(cue["id"], cue["text"]) for cue in result["transcription"]],
            [("C0001", "So it begins"), ("C0002", "again")],
        )

    def test_repeated_runs_are_identical(self) -> None:
        self.assertEqual(
            self.run_normalize("a.vtt", ROLLING_VTT), self.run_normalize("a.vtt", ROLLING_VTT)
        )

    def test_rejects_out_of_order_cues(self) -> None:
        content = "00:00:05.000 --> 00:00:06.000\nlater\n\n00:00:01.000 --> 00:00:02.000\nearlier\n"
        with self.assertRaisesRegex(ValueError, "out of order"):
            self.run_normalize("bad.vtt", "WEBVTT\n\n" + content)

    def test_alignment_reports_the_cue_id(self) -> None:
        cues = self.run_normalize("sidecar.srt", SRT)
        diarization = {
            "duration_seconds": 6,
            "audio_sha256": "abc",
            "speakers": ["SPK001"],
            "turns": [{"start": 0, "end": 6, "speaker": "SPK001"}],
            "exclusive_turns": [],
        }
        segments = align(cues, diarization)["segments"]
        self.assertEqual([segment["cue"] for segment in segments], ["C0001", "C0002", "C0003"])


if __name__ == "__main__":
    unittest.main()
