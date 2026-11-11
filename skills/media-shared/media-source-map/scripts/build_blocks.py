#!/usr/bin/env python3
"""Turn normalized cues into source blocks through a small, editable block plan.

  draft     cues (+ alignment) -> plan with suggested block starts; prints every block in full
  preview   cues + plan (+ alignment) -> each block's first and last words, after editing the plan
  assemble  cues + plan -> blocks with S IDs, times, cue ranges, and raw original text

A plan lists where each block starts, as `C0012` or `C0012@3` (the cue's fourth word),
and its speaker. Each block runs to the next block's start, so every cue word lands in
exactly one block. The same cues and plan always assemble to the same blocks. With the
alignment, each printed block names its cues that need speaker review and their voices.
"""

from __future__ import annotations

import argparse
import json
import re
from itertools import pairwise
from pathlib import Path
from typing import Any, NamedTuple

REF = re.compile(r"^(C\d{4,})(?:@(\d+))?$")
SPEAKER = re.compile(r"^SPK\d{3,}$")
SENTENCE_END = re.compile("[.?!\u2026\u3002\uff1f\uff01]['\"\u201d\u2019)\\]]*$")
CLAUSE_END = re.compile("[,;:\u2014\uff0c\uff1b\u3001]$")
MIN_CHARS, MAX_CHARS, PAUSE_MS = 300, 1000, 1000


class Token(NamedTuple):
    cue: int
    index: int
    text: str
    start: int
    end: int


def format_time(milliseconds: int) -> str:
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_cues(path: Path) -> list[dict[str, Any]]:
    cues = load_json(path).get("transcription")
    if not isinstance(cues, list) or not cues or any("id" not in cue for cue in cues):
        raise ValueError("cues must come from normalize_timed_text.py")
    return cues


def tokenize(cues: list[dict[str, Any]]) -> list[Token]:
    tokens = []
    for cue_index, cue in enumerate(cues):
        words = cue.get("words")
        if words:
            tokens.extend(
                Token(cue_index, i, w["text"], w["from"], w["to"]) for i, w in enumerate(words)
            )
        else:
            start, end = cue["offsets"]["from"], cue["offsets"]["to"]
            tokens.extend(
                Token(cue_index, i, text, start, end) for i, text in enumerate(cue["text"].split())
            )
    return tokens


def resolve_starts(
    plan: dict[str, Any], cues: list[dict[str, Any]], tokens: list[Token]
) -> list[int]:
    entries = plan.get("blocks")
    if not isinstance(entries, list) or not entries:
        raise ValueError("plan must contain a non-empty blocks array")
    cue_index = {cue["id"]: index for index, cue in enumerate(cues)}
    flat = {(token.cue, token.index): position for position, token in enumerate(tokens)}
    starts = []
    for entry in entries:
        match = REF.match(str(entry.get("start", "")))
        if not match or match.group(1) not in cue_index:
            raise ValueError(f"unknown block start {entry.get('start')!r}")
        key = (cue_index[match.group(1)], int(match.group(2) or 0))
        if key not in flat:
            raise ValueError(f"block start {entry['start']} points past the cue's words")
        speaker = entry.get("speaker")
        if speaker is not None and not SPEAKER.match(str(speaker)):
            raise ValueError(f"block at {entry['start']} has an invalid speaker {speaker!r}")
        starts.append(flat[key])
    if starts[0] != 0:
        raise ValueError(f"the first block must start at {cues[0]['id']}")
    if any(left >= right for left, right in pairwise(starts)):
        raise ValueError("block starts must strictly increase")
    return starts


def ref(token: Token, cues: list[dict[str, Any]]) -> str:
    cue_id = cues[token.cue]["id"]
    return f"{cue_id}@{token.index}" if token.index else cue_id


def draft(
    cues: list[dict[str, Any]], tokens: list[Token], alignment: dict[str, Any] | None
) -> dict[str, Any]:
    hints: dict[str, str] = {}
    for segment in (alignment or {}).get("segments", []):
        if segment.get("cue") and segment.get("speaker"):
            hints[segment["cue"]] = segment["speaker"]
    blocks = [{"start": cues[0]["id"], "speaker": hints.get(cues[0]["id"]), "reason": "start"}]
    size = len(tokens[0].text)
    for previous, token in pairwise(tokens):
        new_cue = token.cue != previous.cue
        hint = hints.get(cues[token.cue]["id"])
        current = blocks[-1]["speaker"]
        reason = None
        if new_cue and hint and current and hint != current:
            reason = "speaker"
        elif token.text.startswith(">>"):
            reason = "marker"
        elif size >= MIN_CHARS and SENTENCE_END.search(previous.text):
            reason = "sentence"
        elif size >= MIN_CHARS and token.start - previous.end >= PAUSE_MS:
            reason = f"pause {(token.start - previous.end) / 1000:.1f}s"
        elif (
            size >= MAX_CHARS
            and (CLAUSE_END.search(previous.text) or token.start - previous.end >= 300)
        ) or size >= MAX_CHARS * 1.5:
            reason = "length"
        if reason:
            # A marker inside a cue changes voice within that cue's acoustic evidence.
            speaker = None if reason == "marker" and not new_cue else hint
            blocks.append({"start": ref(token, cues), "speaker": speaker, "reason": reason})
            size = 0
        elif new_cue and hint and not current:
            blocks[-1]["speaker"] = hint
        size += len(token.text) + 1
    return {"blocks": blocks}


