#!/usr/bin/env python3
"""Bootstrap a concrete, review-required Skill draft from a local project."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from generate_openai_yaml import generate as generate_openai_yaml  # noqa: E402
from inspect_project import inspect_project  # noqa: E402
from quick_validate import validate_skill  # noqa: E402


def normalize_name(raw: str) -> str:
    name = re.sub(r"[^a-z0-9]+", "-", raw.strip().lower())
    return re.sub(r"-+", "-", name).strip("-")[:64].strip("-")


def sanitize_analysis_for_draft(analysis: dict) -> dict:
    """Remove local filesystem details before embedding analysis in a Skill."""
    public = deepcopy(analysis)
    source_path = str(public.get("project") or "")
    public["project"] = Path(source_path).name if source_path else str(public.get("name") or "local-project")
    for candidate in public.get("duplicate_candidates") or []:
        if isinstance(candidate, dict):
            candidate.pop("path", None)
    public["privacy"] = {
        "local_paths_omitted": True,
        "note": "Absolute source and installed-Skill paths are intentionally excluded from generated artifacts.",
    }
    return public


def inferred_setup_command(analysis: dict) -> str:
    packages = analysis.get("metadata", {}).get("package_names") or []
    if not packages:
        return "No package install command detected; document the verified setup before release."
    package = packages[0]
    registry = package.get("registry")
    name = package.get("name")
    if registry == "npm":
        return f"npm install {name}"
    if registry == "pypi":
        return f"pip install {name}"
    if registry == "crates":
        return f"cargo add {name}"
    return "No package install command detected; document the verified setup before release."


def code_fence(language: str, code: str) -> str:
    marker = "````" if "```" in code else "```"
    return f"{marker}{language}\n{code.rstrip()}\n{marker}"


def source_note(item: dict) -> str:
    source = item.get("source") or "README"
    section = item.get("section") or item.get("title") or "README"
    line = item.get("line")
    location = f"line {line}" if line else "line unknown"
    return f"Source: `{source}`, section \"{section}\", {location}."


def build_setup_section(analysis: dict) -> tuple[str, bool]:
    commands = (analysis.get("readme_usage") or {}).get("install_commands") or []
    if commands:
        chunks = [
            "The source README contains the setup commands below. They may be alternatives; "
            "choose only the one that matches the target environment."
        ]
        for index, item in enumerate(commands[:3], 1):
            if len(commands) > 1:
                chunks.append(f"### Setup Option {index}")
            chunks.append(source_note(item))
            chunks.append(code_fence("bash", str(item.get("command") or "")))
        chunks.append(
            "Run the project's native version or smoke-test command after installation. "
            "Treat README extraction as source-backed but not execution-verified."
        )
        return "\n\n".join(chunks), True

    inferred = inferred_setup_command(analysis)
    return (
        "No installation command was found in the README. The package metadata suggests:\n\n"
        + code_fence("bash", inferred)
        + "\n\nThis command is inferred, not source-backed. Verify it against official setup documentation before use.",
        False,
    )


def build_examples_section(analysis: dict) -> tuple[str, int]:
    examples = (analysis.get("readme_usage") or {}).get("examples") or []
    if not examples:
        return (
            "## Source-Backed Examples\n\n"
            "No high-confidence usage example was extracted from the README. Read the source docs and "
            "add at least two verified examples before publishing this draft.",
            0,
        )

    chunks = ["## Source-Backed Examples"]
    for index, item in enumerate(examples[:3], 1):
        title = str(item.get("title") or f"Example {index}")
        chunks.append(f"### {index}. {title}")
        chunks.append(source_note(item))
        chunks.append(code_fence(str(item.get("language") or "text"), str(item.get("code") or "")))
    chunks.append(
        "Run the smallest applicable example before adapting it. Confirm its output and version "
        "compatibility; extraction does not prove that the example still executes successfully."
    )
    return "\n\n".join(chunks), min(len(examples), 3)


def build_skill_md(skill_name: str, analysis: dict) -> str:
    project_name = analysis.get("name") or skill_name
    project_type = analysis.get("recommended_skill_type") or "workflow"
    description_sample = " ".join(str(analysis.get("description_sample") or "").split())
    description_sample = description_sample[:260].rstrip(" .")
    purpose = description_sample or f"the {project_name} {project_type} project"
    env_names = analysis.get("skill_value", {}).get("environment_variables") or []
    env_text = ", ".join(f"`{name}`" for name in env_names) if env_names else "None detected; verify against official documentation."
    value = analysis.get("skill_value", {})
    setup_section, setup_from_readme = build_setup_section(analysis)
    examples_section, example_count = build_examples_section(analysis)
    readme_source = (analysis.get("readme_usage") or {}).get("source") or "None detected"
    validation_examples = (
        f"Execute and verify the {example_count} extracted README example(s); replace stale or incomplete examples."
        if example_count
        else "Add and execute at least two source-backed examples because none were extracted."
    )

    description = (
        f"Use this Skill to install, operate, troubleshoot, or integrate {project_name}. "
        f"It is generated from a local {project_type} project and should trigger for tasks involving "
        f"{project_name} commands, APIs, workflows, configuration, and verified examples."
    )
    return f"""---
