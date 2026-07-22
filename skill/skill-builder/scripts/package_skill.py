#!/usr/bin/env python3
"""Package a validated Skill directory as a .skill zip archive."""

from __future__ import annotations

import argparse
import fnmatch
import sys
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from quick_validate import validate_skill  # noqa: E402


EXCLUDE_DIRS = {"__pycache__", "node_modules", ".git"}
EXCLUDE_FILES = {".DS_Store"}
EXCLUDE_GLOBS = {"*.pyc", "*.pyo"}
ROOT_EXCLUDE_DIRS = {"evals"}


def should_exclude(rel_path: Path) -> bool:
    parts = rel_path.parts
    if any(part in EXCLUDE_DIRS for part in parts):
        return True
    if len(parts) > 1 and parts[1] in ROOT_EXCLUDE_DIRS:
        return True
    if rel_path.name in EXCLUDE_FILES:
        return True
    return any(fnmatch.fnmatch(rel_path.name, pattern) for pattern in EXCLUDE_GLOBS)


def package_skill(skill_path: str | Path, output_dir: str | Path = ".") -> Path:
    root = Path(skill_path).resolve()
    ok, message = validate_skill(root)
    if not ok:
        raise ValueError(message)

    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    archive_path = output / f"{root.name}.skill"

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(root.rglob("*")):
            if not file_path.is_file():
                continue
            arcname = file_path.relative_to(root.parent)
            if should_exclude(arcname):
                continue
            archive.write(file_path, arcname)

    return archive_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Package a Skill directory.")
    parser.add_argument("skill_directory")
    parser.add_argument("output_directory", nargs="?", default=".")
    args = parser.parse_args()

    try:
        archive_path = package_skill(args.skill_directory, args.output_directory)
    except Exception as exc:  # noqa: BLE001
        print(f"Packaging failed: {exc}", file=sys.stderr)
        return 1

    print(archive_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
