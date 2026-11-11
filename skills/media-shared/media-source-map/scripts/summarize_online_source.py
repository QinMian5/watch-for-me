"""Print the decision fields of a yt-dlp `--dump-single-json` file.

The full JSON stays on disk. The summary keeps source identity, original-language
subtitle candidates, and media formats without URLs, headers, or translated tracks.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DESCRIPTION_LIMIT = 800
IDENTITY_FIELDS = (
    "title",
    "id",
    "extractor",
    "webpage_url",
    "duration",
    "language",
    "availability",
    "license",
    "live_status",
    "age_limit",
    "channel",
    "uploader",
    "upload_date",
)
FORMAT_FIELDS = (
    "format_id",
    "ext",
    "protocol",
    "vcodec",
    "acodec",
    "resolution",
    "fps",
    "abr",
    "tbr",
    "audio_channels",
    "language",
    "format_note",
)


UNDETERMINED = {"und", "mul", "zxx"}


def primary(tag: str | None) -> str | None:
    """Primary language subtag; None when absent or undetermined."""
    subtag = tag.split("-")[0].lower() if tag else None
    return None if subtag in UNDETERMINED else subtag


def subtitle_candidates(tracks: dict, original: str | None) -> tuple[dict, int]:
    """Keep tracks in the source language and yt-dlp's `-orig` tracks."""
    kept = {
        tag: [item.get("ext") for item in items]
        for tag, items in tracks.items()
        if original is None or tag.endswith("-orig") or primary(tag) == original
    }
    return kept, len(tracks) - len(kept)


def is_audio_only(fmt: dict) -> bool:
    return fmt.get("vcodec") == "none" and fmt.get("acodec") != "none"


def is_original_audio(fmt: dict, original: str | None) -> bool:
    note = (fmt.get("format_note") or "").lower()
    if "original" in note:
        return True
    if "dubbed" in note:
        return False
    return original is None or primary(fmt.get("language")) in (None, original)


def compact_format(fmt: dict) -> dict:
    row = {key: fmt[key] for key in FORMAT_FIELDS if fmt.get(key) not in (None, "", 0)}
    size = fmt.get("filesize") or fmt.get("filesize_approx")
    if size:
        row["filesize"] = size
    return row


def summarize(info: dict) -> dict:
    original = primary(info.get("language"))
    summary = {key: info[key] for key in IDENTITY_FIELDS if info.get(key) is not None}

    description = info.get("description") or ""
    if description:
        summary["description"] = description[:DESCRIPTION_LIMIT]
        if len(description) > DESCRIPTION_LIMIT:
            summary["description_truncated"] = True
    if info.get("chapters"):
        summary["chapters"] = [
            {"start": chapter.get("start_time"), "title": chapter.get("title")}
            for chapter in info["chapters"]
        ]

    manual, manual_omitted = subtitle_candidates(info.get("subtitles") or {}, original)
    auto, auto_omitted = subtitle_candidates(info.get("automatic_captions") or {}, original)
    summary["subtitles"] = {
        "manual": manual,
        "automatic": auto,
        "omitted_other_languages": {"manual": manual_omitted, "automatic": auto_omitted},
    }

    audio, video = [], []
    omitted = {"storyboard": 0, "other_language_audio": 0}
    # Single-format extractors store the playable format at the top level.
    formats = info.get("formats") or ([info] if info.get("format_id") or info.get("url") else [])
    for fmt in formats:
        if fmt.get("ext") == "mhtml" or fmt.get("format_note") == "storyboard":
            omitted["storyboard"] += 1
        elif is_audio_only(fmt):
            if is_original_audio(fmt, original):
                audio.append(compact_format(fmt))
            else:
                omitted["other_language_audio"] += 1
        else:
            video.append(compact_format(fmt))
    summary["formats"] = {"audio": audio, "video": video, "omitted": omitted}
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_json", type=Path)
    args = parser.parse_args()
    try:
        info = json.loads(args.source_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"source metadata could not be read: {args.source_json}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summarize(info), ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
