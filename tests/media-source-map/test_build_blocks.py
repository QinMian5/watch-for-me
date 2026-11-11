from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills/media-shared/media-source-map/scripts/build_blocks.py"
)
SPEC = importlib.util.spec_from_file_location("build_blocks", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def cue(number: int, start: int, end: int, text: str, timed: bool = False) -> dict:
    item = {"id": f"C{number:04d}", "offsets": {"from": start, "to": end}, "text": text}
    if timed:
        words = text.split()
        step = (end - start) // len(words)
        item["words"] = [
            {
                "text": word,
                "from": start + i * step,
                "to": start + (i + 1) * step if i + 1 < len(words) else end,
            }
            for i, word in enumerate(words)
        ]
    return item


# A sentence split across cues, an interjection inside a cue, then the first speaker again.
CUES = [
    cue(1, 0, 2000, "so the protocol started", timed=True),
    cue(2, 2000, 4000, "as a small idea right yeah", timed=True),
    cue(3, 4000, 6000, "and then it grew", timed=True),
]
PLAN = {
    "blocks": [
        {"start": "C0001", "speaker": "SPK001"},
        {"start": "C0002@4", "speaker": "SPK002"},
        {"start": "C0003", "speaker": "SPK001"},
    ]
}


class BuildBlocksTests(unittest.TestCase):
    def test_assembles_word_split_blocks_with_cue_ranges(self) -> None:
        blocks = MODULE.assemble(PLAN, CUES, MODULE.tokenize(CUES))
        self.assertEqual(
            [(b["id"], b["original_text"], b["source_cues"], b["speaker"]) for b in blocks],
            [
                ("S001", "so the protocol started as a small idea", ["C0001", "C0002"], "SPK001"),
                ("S002", "right yeah", ["C0002", "C0002"], "SPK002"),
                ("S003", "and then it grew", ["C0003", "C0003"], "SPK001"),
            ],
        )
        self.assertEqual((blocks[1]["start"], blocks[1]["end"]), ("00:00:03.332", "00:00:04.000"))

    def test_same_cues_and_plan_assemble_identically(self) -> None:
        tokens = MODULE.tokenize(CUES)
        self.assertEqual(MODULE.assemble(PLAN, CUES, tokens), MODULE.assemble(PLAN, CUES, tokens))

    def test_cue_timed_split_shares_the_cue_range(self) -> None:
        cues = [cue(1, 1000, 3000, "we shipped it. >> really?")]
        plan = {"blocks": [{"start": "C0001"}, {"start": "C0001@3"}]}
        first, second = MODULE.assemble(plan, cues, MODULE.tokenize(cues))
        self.assertEqual((first["start"], first["end"]), ("00:00:01.000", "00:00:03.000"))
        self.assertEqual((second["start"], second["end"]), ("00:00:01.000", "00:00:03.000"))

    def test_rejects_plans_that_skip_or_reorder_text(self) -> None:
        tokens = MODULE.tokenize(CUES)
        for blocks, message in [
            ([{"start": "C0002"}], "first block"),
            ([{"start": "C0001"}, {"start": "C0003"}, {"start": "C0002"}], "strictly increase"),
            ([{"start": "C0001"}, {"start": "C0002@9"}], "past the cue"),
            ([{"start": "C0001", "speaker": "Alice"}], "invalid speaker"),
        ]:
            with self.subTest(message), self.assertRaisesRegex(ValueError, message):
                MODULE.assemble({"blocks": blocks}, CUES, tokens)

    def test_draft_breaks_at_certain_speaker_changes_and_markers(self) -> None:
        cues = [
            cue(1, 0, 1000, "first speaker talks"),
            cue(2, 1000, 2000, "still first speaker"),
            cue(3, 2000, 3000, "second voice answers"),
            cue(4, 3000, 4000, "overlapping words here"),
            cue(5, 4000, 5000, ">> a marked change"),
        ]
        alignment = {
            "segments": [
                {"cue": "C0001", "speaker": "SPK001"},
                {"cue": "C0002", "speaker": "SPK001"},
                {"cue": "C0003", "speaker": "SPK002"},
                {"cue": "C0004", "speaker": None, "overlap": True},
                {"cue": "C0005", "speaker": None},
            ]
        }
        plan = MODULE.draft(cues, MODULE.tokenize(cues), alignment)
        self.assertEqual(
            [(b["start"], b["speaker"], b["reason"]) for b in plan["blocks"]],
            [
                ("C0001", "SPK001", "start"),
                ("C0003", "SPK002", "speaker"),
                ("C0005", None, "marker"),
            ],
        )

    def test_draft_keeps_the_cue_speaker_across_a_split_inside_it(self) -> None:
        first = " ".join(["word"] * 70) + " ends here. then more words"
        cues = [cue(1, 0, 20000, first), cue(2, 20000, 21000, "the other voice")]
        alignment = {
            "segments": [
                {"cue": "C0001", "speaker": "SPK001"},
                {"cue": "C0002", "speaker": "SPK002"},
            ]
        }
        plan = MODULE.draft(cues, MODULE.tokenize(cues), alignment)
        self.assertEqual(
            [(b["start"], b["speaker"], b["reason"]) for b in plan["blocks"]],
            [
                ("C0001", "SPK001", "start"),
                ("C0001@72", "SPK001", "sentence"),
                ("C0002", "SPK002", "speaker"),
            ],
        )

    def test_draft_keeps_an_internal_marker_unassigned(self) -> None:
        cues = [cue(1, 0, 3000, "hello >> really now")]
        alignment = {"segments": [{"cue": "C0001", "speaker": "SPK001"}]}
        plan = MODULE.draft(cues, MODULE.tokenize(cues), alignment)
        self.assertEqual(
            [(b["start"], b["speaker"]) for b in plan["blocks"]],
            [("C0001", "SPK001"), ("C0001@1", None)],
        )

    def test_draft_waits_for_a_sentence_end_or_pause_past_the_minimum(self) -> None:
        long_text = " ".join(["word"] * 70)
        cues = [
            cue(1, 0, 20000, long_text + " ends here."),
            cue(2, 20000, 21000, "Next sentence"),
            cue(3, 21000, 22000, "continues without stopping"),
        ]
        plan = MODULE.draft(cues, MODULE.tokenize(cues), None)
        self.assertEqual([b["start"] for b in plan["blocks"]], ["C0001", "C0002"])
        self.assertEqual(plan["blocks"][1]["reason"], "sentence")

    def test_preview_flags_cues_that_need_speaker_review(self) -> None:
        alignment = {
            "segments": [
                {"cue": "C0001", "speaker": "SPK001", "needs_review": False},
                {
                    "cue": "C0002",
                    "speaker": None,
                    "speaker_candidates": ["SPK001", "SPK002"],
                    "needs_review": True,
                },
                {"cue": "C0003", "speaker": None, "speaker_candidates": [], "needs_review": True},
            ]
        }
        lines = MODULE.preview(
            PLAN, CUES, MODULE.tokenize(CUES), MODULE.review_cues(alignment)
        ).splitlines()
        self.assertEqual(
            lines,
            [
                "S001 C0001 00:00:00.000 SPK001 8w review C0002(SPK001/SPK002)"
                " | so the protocol started as a small idea",
                "S002 C0002@4 00:00:03.332 SPK002 2w review C0002(SPK001/SPK002) | right yeah",
                "S003 C0003 00:00:04.000 SPK001 4w review C0003(-) | and then it grew",
            ],
        )

    def test_preview_shortens_long_blocks_unless_full(self) -> None:
        text = " ".join(f"w{i}" for i in range(20))
        cues = [cue(1, 0, 1000, text)]
        plan = {"blocks": [{"start": "C0001"}]}
        tokens = MODULE.tokenize(cues)
        self.assertTrue(
            MODULE.preview(plan, cues, tokens).endswith(
                "| w0 w1 w2 w3 w4 w5 w6 w7 … w12 w13 w14 w15 w16 w17 w18 w19"
            )
        )
        self.assertTrue(MODULE.preview(plan, cues, tokens, full=True).endswith(f"| {text}"))


if __name__ == "__main__":
    unittest.main()
