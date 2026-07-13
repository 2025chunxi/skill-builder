#!/usr/bin/env python3
"""Generate a reviewable eval manifest for a Skill."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml


def read_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md has no YAML frontmatter")
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError("SKILL.md frontmatter is not closed")
    data = yaml.safe_load(text[4:end])
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a mapping")
    return data


def default_task(description: str) -> str:
    sentence = re.split(r"(?<=[.!?])\s+", " ".join(description.split()))[0]
    return sentence[:220]


def make_case(case_id: str, prompt: str, trigger_expected: bool, kind: str) -> dict:
    criteria = [
        "Uses the Skill's documented workflow and bundled resources",
        "Produces a verifiable result or clearly identifies the blocker",
    ] if trigger_expected else [
        "Does not invoke or rely on this Skill for an unrelated nearby request",
    ]
    return {
        "id": case_id,
        "kind": kind,
        "prompt": prompt,
        "trigger_expected": trigger_expected,
        "pass_criteria": criteria,
        "status": "not-run",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate evals/evals.json for a Skill.")
    parser.add_argument("skill_directory")
    parser.add_argument("--happy", action="append", default=[])
    parser.add_argument("--edge", action="append", default=[])
    parser.add_argument("--negative", action="append", default=[])
    args = parser.parse_args()

    root = Path(args.skill_directory).resolve()
    try:
        data = read_frontmatter(root / "SKILL.md")
    except Exception as exc:  # noqa: BLE001
        print(f"Eval generation failed: {exc}", file=sys.stderr)
        return 1

    name = str(data.get("name") or root.name)
    description = str(data.get("description") or "")
    base = default_task(description)
    happy = args.happy or [f"Use ${name} to complete this request: {base}"]
    edge = args.edge or [f"Use ${name} for a request with missing access or incomplete input; recover safely and report what is needed."]
    negative = args.negative or [f"Answer a simple unrelated factual question without using ${name}."]

    cases = []
    for index, prompt in enumerate(happy, 1):
        cases.append(make_case(f"happy-{index:02d}", prompt, True, "happy"))
    for index, prompt in enumerate(edge, 1):
        cases.append(make_case(f"edge-{index:02d}", prompt, True, "edge"))
    for index, prompt in enumerate(negative, 1):
        cases.append(make_case(f"negative-{index:02d}", prompt, False, "mis-trigger"))

    payload = {
        "skill": name,
        "needs_human_review": not bool(args.happy and args.edge and args.negative),
        "cases": cases,
    }
    evals_dir = root / "evals"
    evals_dir.mkdir(exist_ok=True)
    output = evals_dir / "evals.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
