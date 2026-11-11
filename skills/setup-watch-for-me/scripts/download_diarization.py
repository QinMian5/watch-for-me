#!/usr/bin/env python3
"""Walk through Hugging Face access, then download a pinned Community-1 snapshot.

Run it in your own terminal on macOS, Linux, or Windows. It opens each Hugging Face page,
says what to do there, and asks for a read token in a hidden prompt. The token goes
straight to the Hub client and is never saved.
"""

import argparse
import getpass
import hashlib
import json
import os
import shutil
import sys
import tempfile
import webbrowser
from pathlib import Path

REPO = "pyannote/speaker-diarization-community-1"
MODEL_URL = f"https://huggingface.co/{REPO}"
TOKENS_URL = "https://huggingface.co/settings/tokens"
# Each stage: title, page to open, what to do there, what Enter confirms.
GUIDE = (
    (
        "Hugging Face account",
        "https://huggingface.co/login",
        [
            "The speaker model is free, but Hugging Face only serves it to signed-in users.",
            "Sign in. No account yet? Use 'Sign Up' on that page to create one.",
        ],
        "Press Enter once you are signed in",
    ),
    (
        "Accept the model's conditions",
        MODEL_URL,
        [
            "Near the top of the model page, fill in the fields it asks for and agree.",
            "Once access is granted, the page shows the model files instead of the form.",
        ],
        "Press Enter once access is granted",
    ),
    (
        "Create a read token",
        TOKENS_URL,
        [
            "Click 'Create new token'.",
            "Choose the 'Read' token type and name it, for example watch-for-me.",
            "Click 'Create token', then copy the token it shows.",
            "Keep the token out of any chat; you paste it here in the next stage.",
        ],
        "Press Enter once the token is copied",
    ),
)
STAGES = len(GUIDE) + 1
REQUIRED_FILES = (
    "config.yaml",
    "embedding/pytorch_model.bin",
    "segmentation/pytorch_model.bin",
    "plda/plda.npz",
    "plda/xvec_transform.npz",
)


def validate_snapshot(directory: Path) -> None:
    for relative in REQUIRED_FILES:
        path = directory / relative
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"snapshot lacks a non-empty regular file: {relative}")


def show_stage(number: int, title: str) -> None:
    if sys.stdout.isatty():
        os.system("cls" if os.name == "nt" else "clear")
    print(f"\nStage {number}/{STAGES}: {title}\n")


def guide() -> None:
    for number, (title, url, lines, done) in enumerate(GUIDE, 1):
        show_stage(number, title)
        for line in lines:
            print(f"  - {line}")
        print(f"\n  Opening {url}")
        if not webbrowser.open(url):
            print("  Could not open a browser; visit that address yourself.")
        input(f"\n  {done} ")


def download(stage: Path, revision: str) -> str:
    """Ask for a token until the pinned snapshot downloads, or the user stops."""
    from huggingface_hub import HfApi, snapshot_download

    show_stage(STAGES, "Download the model")
    print("  Paste the token at the prompt. Nothing appears while you paste; that is expected.\n")
    while True:
        token = getpass.getpass("  Hugging Face read token (not saved): ").strip()
        try:
            if not token:
                raise ValueError("no token was entered")
            resolved = HfApi().model_info(REPO, revision=revision, token=token).sha
            snapshot_download(repo_id=REPO, revision=resolved, token=token, local_dir=stage)
            return resolved
        except Exception as error:  # refused access, a bad token, or a network failure
            reason = str(error).splitlines()[0] if str(error) else type(error).__name__
            print(f"\n  The download did not finish: {reason}")
            print(f"  Usually the conditions at {MODEL_URL} are not accepted yet,")
            print("  or the token was not copied in full.")
            if not input("  Try again? [y/N] ").strip().lower().startswith("y"):
                raise SystemExit("Stopped. Run this command again when you are ready.") from None
        finally:
            token = None


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    destination = args.destination
    if not destination.is_absolute() or destination.exists():
        parser.error("destination must be an absolute, not-yet-existing model directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".community-1.", dir=destination.parent))
    try:
        os.environ.update(
            HF_HOME=str(stage / ".cache/huggingface"),
            HF_HUB_CACHE=str(stage / ".cache/hub"),
            HF_XET_CACHE=str(stage / ".cache/xet"),
            HF_HUB_DISABLE_TELEMETRY="1",
            PYANNOTE_METRICS_ENABLED="0",
        )
        try:
            guide()
            revision = download(stage, args.revision)
        except (KeyboardInterrupt, EOFError):
            raise SystemExit("\nStopped. Run this command again when you are ready.") from None
        validate_snapshot(stage)
        metadata = stage / ".cache"
        if metadata.exists():
            shutil.rmtree(metadata)
        hashes = {
            str(p.relative_to(stage)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(stage.rglob("*"))
            if p.is_file()
        }
        (stage / "snapshot.json").write_text(
            json.dumps({"repo_id": REPO, "revision": revision, "sha256": hashes}, indent=2) + "\n"
        )
        stage.rename(destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    print(f"\nDownloaded Community-1 revision {revision} to {destination}")
    print(f"You can delete the token at {TOKENS_URL}. Go back to your agent to finish setup.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
