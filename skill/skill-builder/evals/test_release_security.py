#!/usr/bin/env python3
"""Regression checks for release secret and private-path detection."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from quick_validate import PRIVATE_HOME_RE, SECRET_RE  # noqa: E402


class ReleaseSecurityTests(unittest.TestCase):
    def test_detects_additional_token_formats(self) -> None:
        self.assertIsNotNone(SECRET_RE.search("npm_" + "A" * 30))
        self.assertIsNotNone(SECRET_RE.search("pypi-" + "B" * 30))
        self.assertIsNotNone(SECRET_RE.search("Bearer " + "c" * 26 + ".123456"))

    def test_detects_private_home_paths(self) -> None:
        self.assertIsNotNone(PRIVATE_HOME_RE.search("C:" + r"\Users\private-user\project"))
        self.assertIsNotNone(PRIVATE_HOME_RE.search("/" + "home/private-user/project"))
        self.assertIsNotNone(PRIVATE_HOME_RE.search("/" + "Users/private-user/project"))

    def test_allows_placeholders_and_portable_paths(self) -> None:
        self.assertIsNone(SECRET_RE.search("Authorization: Bearer $GITHUB_TOKEN"))
        self.assertIsNone(PRIVATE_HOME_RE.search("$HOME/.codex/skills"))
        self.assertIsNone(PRIVATE_HOME_RE.search("~/.codex/skills"))


if __name__ == "__main__":
    unittest.main()
