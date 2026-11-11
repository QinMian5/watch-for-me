import importlib.util
import io
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

SPEC = importlib.util.spec_from_file_location(
    "download_diarization",
    Path(__file__).resolve().parents[2]
    / "skills/setup-watch-for-me/scripts/download_diarization.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SnapshotTests(unittest.TestCase):
    def test_actual_community_snapshot_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in MODULE.REQUIRED_FILES:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"test")
            MODULE.validate_snapshot(root)
            (root / "embedding/pytorch_model.bin").write_bytes(b"")
            with self.assertRaisesRegex(ValueError, "embedding/pytorch_model.bin"):
                MODULE.validate_snapshot(root)

    def test_incomplete_snapshot_is_not_publishable(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(ValueError, "config.yaml"),
        ):
            MODULE.validate_snapshot(Path(directory))


class GuideTests(unittest.TestCase):
    def test_guide_opens_each_page_and_waits_for_the_user(self) -> None:
        with (
            mock.patch.object(MODULE.webbrowser, "open", return_value=True) as opened,
            mock.patch("builtins.input", return_value="") as waited,
            redirect_stdout(io.StringIO()) as out,
        ):
            MODULE.guide()
        self.assertEqual(
            [c.args[0] for c in opened.call_args_list],
            ["https://huggingface.co/login", MODULE.MODEL_URL, MODULE.TOKENS_URL],
        )
        self.assertEqual(waited.call_count, 3)
        self.assertIn("Stage 3/4: Create a read token", out.getvalue())

    def test_refused_token_can_be_retried_or_abandoned(self) -> None:
        calls = []

        class Api:
            def model_info(self, repo: str, revision: str, token: str) -> types.SimpleNamespace:
                calls.append(token)
                if token == "bad":
                    raise RuntimeError("401 Unauthorized\nmore detail")
                return types.SimpleNamespace(sha="abc123")

        hub = types.SimpleNamespace(HfApi=Api, snapshot_download=mock.Mock())
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.dict(sys.modules, {"huggingface_hub": hub}),
            mock.patch.object(MODULE.getpass, "getpass", side_effect=["bad", "good"]),
            mock.patch("builtins.input", return_value="y"),
            redirect_stdout(io.StringIO()) as out,
        ):
            self.assertEqual(MODULE.download(Path(directory), "pinned"), "abc123")
        self.assertEqual(calls, ["bad", "good"])
        self.assertIn("did not finish: 401 Unauthorized", out.getvalue())
        hub.snapshot_download.assert_called_once()

        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.dict(sys.modules, {"huggingface_hub": hub}),
            mock.patch.object(MODULE.getpass, "getpass", return_value="bad"),
            mock.patch("builtins.input", return_value=""),
            redirect_stdout(io.StringIO()),
            self.assertRaisesRegex(SystemExit, "Run this command again"),
        ):
            MODULE.download(Path(directory), "pinned")


if __name__ == "__main__":
    unittest.main()
