#!/usr/bin/env python3
"""Run offline release checks and build skill-builder.skill."""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "skill-builder"
DIST = ROOT / "dist"


def run(*args: str | Path) -> None:
    command = [str(arg) for arg in args]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def verify_archive(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise RuntimeError(f"Corrupt archive member: {bad_member}")
        names = {name.rstrip("/") for name in archive.namelist() if name.rstrip("/")}
    roots = {name.split("/", 1)[0] for name in names}
    if roots != {"skill-builder"}:
        raise RuntimeError(f"Unexpected archive roots: {sorted(roots)}")
    forbidden = [
        name for name in names
        if "/evals/" in f"/{name}/"
        or "/__pycache__/" in f"/{name}/"
        or name.endswith((".pyc", ".pyo"))
    ]
    if forbidden:
        raise RuntimeError(f"Forbidden release files: {forbidden}")
    required = {
        "skill-builder/SKILL.md",
        "skill-builder/agents/openai.yaml",
        "skill-builder/scripts/bootstrap_from_project.py",
    }
    if missing := sorted(required - names):
        raise RuntimeError(f"Missing release files: {missing}")


def main() -> int:
    python = sys.executable
    validator = SKILL / "scripts" / "quick_validate.py"
    packager = SKILL / "scripts" / "package_skill.py"
    run(python, SKILL / "evals" / "test_readme_extraction.py")
    run(python, SKILL / "evals" / "test_release_security.py")
    run(python, validator, SKILL, "--strict")
    DIST.mkdir(parents=True, exist_ok=True)
    run(python, packager, SKILL, DIST)
    verify_archive(DIST / "skill-builder.skill")
    run(python, ROOT / "scripts" / "security_scan.py")
    print(DIST / "skill-builder.skill")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