def spans(starts: list[int], total: int) -> list[tuple[int, int]]:
    return list(zip(starts, [*starts[1:], total], strict=True))


def assemble(plan: dict[str, Any], cues: list[dict[str, Any]], tokens: list[Token]) -> list[dict]:
    starts = resolve_starts(plan, cues, tokens)
    blocks = []
    for order, ((first, stop), entry) in enumerate(
        zip(spans(starts, len(tokens)), plan["blocks"], strict=True), start=1
    ):
        words = tokens[first:stop]
        blocks.append(
            {
                "id": f"S{order:03d}",
                "order": order,
                "start": format_time(words[0].start),
                "end": format_time(max(word.end for word in words)),
                "speaker": entry.get("speaker"),
                "source_cues": [cues[words[0].cue]["id"], cues[words[-1].cue]["id"]],
                "original_text": " ".join(word.text for word in words),
            }
        )
    return blocks


def review_cues(alignment: dict[str, Any] | None) -> dict[str, list[str]]:
    """Cue IDs the alignment leaves for speaker review, with their candidate voices."""
    return {
        segment["cue"]: segment.get("speaker_candidates", [])
        for segment in (alignment or {}).get("segments", [])
        if segment.get("cue") and segment.get("needs_review")
    }


def preview(
    plan: dict[str, Any],
    cues: list[dict[str, Any]],
    tokens: list[Token],
    review: dict[str, list[str]] | None = None,
    full: bool = False,
) -> str:
    starts = resolve_starts(plan, cues, tokens)
    review = review or {}
    lines = []
    for order, ((first, stop), entry) in enumerate(
        zip(spans(starts, len(tokens)), plan["blocks"], strict=True), start=1
    ):
        words = [token.text for token in tokens[first:stop]]
        short = full or len(words) <= 16
        text = " ".join(words if short else [*words[:8], "…", *words[-8:]])
        reason = f" [{entry['reason']}]" if entry.get("reason") else ""
        block_cues = dict.fromkeys(cues[token.cue]["id"] for token in tokens[first:stop])
        flagged = [f"{c}({'/'.join(review[c]) or '-'})" for c in block_cues if c in review]
        flags = f" review {' '.join(flagged)}" if flagged else ""
        lines.append(
            f"S{order:03d} {entry['start']} {format_time(tokens[first].start)} "
            f"{entry.get('speaker') or '-'} {len(words)}w{reason}{flags} | {text}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    commands = parser.add_subparsers(dest="command", required=True)
    draft_parser = commands.add_parser("draft")
    draft_parser.add_argument("cues", type=Path)
    draft_parser.add_argument("--alignment", type=Path)
    draft_parser.add_argument("--output", type=Path, required=True)
    preview_parser = commands.add_parser("preview")
    preview_parser.add_argument("cues", type=Path)
    preview_parser.add_argument("plan", type=Path)
    preview_parser.add_argument("--alignment", type=Path)
    preview_parser.add_argument("--full", action="store_true", help="print each block in full")
    assemble_parser = commands.add_parser("assemble")
    assemble_parser.add_argument("cues", type=Path)
    assemble_parser.add_argument("plan", type=Path)
    assemble_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        cues = load_cues(args.cues)
        tokens = tokenize(cues)
        alignment = load_json(args.alignment) if getattr(args, "alignment", None) else None
        if args.command == "draft":
            plan = draft(cues, tokens, alignment)
            args.output.write_text(
                json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            print(preview(plan, cues, tokens, review_cues(alignment), full=True))
        elif args.command == "preview":
            plan = load_json(args.plan)
            print(preview(plan, cues, tokens, review_cues(alignment), full=args.full))
        else:
            blocks = assemble(load_json(args.plan), cues, tokens)
            args.output.write_text(
                json.dumps(blocks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            print(
                f"Assembled {len(blocks)} blocks S001 to {blocks[-1]['id']} from {len(cues)} cues"
            )
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"build_blocks.py: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
