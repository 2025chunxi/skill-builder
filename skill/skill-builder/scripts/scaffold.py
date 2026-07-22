#!/usr/bin/env python3
"""Create a lean starter Codex Skill directory."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


TYPE_HINTS = {
    "cli": {
        "title": "CLI Wrapper",
        "resources": ("scripts", "references"),
        "body": """## Overview

Use this Skill to run and troubleshoot [tool-name] from the command line.

## Setup

```bash
[install command]
```

## Core Commands

```bash
[tool] --help
```

## Workflow

1. Confirm the tool is installed.
2. Run the smallest command that proves the input is valid.
3. Execute the requested conversion/action.
4. Verify the output file, stdout, or exit code.

## Validation

Record the exact command run and the output path or result that proves success.
""",
    },
    "library": {
        "title": "Library Skill",
        "resources": ("scripts", "references"),
        "body": """## Overview

Use this Skill to write reliable code with [library-name].

## Setup

```bash
[install command]
```

## Core Patterns

```python
# Replace with a minimal working example.
```

## Validation

Run a small executable example before using the library in a larger workflow.
""",
    },
    "api": {
        "title": "API Skill",
        "resources": ("scripts", "references"),
        "body": """## Overview

Use this Skill to call the [service-name] API.

## Setup

Required environment variables:

- `[SERVICE]_API_KEY`

## Authentication

Show the exact header or token exchange pattern here.

## Core Endpoints

Document the highest-value endpoints in `references/api.md` when the API is large.

## Validation

Start with a read-only or low-cost endpoint before making state-changing calls.
""",
    },
    "mcp": {
        "title": "MCP Server Skill",
        "resources": ("references",),
        "body": """## Overview

Use this Skill to install, configure, and use the [server-name] MCP server.

## Setup

Document the startup command, transport type, and required environment variables.

## Tools

List the MCP tools and the situations where each should be used.

## Validation

Verify the server starts and at least one harmless tool call succeeds.
""",
    },
    "knowledge": {
        "title": "Knowledge Skill",
        "resources": ("references",),
        "body": """## Overview

Use this Skill for [domain/workflow] tasks where the process, constraints, or
domain knowledge are not obvious from general model knowledge.

## When To Use

- [specific trigger]
- [specific trigger]

## When Not To Use

- Generic tasks that do not need this domain process.

## Process

1. [step]
2. [step]
3. [step]

## Output Format

Describe the required output structure.
""",
    },
    "workflow": {
        "title": "Workflow Skill",
        "resources": ("scripts", "references"),
        "body": """## Overview

Use this Skill when the task requires a repeatable sequence across multiple
tools or files.

## Pipeline

1. [step and tool]
2. [step and tool]
3. [step and tool]

## Recovery

If a step fails, classify the failure, fix the smallest cause, and rerun from
the last verified checkpoint.

## Validation

List the checks that prove the full workflow succeeded.
""",
    },
    "template": {
        "title": "Template Skill",
        "resources": ("assets", "references"),
        "body": """## Overview

Use this Skill to create or update artifacts that follow the bundled template.

## Assets

- `assets/`: templates, example files, fonts, images, or boilerplate.

## Workflow

1. Inspect the user's requested output.
2. Select the closest bundled asset.
3. Modify only the required content.
4. Render or validate the final artifact.
""",
    },
}


def normalize_name(raw: str) -> str:
    name = raw.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name[:64].strip("-")


def build_skill_md(name: str, skill_type: str) -> str:
    hint = TYPE_HINTS[skill_type]
    return f"""---
name: {name}
description: >
  Use this Skill for [specific task]. Include concrete trigger phrases and the
  durable knowledge, scripts, or assets this Skill provides.
---

# {hint["title"]}

{hint["body"]}
"""


def build_openai_yaml(name: str, skill_type: str) -> str:
    hint = TYPE_HINTS[skill_type]
    display = " ".join(part.capitalize() for part in name.split("-"))
    short = f"Starter {hint['title'].lower()} workflow"
    prompt = f"Use ${name} to handle this task with its generated workflow."
    return f"""interface:
  display_name: "{display}"
  short_description: "{short}"
  default_prompt: "{prompt}"

policy:
  allow_implicit_invocation: true
"""


def build_evals(name: str) -> str:
    payload = {
        "skill": name,
        "needs_human_review": True,
        "cases": [
            {
                "id": "happy-01",
                "kind": "happy",
                "prompt": f"Use ${name} for the most common intended task.",
                "trigger_expected": True,
                "pass_criteria": ["Uses the documented workflow", "Produces a verifiable result"],
                "status": "not-run",
            },
            {
                "id": "edge-01",
                "kind": "edge",
                "prompt": f"Use ${name} when one required input or permission is missing.",
                "trigger_expected": True,
                "pass_criteria": ["Handles the limitation safely", "Identifies the smallest unblocker"],
                "status": "not-run",
            },
            {
                "id": "negative-01",
                "kind": "mis-trigger",
                "prompt": f"Answer a nearby but unrelated request without using ${name}.",
                "trigger_expected": False,
                "pass_criteria": ["Does not invoke this Skill"],
                "status": "not-run",
            },
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def create_scaffold(name: str, skill_type: str, output_dir: str | Path) -> Path:
    normalized = normalize_name(name)
    if not normalized or not NAME_RE.match(normalized):
        raise ValueError("Skill name must contain lowercase letters, digits, or hyphens")
    if skill_type not in TYPE_HINTS:
        raise ValueError("Unknown type: " + skill_type)

    root = Path(output_dir).resolve() / normalized
    if root.exists():
        raise FileExistsError(f"Directory already exists: {root}")

    root.mkdir(parents=True)
    (root / "SKILL.md").write_text(build_skill_md(normalized, skill_type), encoding="utf-8")
    (root / "agents").mkdir()
    (root / "agents" / "openai.yaml").write_text(
        build_openai_yaml(normalized, skill_type),
        encoding="utf-8",
    )
    (root / "evals").mkdir()
    (root / "evals" / "evals.json").write_text(build_evals(normalized), encoding="utf-8")

    for resource in TYPE_HINTS[skill_type]["resources"]:
        (root / resource).mkdir()
        if resource == "scripts":
            (root / resource / "__init__.py").write_text("", encoding="utf-8")
        elif resource == "assets":
            (root / resource / ".gitkeep").write_text("", encoding="utf-8")

    return root


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a starter Codex Skill.")
    parser.add_argument("--name", required=True, help="Skill name or title")
    parser.add_argument(
        "--type",
        required=True,
        choices=sorted(TYPE_HINTS),
        help="Skill type",
    )
    parser.add_argument("--output", default=".", help="Parent output directory")
    args = parser.parse_args()

    try:
        root = create_scaffold(args.name, args.type, args.output)
    except Exception as exc:  # noqa: BLE001
        print(f"Scaffold failed: {exc}", file=sys.stderr)
        return 1

    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
