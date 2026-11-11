#!/usr/bin/env python3
"""Normalize captions, subtitle sidecars, and Whisper JSON into ordered, numbered cues.

The output keeps the Whisper segment shape read by align_speakers.py and adds a stable
`C0001` ID per cue. Rolling-caption repeats are removed line by line. Inline caption
word timestamps become `words`; a cue without them carries cue-level timing only.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

from diarize import write_json

TIMESTAMP = r"(?:\d+:)?\d{1,2}:\d{2}[.,]\d{3}"
TIME_LINE = re.compile(rf"^\s*({TIMESTAMP})\s*-->\s*({TIMESTAMP})")
INLINE_TIME = re.compile(rf"<({TIMESTAMP})>")
TAG = re.compile(r"<[^>]*>|\{\\[^}]*\}")
ROLLING_GAP_MS = 100
# A sound annotation is a short label of letters only, e.g. [Music] or (Laughter); bracketed
# text with punctuation, digits, or more words may be speech and stays.
LABEL = r"[^\W\d_]+(?:[ -][^\W\d_]+){0,2}"
NON_SPEECH = re.compile(rf"^(?:\[{LABEL}\]|\({LABEL}\)|[\u266a\u266b\s])+$")


def parse_time(value: str) -> int:
    clock, _, fraction = value.replace(",", ".").partition(".")
    parts = [int(part) for part in clock.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    hours, minutes, seconds = parts
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + int(fraction)


def format_time(milliseconds: int) -> str:
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def clean(text: str) -> str:
    return " ".join(html.unescape(TAG.sub("", text)).split())


def parse_line(line: str, start: int) -> tuple[str, list[list[Any]] | None, int]:
    """Return a line's plain text, its timed tokens when it has inline timestamps, and the
    latest timestamp, which carries over to the next line of the same cue."""
    pieces = INLINE_TIME.split(line)
    if len(pieces) == 1:
        return clean(line), None, start
    words: list[list[Any]] = []
    for index, piece in enumerate(pieces):
        if index % 2:
            start = parse_time(piece)
            continue
        words.extend([token, start] for token in clean(piece).split())
    return " ".join(word[0] for word in words), words, start


def parse_subtitles(text: str) -> list[tuple[int, int, list[str]]]:
    """Parse WebVTT or SRT cues line by line; every timing line starts a new cue.

    A non-blank line directly before a timing line and after a blank one is the cue's
    number or identifier. Blank includes whitespace-only lines. The WebVTT header and NOTE,
    STYLE, and REGION blocks are skipped.
    """
    cues: list[tuple[int, int, list[str]]] = []
    skipping, previous_blank = False, True
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        blank = not line.strip()
        match = TIME_LINE.match(line)
        if match:
            if cues:
                lines = cues[-1][2]
                if len(lines) >= 2 and lines[-1].strip() and not lines[-2].strip():
                    lines.pop()
            start, end = (parse_time(value) for value in match.groups())
            cues.append((start, end, []))
            skipping = False
        elif skipping:
            skipping = not blank
        elif previous_blank and line.startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
            skipping = True
        elif cues:
            cues[-1][2].append(line)
        previous_blank = blank
    return cues


def strip_repeats(lines: list[str], previous: list[str]) -> tuple[list[str], int]:
    """Drop leading lines repeated from the previous cue's display, as rolling captions do."""
    for size in range(min(len(lines), len(previous)), 0, -1):
        if lines[:size] == previous[-size:]:
            return lines[size:], size
    return lines, 0


def parse_cue(start: int, raw_lines: list[str]) -> list[tuple[str, list[list[Any]] | None]]:
    parsed, state = [], start
    for line in raw_lines:
        plain, words, state = parse_line(line, state)
        if plain:
            parsed.append((plain, words))
    return parsed


def timed_words(lines: list[tuple[str, Any]], start: int, end: int) -> list[dict] | None:
    """Return word timings when every line has them and they run forward inside the cue."""
    if not lines or any(words is None for _, words in lines):
        return None
    tokens = [word for _, words in lines for word in words]
    starts = [token_start for _, token_start in tokens]
    if starts != sorted(starts) or starts[0] < start or starts[-1] > end:
        return None
    return [
        {
            "text": token,
            "from": token_start,
            "to": starts[index + 1] if index + 1 < len(starts) else end,
        }
        for index, (token, token_start) in enumerate(tokens)
    ]


