#!/usr/bin/env python3
"""Validate a Codex Skill directory before packaging."""

from __future__ import annotations

import argparse
import ast
import json
import py_compile
import re
import sys
from pathlib import Path

import yaml


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PLACEHOLDER_RE = re.compile(r"TODO|FIXME|\[[^\]\n]{3,80}\]|<[^>\n]{1,80}>")
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{20,}|AKIA[0-9A-Z]{16}|"
    r"AIza[0-9A-Za-z_-]{30,}|npm_[A-Za-z0-9]{20,}|pypi-[A-Za-z0-9_-]{20,}|"
    r"(?:sk|rk)_live_[A-Za-z0-9]{16,}|"
    r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}|"
    r"Bearer\s+[A-Za-z0-9._-]{20,}|https?://[^\s/:]+:[^\s/@]+@|"
    r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----)",
    re.IGNORECASE,
)
PRIVATE_HOME_RE = re.compile(
    r"(?:[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s]+|/(?:home|Users)/[^/\s]+)",
    re.IGNORECASE,
)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://|#|mailto:)([^)]+)\)")
EXCLUDED_DIRS = {"__pycache__", "node_modules", ".git"}
ROOT_EXCLUDED_DIRS = {"evals"}


def _is_packaged_path(root: Path, path: Path) -> bool:
    rel = path.relative_to(root)
    parts = rel.parts[:-1]
    if any(part in EXCLUDED_DIRS for part in parts):
        return False
    if parts and parts[0] in ROOT_EXCLUDED_DIRS:
        return False
    return True


def _extract_frontmatter(text: str):
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError("SKILL.md frontmatter is not closed with ---")
    raw = text[4:end]
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    body = text[end + len("\n---") :]
    return data, body


