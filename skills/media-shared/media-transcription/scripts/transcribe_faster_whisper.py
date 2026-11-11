#!/usr/bin/env python3
"""Run faster-whisper and emit normalized Media Source Map JSON and SRT inputs."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

BEAM_SIZE = 5


def milliseconds_to_timestamp(milliseconds: int) -> str:
    if milliseconds < 0:
        raise ValueError("timestamp must be non-negative")
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def normalize_segments(segments: Iterable[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    previous_start_ms = -1

    for segment in segments:
        text = str(segment.text)
        if not text.strip():
            continue

        start_ms = round(float(segment.start) * 1000)
        end_ms = round(float(segment.end) * 1000)
        if start_ms < 0 or end_ms < start_ms:
            raise ValueError("faster-whisper returned an invalid segment range")
        if start_ms < previous_start_ms:
            raise ValueError("faster-whisper returned segments out of order")

        normalized.append(
            {
                "timestamps": {
                    "from": milliseconds_to_timestamp(start_ms),
                    "to": milliseconds_to_timestamp(end_ms),
                },
                "offsets": {"from": start_ms, "to": end_ms},
                "text": text,
            }
        )
        previous_start_ms = start_ms

    if not normalized:
        raise ValueError("faster-whisper returned no non-empty segments")
    return normalized


def build_payload(
    *,
    input_path: Path,
    segments: Iterable[Any],
    info: object,
    model: str,
    device: str,
    compute_type: str,
    quality: str,
) -> dict[str, Any]:
    return {
        "systeminfo": {"file": str(input_path.resolve())},
        "model": {
            "backend": "faster-whisper",
            "name": model,
            "device": device,
            "compute_type": compute_type,
        },
        "params": {
            "task": "transcribe",
            "quality": quality,
            "beam_size": BEAM_SIZE,
            "vad_filter": True,
        },
        "result": {
            "language": getattr(info, "language", None),
            "language_probability": getattr(info, "language_probability", None),
            "duration": getattr(info, "duration", None),
            "duration_after_vad": getattr(info, "duration_after_vad", None),
        },
        "transcription": normalize_segments(segments),
    }


def render_srt(transcription: Sequence[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for index, segment in enumerate(transcription, start=1):
        blocks.append(
            "\n".join(
                [
                    str(index),
                    (f"{segment['timestamps']['from']} --> {segment['timestamps']['to']}"),
                    segment["text"],
                ]
            )
        )
    return "\n\n".join(blocks) + "\n"


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        handle.write(content)
        temporary_path = Path(handle.name)
    os.replace(temporary_path, path)


def write_outputs(output_prefix: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    json_path = Path(f"{output_prefix}.json")
    srt_path = Path(f"{output_prefix}.srt")
    atomic_write(json_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    atomic_write(srt_path, render_srt(payload["transcription"]))
    return json_path, srt_path


def transcribe(args: argparse.Namespace) -> tuple[Path, Path]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("faster-whisper is unavailable in the uv command environment") from exc

    model = WhisperModel(
        args.model,
        device=args.device,
        compute_type=args.compute_type,
        download_root=str(args.model_cache),
    )
    segments, info = model.transcribe(
        str(args.input_path),
        task="transcribe",
        beam_size=BEAM_SIZE,
        vad_filter=True,
    )
    payload = build_payload(
        input_path=args.input_path,
        segments=segments,
        info=info,
        model=args.model,
        device=args.device,
        compute_type=args.compute_type,
        quality=args.quality,
    )
    return write_outputs(args.output_prefix, payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transcribe media into normalized Media Source Map JSON and SRT inputs."
    )
    parser.add_argument("input_path", type=Path)
    parser.add_argument("--output-prefix", required=True, type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-cache", required=True, type=Path)
    parser.add_argument("--device", required=True, choices=("cpu", "cuda", "auto"))
    parser.add_argument("--compute-type", required=True)
    parser.add_argument("--quality", required=True, choices=("balanced", "maximum"))
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.input_path.is_file():
        parser.error(f"input file does not exist: {args.input_path}")
    try:
        json_path, srt_path = transcribe(args)
    except (RuntimeError, ValueError) as exc:
        parser.exit(1, f"transcribe_faster_whisper.py: {exc}\n")
    print(json_path)
    print(srt_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