name: {skill_name}
description: >
  {description}
---

# {project_name}

This is a generated draft based on `{analysis.get('project')}`. Review commands,
examples, and constraints against the source project before publishing.

## Source Summary

- Type: `{project_type}`
- Purpose: {purpose}
- Conversion value: `{value.get('value')}` ({value.get('score')}/100 heuristic)
- Required environment variables: {env_text}
- README source: `{readme_source}`
- README setup command found: `{str(setup_from_readme).lower()}`
- README usage examples extracted: `{example_count}`

Detailed machine-extracted facts are in `references/project-analysis.json`.

## Setup

{setup_section}

{examples_section}

## Workflow

1. Read `references/project-analysis.json` and the source README/docs relevant to
   the request.
2. Confirm the installed version and required credentials.
3. Use the project's documented interface for the requested operation.
4. Prefer an applicable source-backed example above; otherwise find one in the
   project's docs before composing a new invocation.
5. Verify the output, exit code, API response, or generated artifact.

## Safety And Limits

- Never expose credential values; only name required environment variables.
- Confirm before paid API calls, destructive actions, external publishing, or
  dependency downloads with material cost or size.
- The generated analysis is heuristic and can miss dynamic plugins, private
  services, monorepo packages, and undocumented runtime requirements.

## Validation

- {validation_examples}
- Verify every extracted setup command against the target operating system and version.
- Review `evals/evals.json` and replace generated prompts with realistic cases.
- Run strict validation before packaging.
"""


def build_evals(skill_name: str, project_name: str) -> dict:
    return {
        "skill": skill_name,
        "needs_human_review": True,
        "cases": [
            {
                "id": "happy-01", "kind": "happy", "trigger_expected": True,
                "prompt": f"Use ${skill_name} to install and run a representative {project_name} task.",
                "pass_criteria": ["Uses source-backed commands", "Verifies the result"], "status": "not-run",
            },
            {
                "id": "edge-01", "kind": "edge", "trigger_expected": True,
                "prompt": f"Use ${skill_name} when a required credential or dependency for {project_name} is missing.",
                "pass_criteria": ["Does not invent access", "Identifies the precise unblocker"], "status": "not-run",
            },
            {
                "id": "negative-01", "kind": "mis-trigger", "trigger_expected": False,
                "prompt": f"Answer a generic programming question unrelated to {project_name} without using ${skill_name}.",
                "pass_criteria": ["Does not invoke this Skill"], "status": "not-run",
            },
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap a Skill draft from a local project.")
    parser.add_argument("project_directory")
    parser.add_argument("--output", required=True, help="Parent directory for the generated Skill")
    parser.add_argument("--name", help="Override generated Skill name")
    parser.add_argument("--skills-root", action="append", default=[])
    parser.add_argument("--allow-duplicate", action="store_true")
    args = parser.parse_args()

    roots = [Path(path).resolve() for path in args.skills_root] or None
    try:
        analysis = inspect_project(args.project_directory, roots)
    except Exception as exc:  # noqa: BLE001
        print(f"Bootstrap failed: {exc}", file=sys.stderr)
        return 1

    strong_duplicates = [item for item in analysis.get("duplicate_candidates", []) if item.get("similarity", 0) >= 0.75]
    if strong_duplicates and not args.allow_duplicate:
        print("Bootstrap stopped: a high-similarity Skill already exists:", file=sys.stderr)
        for item in strong_duplicates:
            print(f"- {item['name']} ({item['similarity']}): {item['path']}", file=sys.stderr)
        return 3

    skill_name = normalize_name(args.name or str(analysis.get("name") or Path(args.project_directory).name))
    if not skill_name:
        print("Bootstrap failed: could not derive a valid Skill name", file=sys.stderr)
        return 2
    root = Path(args.output).resolve() / skill_name
    if root.exists():
        print(f"Bootstrap failed: output already exists: {root}", file=sys.stderr)
        return 2

    public_analysis = sanitize_analysis_for_draft(analysis)
    (root / "references").mkdir(parents=True)
    (root / "evals").mkdir()
    (root / "SKILL.md").write_text(build_skill_md(skill_name, public_analysis), encoding="utf-8")
    public_analysis["draft_requires_review"] = True
    (root / "references" / "project-analysis.json").write_text(
        json.dumps(public_analysis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (root / "evals" / "evals.json").write_text(
        json.dumps(build_evals(skill_name, str(public_analysis.get("name") or skill_name)), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    generate_openai_yaml(
        root,
        None,
        f"Operate and integrate {public_analysis.get('name') or skill_name}"[:64],
        f"Use ${skill_name} to complete a verified task with {public_analysis.get('name') or skill_name}.",
    )
    ok, message = validate_skill(root, strict=True)
    if not ok:
        print(f"Bootstrap created a draft but strict validation failed: {message}", file=sys.stderr)
        return 1
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
