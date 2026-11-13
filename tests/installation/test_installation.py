"""Verify shared routes and command entry points in a skills-only installation."""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = REPO_ROOT / "skills"
FIXTURES = REPO_ROOT / "tests/media-render/fixtures"
PACKAGES = ("watch-for-me", "setup-watch-for-me", "media-shared")


def resource_paths(manifest: dict) -> Iterator[str]:
    yield from manifest.get("always_load", [])
    for axis in manifest.get("axes", {}).values():
        yield from axis["values"].values()
    for section in manifest.values():
        if isinstance(section, dict):
            for route in section.get("on_demand", []):
                yield route["path"]


class InstallationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name).resolve()
        self.skills = self.work / "installed" / "skills"
        for name in PACKAGES:
            shutil.copytree(
                SKILLS_ROOT / name,
                self.skills / name,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
            )

    def test_manifest_routes_are_complete_inside_skills_only_installation(self) -> None:
        manifests = sorted(self.skills.rglob("manifest.yaml"))
        self.assertEqual(len(manifests), 6)
        for manifest in manifests:
            for resource in resource_paths(yaml.safe_load(manifest.read_text())):
                with self.subTest(manifest=manifest.relative_to(self.skills), resource=resource):
                    target = (manifest.parent / resource).resolve()
                    self.assertTrue(target.is_relative_to(self.skills))
                    self.assertTrue(target.is_file())
        shared = yaml.safe_load((self.skills / "media-shared/manifest.yaml").read_text())
        self.assertEqual(shared["always_load"], [])
        self.assertEqual(
            {route["path"] for route in shared["modules"]["on_demand"]},
            {
                "media-source-map/manifest.yaml",
                "media-transcription/manifest.yaml",
                "media-render/manifest.yaml",
            },
        )

    def test_installed_skills_carry_no_tests(self) -> None:
        self.assertEqual(sorted(self.skills.rglob("tests")), [])
        self.assertEqual(sorted(self.skills.rglob("test_*.py")), [])

    def test_public_routers_reach_sibling_shared_package(self) -> None:
        for name in PACKAGES:
            entry = self.skills / name / "SKILL.md"
            links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", entry.read_text())
            if name != "media-shared":
                self.assertIn("../media-shared/SKILL.md", links)
            for link in links:
                with self.subTest(skill=name, link=link):
                    target = (entry.parent / link).resolve()
                    self.assertTrue(target.is_relative_to(self.skills))
                    self.assertTrue(target.is_file())
        policy = yaml.safe_load((self.skills / "media-shared/agents/openai.yaml").read_text())[
            "policy"
        ]
        self.assertIs(policy["allow_implicit_invocation"], False)

    def test_bundled_commands_run_from_unrelated_working_directory(self) -> None:
        commands = (
            "media-shared/media-source-map/scripts/validate_source_map.py",
            "media-shared/media-source-map/scripts/assemble_source_map.py",
            "media-shared/media-source-map/scripts/summarize_online_source.py",
            "media-shared/media-render/scripts/render_bundle.py",
            "media-shared/media-render/scripts/write_reader_copy.py",
            "media-shared/media-transcription/scripts/transcribe_faster_whisper.py",
            "media-shared/media-transcription/scripts/diarize.py",
            "media-shared/media-transcription/scripts/align_speakers.py",
            "setup-watch-for-me/scripts/download_diarization.py",
        )
        for command in commands:
            with self.subTest(command=command):
                result = subprocess.run(
                    [sys.executable, "-B", str(self.skills / command), "--help"],
                    cwd=self.work,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout)

    def test_installed_renderer_imports_the_map_model_from_an_unrelated_directory(self) -> None:
        fixtures = FIXTURES
        bundle = self.work / "bundle"
        bundle.mkdir()
        shutil.copy(fixtures / "source_map.fixture.json", bundle / "source_map.json")
        shutil.copy(fixtures / "notes.A-generic.json", bundle / "notes.json")
        shutil.copytree(fixtures / "assets", bundle / "assets")
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(self.skills / "media-shared/media-render/scripts/render_bundle.py"),
                str(bundle),
            ],
            cwd=self.work,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("rendered", result.stdout)
        self.assertTrue((bundle / "media.html").is_file())
        self.assertTrue((bundle / "source_map.md").is_file())


if __name__ == "__main__":
    unittest.main()
