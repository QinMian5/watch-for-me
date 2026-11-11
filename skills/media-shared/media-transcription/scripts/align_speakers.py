#!/usr/bin/env python3
"""Attach acoustic evidence to timed ASR without inventing word boundaries."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from diarize import write_json


def union_duration(ranges: list[tuple[float, float]]) -> float:
    total, right = 0.0, -math.inf
    for start, end in sorted(ranges):
        total += max(0.0, end - max(start, right))
        right = max(right, end)
    return total


def align(transcript: dict, diarization: dict) -> dict:
    segments = transcript.get("transcription")
    if not isinstance(segments, list) or not segments:
        raise ValueError("ASR transcription must be a non-empty array")
    duration = diarization["duration_seconds"]
    if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
        raise ValueError("diarization duration must be positive and finite")
    speakers = set(diarization["speakers"])
    for key in ("turns", "exclusive_turns"):
        previous_end = 0.0
        for turn in diarization[key]:
            start, end = turn["start"], turn["end"]
            if (
                not math.isfinite(start + end)
                or not 0 <= start < end <= duration
                or turn["speaker"] not in speakers
            ):
                raise ValueError("invalid diarization turn")
            if key == "exclusive_turns" and start < previous_end - 0.000001:
                raise ValueError("exclusive turns must be ordered and non-overlapping")
            previous_end = end
    blocks, previous_start = [], -1.0
    for segment in segments:
        start, end = segment["offsets"]["from"] / 1000, segment["offsets"]["to"] / 1000
        text = segment["text"]
        if (
            not math.isfinite(start + end)
            or start < previous_start
            or not 0 <= start <= end <= duration + 0.1
            or start > duration
            or not isinstance(text, str)
            or not text.strip()
        ):
            raise ValueError("ASR segments must be timed, non-empty, ordered, and within the audio")
        previous_start = start
        end = min(end, duration)
        evidence = [
            {
                "start": max(start, t["start"]),
                "end": min(end, t["end"]),
                "speaker": t["speaker"],
            }
            for t in diarization["turns"]
            if t["start"] < end and t["end"] > start
        ]
        candidates = sorted({turn["speaker"] for turn in evidence})
        overlap = any(
            a["speaker"] != b["speaker"]
            and min(a["end"], b["end"]) > max(a["start"], b["start"]) + 0.000001
            for i, a in enumerate(evidence)
            for b in evidence[i + 1 :]
        )
        coverage = (
            union_duration([(t["start"], t["end"]) for t in evidence]) / (end - start)
            if end > start
            else 0.0
        )
        exclusive_evidence = [
            {
                "start": max(start, t["start"]),
                "end": min(end, t["end"]),
                "speaker": t["speaker"],
            }
            for t in diarization["exclusive_turns"]
            if t["start"] < end and t["end"] > start
        ]
        # Coverage is a review heuristic, never a calibrated identity confidence.
        certain = len(candidates) == 1 and coverage >= 0.8 and not overlap
        blocks.append(
            {
                "cue": segment.get("id"),
                "start": start,
                "end": end,
                "text": text,
                "speaker": candidates[0] if certain else None,
                "speaker_candidates": candidates,
                "overlap": overlap,
                "needs_review": not certain,
                "speech_coverage": round(coverage, 6),
                "turn_evidence": evidence,
                "exclusive_evidence": exclusive_evidence,
            }
        )
    return {"audio_sha256": diarization["audio_sha256"], "segments": blocks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("diarization", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = align(
        json.loads(args.transcript.read_text()),
        json.loads(args.diarization.read_text()),
    )
    write_json(args.output, result)
    print(
        f"Aligned {len(result['segments'])} segments; "
        f"{sum(s['needs_review'] for s in result['segments'])} require attribution review"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