def normalize_subtitles(text: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Remove rolling-caption repeats only from a track that shows the rolling pattern.

    A rolling track carries its display forward: at least a tenth of its cues are brief
    transitions (at most 100 ms) that only repeat the previous cue's lines. In such a track,
    a cue starting where the previous one ended drops the leading lines it repeats; a cue
    made only of repeats is dropped when brief and kept when it has real duration. Any other
    track keeps every line, since separate cues may say the same thing again.
    """
    cues = [(start, end, parse_cue(start, raw)) for start, end, raw in parse_subtitles(text)]
    displays = [[plain for plain, _ in parsed] for _, _, parsed in cues]
    transitions = sum(
        1
        for index in range(1, len(cues))
        if displays[index]
        and cues[index][1] - cues[index][0] <= ROLLING_GAP_MS
        and cues[index][0] <= cues[index - 1][1] + ROLLING_GAP_MS
        and not strip_repeats(displays[index], displays[index - 1])[0]
    )
    rolling = transitions * 10 >= len(cues) > 1
    segments = []
    stats = {"repeated_lines_removed": 0, "non_speech_cues_removed": 0}
    for index, (start, end, parsed) in enumerate(cues):
        kept, removed = displays[index], 0
        if rolling and index and start <= cues[index - 1][1] + ROLLING_GAP_MS:
            kept, removed = strip_repeats(displays[index], displays[index - 1])
            if not kept and end - start > ROLLING_GAP_MS:
                kept, removed = displays[index], 0
        stats["repeated_lines_removed"] += removed
        new_lines = parsed[len(parsed) - len(kept) :]
        text_value = " ".join(plain for plain, _ in new_lines)
        if not text_value:
            continue
        if NON_SPEECH.match(text_value):
            stats["non_speech_cues_removed"] += 1
            continue
        segment: dict[str, Any] = {"start": start, "end": end, "text": text_value}
        words = timed_words(new_lines, start, end)
        if words:
            segment["words"] = words
            segment["start"] = words[0]["from"]
        segments.append(segment)
    return segments, stats


def normalize_whisper(payload: dict[str, Any]) -> list[dict[str, Any]]:
    transcription = payload.get("transcription")
    if not isinstance(transcription, list):
        raise ValueError("Whisper JSON must contain a transcription array")
    return [
        {
            "start": item["offsets"]["from"],
            "end": item["offsets"]["to"],
            "text": " ".join(item["text"].split()),
        }
        for item in transcription
        if item["text"].strip()
    ]


def normalize(path: Path) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        source_format, stats = "whisper-json", {}
        segments = normalize_whisper(json.loads(content))
    elif path.suffix.lower() in {".vtt", ".srt"}:
        source_format = path.suffix.lower()[1:]
        segments, stats = normalize_subtitles(content)
    else:
        raise ValueError("timed text must be .vtt, .srt, or Whisper .json; convert other formats")
    if not segments:
        raise ValueError("timed text contains no non-empty cues")
    previous_start = -1
    for segment in segments:
        if segment["start"] < previous_start or segment["end"] < segment["start"]:
            raise ValueError(f"cue at {format_time(segment['start'])} is out of order or reversed")
        previous_start = segment["start"]
    word_timed = sum("words" in segment for segment in segments)
    transcription = []
    for number, segment in enumerate(segments, start=1):
        cue = {
            "id": f"C{number:04d}",
            "timestamps": {
                "from": format_time(segment["start"]),
                "to": format_time(segment["end"]),
            },
            "offsets": {"from": segment["start"], "to": segment["end"]},
            "text": segment["text"],
        }
        if "words" in segment:
            cue["words"] = segment["words"]
        transcription.append(cue)
    return {
        "source_format": source_format,
        "timing": "word" if word_timed == len(segments) else "cue" if not word_timed else "mixed",
        **stats,
        "transcription": transcription,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("timed_text", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = normalize(args.timed_text)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"normalize_timed_text.py: {exc}\n")
    write_json(args.output, result)
    cues = result["transcription"]
    print(
        f"Normalized {len(cues)} cues ({result['timing']} timing) "
        f"{cues[0]['id']} to {cues[-1]['id']}; "
        f"removed {result.get('repeated_lines_removed', 0)} repeated lines and "
        f"{result.get('non_speech_cues_removed', 0)} non-speech cues"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
