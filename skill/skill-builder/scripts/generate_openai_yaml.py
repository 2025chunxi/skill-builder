#!/usr/bin/env python3
"""Generate agents/openai.yaml for a Skill directory."""

from __future__ import annotations

import argparse
import re
import textwrap
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


def titleize(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


def compact(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip(" .,;:") + "..."


def quote_yaml(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def generate(skill_dir: str | Path, display_name: str | None, short_description: str | None, default_prompt: str | None) -> Path:
    root = Path(skill_dir).resolve()
    frontmatter = read_frontmatter(root / "SKILL.md")
    name = frontmatter.get("name")
    description = frontmatter.get("description")
    if not isinstance(name, str) or not isinstance(description, str):
        raise ValueError("SKILL.md must contain string name and description")

    display = display_name or titleize(name)
    short = short_description or compact(description, 64)
    prompt = default_prompt or f"Use ${name} to handle this task using its workflow and bundled resources."

    if f"${name}" not in prompt:
        raise ValueError(f"default_prompt must mention ${name}")
    if not 25 <= len(short) <= 96:
        raise ValueError("short_description should be 25-96 characters")

    agents_dir = root / "agents"
    agents_dir.mkdir(exist_ok=True)
    output = agents_dir / "openai.yaml"
    content = textwrap.dedent(
        f"""\
        interface:
          display_name: {quote_yaml(display)}
          short_description: {quote_yaml(short)}
          default_prompt: {quote_yaml(prompt)}

        policy:
          allow_implicit_invocation: true
        """
    )
    output.write_text(content, encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate agents/openai.yaml for a Skill.")
    parser.add_argument("skill_directory")
    parser.add_argument("--display-name")
    parser.add_argument("--short-description")
    parser.add_argument("--default-prompt")
    args = parser.parse_args()

    try:
        output = generate(
            args.skill_directory,
            args.display_name,
            args.short_description,
            args.default_prompt,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"openai.yaml generation failed: {exc}")
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