def _validate_evals(root: Path, name: str):
    evals_path = root / "evals" / "evals.json"
    if not evals_path.exists():
        return False, "strict mode requires evals/evals.json"
    try:
        data = json.loads(evals_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"evals/evals.json is invalid: {exc}"
    if data.get("skill") != name:
        return False, f"evals skill must be '{name}'"
    cases = data.get("cases")
    if not isinstance(cases, list) or len(cases) < 3:
        return False, "evals must contain at least 3 cases"
    if not any(case.get("trigger_expected") is False for case in cases if isinstance(case, dict)):
        return False, "evals must contain at least one mis-trigger case"
    return True, ""


def validate_skill(skill_path: str | Path, strict: bool = False):
    root = Path(skill_path).resolve()
    if not root.exists():
        return False, f"Skill folder not found: {root}"
    if not root.is_dir():
        return False, f"Path is not a directory: {root}"

    skill_md = root / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found at the skill root"

    packaged_skill_mds = [
        p
        for p in root.rglob("SKILL.md")
        if _is_packaged_path(root, p)
    ]
    if len(packaged_skill_mds) != 1 or packaged_skill_mds[0].resolve() != skill_md.resolve():
        extras = [
            str(p.relative_to(root))
            for p in packaged_skill_mds
            if p.resolve() != skill_md.resolve()
        ]
        return False, "Only one packaged SKILL.md is allowed. Extra: " + ", ".join(extras)

    try:
        content = skill_md.read_text(encoding="utf-8")
        frontmatter, body = _extract_frontmatter(content)
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)

    allowed = {"name", "description"}
    unexpected = set(frontmatter) - allowed
    if unexpected:
        return False, "Unexpected frontmatter key(s): " + ", ".join(sorted(unexpected))

    name = frontmatter.get("name")
    if not isinstance(name, str) or not name.strip():
        return False, "frontmatter.name is required and must be a string"
    name = name.strip()
    if not NAME_RE.match(name):
        return False, "name must be kebab-case lowercase letters, digits, and hyphens"
    if len(name) > 64:
        return False, "name must be 64 characters or fewer"
    if root.name != name:
        return False, f"folder name '{root.name}' must match frontmatter name '{name}'"

    description = frontmatter.get("description")
    if not isinstance(description, str) or not description.strip():
        return False, "frontmatter.description is required and must be a string"
    description = " ".join(description.split())
    if len(description) > 1024:
        return False, f"description is too long ({len(description)} chars, max 1024)"
    if "<" in description or ">" in description:
        return False, "description must not contain angle brackets"
    if PLACEHOLDER_RE.search(description):
        return False, "description contains placeholder text"

    if len(body.strip()) < 200:
        return False, "SKILL.md body is too short to be useful"
    if SECRET_RE.search(content):
        return False, "SKILL.md appears to contain a secret token"

    warnings = []
    openai_yaml = root / "agents" / "openai.yaml"
    if strict and not openai_yaml.exists():
        return False, "strict mode requires agents/openai.yaml"
    if openai_yaml.exists():
        try:
            metadata = yaml.safe_load(openai_yaml.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            return False, f"agents/openai.yaml is invalid YAML: {exc}"
        if not isinstance(metadata, dict):
            return False, "agents/openai.yaml must be a YAML mapping"
        interface = metadata.get("interface")
        if not isinstance(interface, dict):
            return False, "agents/openai.yaml must contain interface mapping"
        default_prompt = interface.get("default_prompt", "")
        if default_prompt and f"${name}" not in str(default_prompt):
            return False, f"interface.default_prompt must mention ${name}"
        short_description = interface.get("short_description", "")
        if short_description and len(str(short_description)) > 96:
            return False, "interface.short_description should be 96 characters or fewer"

    if strict:
        if re.search(r"\b(?:TODO|FIXME|TBD)\b", body, re.IGNORECASE):
            return False, "SKILL.md body contains unfinished placeholder markers"
        evals_ok, evals_message = _validate_evals(root, name)
        if not evals_ok:
            return False, evals_message

        body_without_fences = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
        for raw_target in MARKDOWN_LINK_RE.findall(body_without_fences):
            target = raw_target.strip().split("#", 1)[0]
            if target and not (root / target).exists():
                return False, f"broken local Markdown link in SKILL.md: {raw_target}"

        for script in root.rglob("*.py"):
            if _is_packaged_path(root, script):
                try:
                    ast.parse(
                        script.read_text(encoding="utf-8"),
                        filename=str(script),
                        feature_version=(3, 11),
                    )
                except SyntaxError as exc:
                    return False, f"Python 3.11 syntax error in {script.relative_to(root)}: {exc.msg}"
                try:
                    py_compile.compile(str(script), doraise=True)
                except py_compile.PyCompileError as exc:
                    return False, f"Python syntax error in {script.relative_to(root)}: {exc.msg}"

        for reference in (root / "references").glob("*.md") if (root / "references").exists() else []:
            lines = reference.read_text(encoding="utf-8", errors="ignore").splitlines()
            if len(lines) > 180 and not any("table of contents" in line.lower() for line in lines[:40]):
                warnings.append(f"long reference has no Table of Contents: {reference.name}")

    packaged_text_files = [
        p
        for p in root.rglob("*")
        if p.is_file()
        and _is_packaged_path(root, p)
        and p.suffix.lower() in {".md", ".txt", ".yaml", ".yml", ".json", ".py", ".js", ".ts"}
    ]
    for path in packaged_text_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if SECRET_RE.search(text):
            return False, f"possible secret token in {path.relative_to(root)}"
        if PRIVATE_HOME_RE.search(text):
            return False, f"possible private user-home path in {path.relative_to(root)}"

    message = "Skill is valid"
    if warnings:
        message += "; warnings: " + " | ".join(warnings)
    return True, message


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Codex Skill directory.")
    parser.add_argument("skill_directory")
    parser.add_argument("--strict", action="store_true", help="Run release-level checks")
    args = parser.parse_args()
    ok, message = validate_skill(args.skill_directory, strict=args.strict)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
