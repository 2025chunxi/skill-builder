#!/usr/bin/env python3
"""Regression checks for README usage extraction and draft rendering."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "readme-project"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from bootstrap_from_project import build_skill_md, sanitize_analysis_for_draft  # noqa: E402
from inspect_project import inspect_project  # noqa: E402


class ReadmeExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.analysis = inspect_project(FIXTURE, [FIXTURE / "no-installed-skills"])

    def test_extracts_source_backed_commands_and_examples(self) -> None:
        usage = self.analysis["readme_usage"]
        commands = [item["command"] for item in usage["install_commands"]]
        self.assertIn("python -m pip install readme-demo", commands)
        self.assertIn("pipx install readme-demo", commands)
        self.assertGreaterEqual(len(usage["examples"]), 2)
        self.assertTrue(all(item["source"] == "README.md" for item in usage["examples"]))

    def test_redacts_sensitive_example_values(self) -> None:
        rendered = "\n".join(item["code"] for item in self.analysis["readme_usage"]["examples"])
        self.assertIn("DEMO_API_KEY=REDACTED", rendered)
        self.assertNotIn("not-a-real-key", rendered)

    def test_generated_draft_contains_real_usage(self) -> None:
        public_analysis = sanitize_analysis_for_draft(self.analysis)
        skill_md = build_skill_md("readme-demo", public_analysis)
        self.assertIn("python -m pip install readme-demo", skill_md)
        self.assertIn("from readme_demo import scan", skill_md)
        self.assertIn("readme-demo scan ./src --format json", skill_md)
        self.assertIn("README usage examples extracted: `2`", skill_md)
        self.assertNotIn(str(FIXTURE.resolve()), skill_md)
        self.assertEqual(public_analysis["project"], "readme-project")
        self.assertTrue(public_analysis["privacy"]["local_paths_omitted"])
        self.assertTrue(all("path" not in item for item in public_analysis["duplicate_candidates"]))


if __name__ == "__main__":
    unittest.main()
