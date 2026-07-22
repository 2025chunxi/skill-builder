# Skill Format Specification

Use this reference when validating or packaging a generated Skill.

## Required Structure

```text
skill-name/
  SKILL.md
  scripts/      optional
  references/   optional
  assets/       optional
  agents/
    openai.yaml recommended UI metadata
```

The folder name must exactly match `name` in `SKILL.md`.

## Frontmatter

Use only the required fields unless the current platform explicitly documents
additional supported metadata.

```yaml
---
name: skill-name
description: >
  Action-oriented trigger description.
---
```

Rules:

- `name`: lowercase letters, digits, hyphens; max 64 characters.
- `description`: describe what the Skill does and when to use it; max 1024
  characters for portability.
- Avoid placeholders, angle brackets, secrets, cookies, tokens, and private data.

## Progressive Disclosure

Keep frequently loaded content small.

| Layer | Loaded when | Guidance |
|---|---|---|
| `name` and `description` | Skill discovery | Make triggers precise |
| `SKILL.md` | Skill is used | Keep workflow concise |
| `references/` | Agent chooses to read | Put long docs and examples here |
| `scripts/` | Agent runs/inspects | Put deterministic helpers here |
| `assets/` | Artifact creation | Store templates, images, boilerplate |

## Packaging Rules

- Package exactly one Skill folder per `.skill` file.
- The archive should contain `skill-name/SKILL.md`, not just `SKILL.md` at the
  zip root.
- Exclude `__pycache__`, `node_modules`, `.git`, root `evals`, and compiled
  Python files.
- Validate before packaging.
- Use `quick_validate.py --strict` before release; normal mode is for iterative
  development and backward compatibility.
- Keep `evals/evals.json` in source for forward-testing. The packager excludes
  root `evals/` from the distributable archive.

## agents/openai.yaml

Recommended:

```yaml
interface:
  display_name: "Human Name"
  short_description: "Short scan-friendly description"
  default_prompt: "Use $skill-name to handle this task."

policy:
  allow_implicit_invocation: true
```

Rules:

- Quote string values.
- `default_prompt` must mention `$skill-name`.
- Keep `short_description` short enough for UI chips.
- Do not add icons or brand colors unless real assets exist.

## Common Failures

| Failure | Fix |
|---|---|
| Folder name differs from frontmatter name | Rename folder or update `name` |
| Description is generic | Add concrete trigger phrases |
| `SKILL.md` is too long | Move details to `references/` |
| Generated files contain placeholders | Fill them before packaging |
| Scripts have hidden assumptions | Add args, env vars, and validation checks |
| Multiple nested `SKILL.md` files | Package each Skill separately |
