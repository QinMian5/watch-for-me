#!/usr/bin/env python3
"""Run Community-1 locally on prepared PCM audio and retain both turn views."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
import wave
from collections.abc import Iterable
from itertools import pairwise
from pathlib import Path
from typing import Protocol


class Segment(Protocol):
    start: float
    end: float


class DiarizationOutput(Protocol):
    speaker_diarization: Iterable[tuple[Segment, str]]
    exclusive_speaker_diarization: Iterable[tuple[Segment, str]]


def speaker_options(num: int | None, minimum: int | None, maximum: int | None) -> dict:
    for value in (num, minimum, maximum):
        if value is not None and value < 1:
            raise ValueError("speaker counts must be positive")
    if num is not None:
        return {"num_speakers": num}
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("minimum speaker count exceeds maximum")
    return {
        k: v for k, v in (("min_speakers", minimum), ("max_speakers", maximum)) if v is not None
    }


def read_pcm(path: Path) -> tuple[bytes, int]:
    with wave.open(str(path), "rb") as source:
        if (
            source.getnchannels(),
            source.getframerate(),
            source.getsampwidth(),
            source.getcomptype(),
        ) != (1, 16000, 2, "NONE"):
            raise ValueError("input must be mono 16 kHz signed 16-bit PCM WAV")
        frames = source.getnframes()
        data = source.readframes(frames)
    if frames == 0 or len(data) != frames * 2:
        raise ValueError("empty or truncated PCM audio")
    return data, frames


def normalized_turns(annotation: Iterable[tuple[Segment, str]], duration: float) -> list[dict]:
    turns = []
    for segment, speaker in annotation:
        start, end = float(segment.start), float(segment.end)
        if (
            not math.isfinite(start + end)
            or start < 0
            or start >= duration
            or end <= start
            or end > duration + 0.1
        ):
            raise ValueError("diarization returned an invalid time range")
        turns.append(
            {
                "start": round(start, 6),
                "end": round(min(end, duration), 6),
                "speaker": str(speaker),
            }
        )
    return sorted(turns, key=lambda item: (item["start"], item["end"], item["speaker"]))


def build_result(
    output: DiarizationOutput,
    duration: float,
    model: str,
    revision: str,
    device: str,
    options: dict,
    audio_sha256: str,
) -> dict:
    regular = normalized_turns(output.speaker_diarization, duration)
    exclusive = normalized_turns(output.exclusive_speaker_diarization, duration)
    labels = list(dict.fromkeys(turn["speaker"] for turn in regular))
    mapping = {label: f"SPK{index:03d}" for index, label in enumerate(labels, 1)}
    for turn in regular + exclusive:
        if turn["speaker"] not in mapping:
            raise ValueError("exclusive diarization references an unknown speaker")
        turn["speaker"] = mapping[turn["speaker"]]
    if any(right["start"] < left["end"] - 0.000001 for left, right in pairwise(exclusive)):
        raise ValueError("exclusive speaker turns overlap")
    return {
        "backend": "pyannote.audio",
        "model": model,
        "revision": revision,
        "device": device,
        "duration_seconds": duration,
        "audio_sha256": audio_sha256,
        "parameters": options,
        "speaker_count": len(labels),
        "speakers": list(mapping.values()),
        "turns": regular,
        "exclusive_turns": exclusive,
    }


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--device", choices=["cpu", "cuda", "mps"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--num-speakers", type=int)
    parser.add_argument("--min-speakers", type=int)
    parser.add_argument("--max-speakers", type=int)
    args = parser.parse_args()
    options = speaker_options(args.num_speakers, args.min_speakers, args.max_speakers)
    if not (args.model / "config.yaml").is_file():
        parser.error(
            "--model must be a downloaded Community-1 directory containing config.yaml; "
            "run setup-watch-for-me"
        )
    pcm, frames = read_pcm(args.audio)
    os.environ.update(
        HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", PYANNOTE_METRICS_ENABLED="0"
    )
    if args.device == "mps":
        os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "0"
    import torch
    from pyannote.audio import Pipeline

    if args.device == "cuda" and not torch.cuda.is_available():
        parser.error("configured CUDA is unavailable; verify the device through setup-watch-for-me")
    if args.device == "mps" and not torch.backends.mps.is_available():
        parser.error("configured MPS is unavailable; verify the device through setup-watch-for-me")
    waveform = (
        torch.frombuffer(bytearray(pcm), dtype=torch.int16)
        .to(torch.float32)
        .div_(32768)
        .unsqueeze(0)
    )
    pipeline = Pipeline.from_pretrained(str(args.model.resolve()))
    pipeline.to(torch.device(args.device))
    print(f"Diarization device: {pipeline.device}", flush=True)
    output = pipeline({"waveform": waveform, "sample_rate": 16000}, **options)
    result = build_result(
        output,
        frames / 16000,
        str(args.model.resolve()),
        args.revision,
        args.device,
        options,
        hashlib.sha256(args.audio.read_bytes()).hexdigest(),
    )
    write_json(args.output, result)
    print(
        f"Diarization: {result['speaker_count']} estimated speakers; {len(result['turns'])} turns"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
