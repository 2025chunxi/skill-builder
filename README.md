# project-to-skill

A Codex Skill for deciding whether a local project is worth converting into a
reusable Skill, then generating, validating, and packaging the result.

> Status: `v0.1.0-beta`. The deterministic workflow is tested; trigger behavior
> should continue to be evaluated across Codex versions and project types.

[简体中文](README.zh-CN.md)

## What It Does

- Inspects project ecosystem, metadata, files, tests, docs, and environment names.
- Scores whether Skill conversion adds value instead of wrapping generic prompts.
- Checks installed Skill directories for likely duplicates.
- Extracts README installation commands and up to three source-backed examples.
- Redacts sensitive-looking values and omits absolute local paths by default.
- Generates `SKILL.md`, `agents/openai.yaml`, eval cases, and project analysis.
- Runs Python 3.11-compatible strict validation and packages a `.skill` archive.

## Why It Matters

Strong models can write instructions, but conversion quality still depends on
repeatable source inspection, duplicate detection, evidence tracking, privacy
protection, validation, and deterministic packaging. This Skill makes those
parts explicit and testable.

## Install

Download `project-to-skill.skill` from the latest GitHub Release and extract its
top-level `project-to-skill` folder under `$CODEX_HOME/skills` or
`~/.codex/skills`. Start a new Codex task so Skill metadata is reloaded.

The source Skill lives at `skill/project-to-skill` for GitHub-based installers.

## Build And Verify

Requires Python 3.11 or newer and PyYAML 6.x.

```bash
python -m pip install -r requirements.txt
python scripts/build_release.py
```

Output: `dist/project-to-skill.skill`.

The build runs README extraction and security regression tests, strict Skill
validation, archive checks, and a repository-wide secret, PII, private-path, and
archive-safety scan.

## Privacy Boundary

Generated Skill artifacts omit absolute source-project and installed-Skill paths.
Standalone inspector output is also redacted by default. Use
`--include-local-paths` only for private local diagnostics.

README extraction is source-backed but not execution verification. Run retained
commands and examples before publishing a generated Skill.

## License

MIT. See [LICENSE](LICENSE).
