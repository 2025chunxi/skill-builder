#!/usr/bin/env python3
"""Inspect a local project and judge whether it is worth converting to a Skill."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover - Python 3.11+ is expected.
    tomllib = None

import yaml


IGNORE_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", "__pycache__", "node_modules",
    "dist", "build", ".next", ".venv", "venv", "target", "coverage",
}
TEXT_SUFFIXES = {
    ".md", ".txt", ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".toml",
    ".yaml", ".yml", ".rs", ".go", ".java", ".sh", ".ps1",
}
ENV_RE = re.compile(r"\b([A-Z][A-Z0-9_]{2,}(?:_KEY|_TOKEN|_SECRET|_URL|_HOST|_PORT|_ID))\b")
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})\s*([^\s`]*)?.*$")
INLINE_CODE_RE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
INSTALL_COMMAND_RE = re.compile(
    r"^(?:(?:sudo|python(?:3)?\s+-m)\s+)?(?:"
    r"pip(?:3)?\s+install|pipx\s+install|uv\s+(?:add|sync|tool\s+install)|"
    r"poetry\s+(?:add|install)|npm\s+(?:install|i)|pnpm\s+(?:add|install|i)|"
    r"yarn\s+(?:add|install)|bun\s+(?:add|install)|cargo\s+(?:add|install)|"
    r"go\s+install|dotnet\s+tool\s+install|gem\s+install|composer\s+require|"
    r"brew\s+install|apt(?:-get)?\s+install|dnf\s+install|yum\s+install|"
    r"docker\s+pull"
    r")\b",
    re.IGNORECASE,
)
SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?i)(\b(?:[a-z][a-z0-9_]*_)?(?:api[_-]?key|access[_-]?token|auth[_-]?token|token|secret|password)\b"
    r"\s*[:=]\s*)([\"']?)([^\"'\s,}]+)([\"']?)"
)
BEARER_RE = re.compile(r"(?i)(\bbearer\s+)([A-Za-z0-9._-]{16,})")
SECRET_TOKEN_RE = re.compile(
    r"sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}"
)
INSTALL_HEADINGS = (
    "install", "setup", "prerequisite", "getting started", "quick start",
    "安装", "配置", "快速开始", "入门",
)
PURE_INSTALL_HEADINGS = ("install", "setup", "prerequisite", "安装", "配置")
USAGE_HEADINGS = (
    "usage", "example", "quick start", "getting started", "tutorial", "demo",
    "command", "api", "integration", "使用", "示例", "快速开始", "入门", "教程",
)
SHELL_LANGUAGES = {"", "bash", "sh", "shell", "console", "terminal", "zsh", "fish", "powershell", "ps1", "cmd"}
PROGRAMMING_LANGUAGES = {
    "python", "py", "pycon", "python-console", "python-repl",
    "javascript", "js", "typescript", "ts", "tsx", "jsx",
    "go", "rust", "java", "csharp", "cs", "ruby", "php", "kotlin", "swift",
}


def read_text(path: Path, limit: int = 200_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""


def find_readme(root: Path, files: list[Path]) -> Path | None:
    candidates = [path for path in files if path.name.lower().startswith("readme")]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda path: (
            len(path.relative_to(root).parts),
            0 if path.suffix.lower() in {".md", ".markdown"} else 1,
            path.relative_to(root).as_posix().lower(),
        ),
    )


def _clean_heading(raw: str) -> str:
    text = re.sub(r"!\[[^]]*\]\([^)]*\)", "", raw)
    text = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", text)
    return re.sub(r"[*_`]+", "", text).strip()


def _parse_markdown_code_blocks(text: str) -> list[dict]:
    blocks: list[dict] = []
    heading = "README"
    fence = ""
    language = ""
    start_line = 0
    code_lines: list[str] = []

    for line_number, line in enumerate(text.splitlines(), 1):
        if fence:
            stripped = line.lstrip()
            if stripped.startswith(fence[0]) and len(stripped) - len(stripped.lstrip(fence[0])) >= len(fence):
                blocks.append({
                    "section": heading,
                    "language": language.lower(),
                    "code": "\n".join(code_lines).strip(),
                    "line": start_line,
                })
                fence = ""
                language = ""
                code_lines = []
            else:
                code_lines.append(line)
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match:
            heading = _clean_heading(heading_match.group(2)) or "README"
            continue

        fence_match = FENCE_RE.match(line)
        if fence_match:
            fence = fence_match.group(1)
            language = (fence_match.group(2) or "").strip()
            start_line = line_number + 1

    return blocks


def _strip_shell_prompt(line: str) -> str:
    return re.sub(r"^\s*(?:(?:PS\s*)?>|\$)\s+", "", line).strip()


def _logical_commands(code: str, base_line: int):
    current: list[str] = []
    current_line = base_line
    for offset, raw in enumerate(code.splitlines()):
        line = _strip_shell_prompt(raw)
        if not line or line.startswith("#"):
            if current:
                yield "\n".join(current), current_line
                current = []
            continue
        if not current:
            current_line = base_line + offset
        current.append(line)
        if not line.rstrip().endswith(("\\", "`", "^")):
            yield "\n".join(current), current_line
            current = []
    if current:
        yield "\n".join(current), current_line


def _redact_sensitive(text: str) -> str:
    safe_markers = ("$", "%", "YOUR_", "EXAMPLE", "REPLACE", "REDACTED", "XXX", "TEST_")

    def replace_assignment(match: re.Match) -> str:
        value = match.group(3)
        if value.upper().startswith(safe_markers):
            return match.group(0)
        quote = match.group(2) if match.group(2) == match.group(4) else ""
        return f"{match.group(1)}{quote}REDACTED{quote}"

    text = SENSITIVE_ASSIGNMENT_RE.sub(replace_assignment, text)
    text = BEARER_RE.sub(r"\1REDACTED", text)
    return SECRET_TOKEN_RE.sub("REDACTED", text)


def _readme_summary(text: str, limit: int = 500) -> str:
    paragraphs: list[str] = []
    current: list[str] = []
    in_fence = False
    fence_char = ""

    for line in text.splitlines():
        fence_match = FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if not in_fence:
                in_fence = True
                fence_char = marker[0]
            elif marker[0] == fence_char:
                in_fence = False
            continue
        if in_fence or HEADING_RE.match(line):
            continue
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
                if paragraphs:
                    break
            continue
        if (
            stripped.startswith(("![", "[![", "<", "|", "- ", "* ", "> "))
            or re.fullmatch(r"[-=:| ]+", stripped)
        ):
            continue
        cleaned = re.sub(r"!\[[^]]*\]\([^)]*\)", "", stripped)
        cleaned = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", cleaned)
        cleaned = re.sub(r"[*_`]", "", cleaned).strip()
        if cleaned:
            current.append(cleaned)
    if current and not paragraphs:
        paragraphs.append(" ".join(current))
    return " ".join(paragraphs)[:limit].strip()


def _contains_heading_term(section: str, terms: tuple[str, ...]) -> bool:
    lowered = section.lower()
    return any(term in lowered for term in terms)


def _has_usage_action(code: str, language: str) -> bool:
    if language in PROGRAMMING_LANGUAGES:
        return bool(re.search(
            r"(?m)^\s*(?:(?:>>>|\.\.\.)\s*)?(?:from\s+\S+\s+import|import\s+\S+|const\s+\S+\s*=|"
            r"let\s+\S+\s*=|require\s*\(|func\s+\w+|fn\s+\w+|public\s+class)",
            code,
        ))
    for command, _ in _logical_commands(code, 1):
        first_line = command.splitlines()[0]
        if INSTALL_COMMAND_RE.match(first_line):
            continue
        if re.match(r"^(?:cd|export|set|git\s+clone)\b", first_line, re.IGNORECASE):
            continue
        if re.match(r"^(?:curl|wget|python|node|npx|docker|kubectl|gh|[A-Za-z0-9_.\\/-]+)\b", first_line):
            return True
    return False


def extract_readme_usage(root: Path, readme: Path | None) -> dict:
    if readme is None:
        return {"source": None, "install_commands": [], "examples": []}

    text = read_text(readme)
    source = readme.relative_to(root).as_posix()
    blocks = _parse_markdown_code_blocks(text)
    install_commands: list[dict] = []
    seen_commands: set[str] = set()

    for block in blocks:
        if block["language"] not in SHELL_LANGUAGES and not _contains_heading_term(block["section"], INSTALL_HEADINGS):
            continue
        for command, line in _logical_commands(block["code"], block["line"]):
            first_line = command.splitlines()[0]
            if not INSTALL_COMMAND_RE.match(first_line):
                continue
            cleaned = _redact_sensitive(command[:800])
            key = " ".join(cleaned.lower().split())
            if key in seen_commands:
                continue
            seen_commands.add(key)
            install_commands.append({
                "command": cleaned,
                "section": block["section"],
                "line": line,
                "source": source,
            })

    for line_number, line in enumerate(text.splitlines(), 1):
        for inline in INLINE_CODE_RE.findall(line):
            command = _strip_shell_prompt(inline)
            if not INSTALL_COMMAND_RE.match(command):
                continue
            cleaned = _redact_sensitive(command[:800])
            key = " ".join(cleaned.lower().split())
            if key not in seen_commands:
                seen_commands.add(key)
                install_commands.append({
                    "command": cleaned,
                    "section": "README prose",
                    "line": line_number,
                    "source": source,
                })

    candidates: list[tuple[int, int, dict]] = []
    for order, block in enumerate(blocks):
        code = block["code"].strip()
        if not code or len(code) < 12:
            continue
        language = block["language"]
        score = 0
        if _contains_heading_term(block["section"], USAGE_HEADINGS):
            score += 6
        if _contains_heading_term(block["section"], PURE_INSTALL_HEADINGS):
            score -= 4
        if language in PROGRAMMING_LANGUAGES:
            score += 3
        elif language in SHELL_LANGUAGES:
            score += 2
        else:
            score -= 2
        if _has_usage_action(code, language):
            score += 3
        else:
            score -= 4
        if score < 3:
            continue
        clipped = "\n".join(code.splitlines()[:50])[:2000].rstrip()
        candidates.append((score, order, {
            "title": block["section"],
            "language": language or "text",
            "code": _redact_sensitive(clipped),
            "line": block["line"],
            "source": source,
        }))

    examples: list[dict] = []
    seen_examples: set[str] = set()
    for _, _, example in sorted(candidates, key=lambda item: (-item[0], item[1])):
        key = " ".join(example["code"].lower().split())
        if key in seen_examples:
            continue
        seen_examples.add(key)
        examples.append(example)
        if len(examples) == 3:
            break

    return {
        "source": source,
        "summary": _redact_sensitive(_readme_summary(text)),
        "install_commands": install_commands[:8],
        "examples": examples,
    }


def iter_project_files(root: Path, max_files: int):
    count = 0
    for path in root.rglob("*"):
        if count >= max_files:
            break
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in IGNORE_DIRS for part in rel.parts):
            continue
        count += 1
        yield path


def load_json(path: Path) -> dict:
    try:
        data = json.loads(read_text(path))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def load_toml(path: Path) -> dict:
    if tomllib is None:
        return {}
    try:
        data = tomllib.loads(read_text(path))
        return data if isinstance(data, dict) else {}
    except (ValueError, tomllib.TOMLDecodeError):
        return {}


def detect_metadata(root: Path) -> dict:
    result: dict[str, object] = {"ecosystems": [], "package_names": []}

    package_json = root / "package.json"
    if package_json.exists():
        data = load_json(package_json)
        result["ecosystems"].append("node")
        if data.get("name"):
            result["package_names"].append({"registry": "npm", "name": data["name"]})
        result["node"] = {
            "name": data.get("name"),
            "description": data.get("description"),
            "bin": data.get("bin"),
            "scripts": sorted((data.get("scripts") or {}).keys()),
            "dependency_count": len(data.get("dependencies") or {}),
            "dev_dependency_count": len(data.get("devDependencies") or {}),
        }

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        data = load_toml(pyproject)
        project = data.get("project") or {}
        poetry = ((data.get("tool") or {}).get("poetry") or {})
        name = project.get("name") or poetry.get("name")
        result["ecosystems"].append("python")
        if name:
            result["package_names"].append({"registry": "pypi", "name": name})
        result["python"] = {
            "name": name,
            "description": project.get("description") or poetry.get("description"),
            "scripts": sorted((project.get("scripts") or {}).keys()),
            "dependency_count": len(project.get("dependencies") or poetry.get("dependencies") or {}),
        }

    cargo = root / "Cargo.toml"
    if cargo.exists():
        data = load_toml(cargo)
        package = data.get("package") or {}
        result["ecosystems"].append("rust")
        if package.get("name"):
            result["package_names"].append({"registry": "crates", "name": package["name"]})
        result["rust"] = {
            "name": package.get("name"),
            "description": package.get("description"),
            "dependency_count": len(data.get("dependencies") or {}),
        }

    if (root / "go.mod").exists():
        result["ecosystems"].append("go")
    if any((root / name).exists() for name in ("Dockerfile", "docker-compose.yml", "compose.yaml")):
        result["containerized"] = True
    return result


def classify_project(root: Path, files: list[Path], metadata: dict) -> tuple[str, list[str]]:
    names = {path.name.lower() for path in files}
    text_sample = "\n".join(
        read_text(path, 30_000).lower()
        for path in files
        if path.suffix.lower() in {".md", ".py", ".js", ".ts", ".toml"}
    )[:500_000]
    signals: list[str] = []

    if "mcp" in text_sample and any(term in text_sample for term in ("fastmcp", "mcp server", "serversession")):
        signals.append("MCP server markers found")
        return "mcp", signals
    if any(name in names for name in ("openapi.json", "openapi.yaml", "swagger.json")):
        signals.append("OpenAPI/Swagger definition found")
        return "api", signals
    if any(term in text_sample for term in ("argparse", "click.command", "typer.typer", "commander(", "clap::")):
        signals.append("CLI framework markers found")
        return "cli", signals
    if metadata.get("package_names"):
        signals.append("Publishable package metadata found")
        return "library", signals
    if any(part.lower() in {"templates", "assets"} for path in files for part in path.parts):
        signals.append("Reusable templates/assets found")
        return "template", signals
    if any(part.lower() in {"docs", "references", "playbooks", "sop"} for path in files for part in path.parts):
        signals.append("Documentation/process corpus found")
        return "knowledge", signals
    signals.append("No dominant executable interface detected")
    return "workflow", signals


def score_value(root: Path, files: list[Path], metadata: dict, project_type: str) -> dict:
    names = {path.name.lower() for path in files}
    dirs = {part.lower() for path in files for part in path.relative_to(root).parts[:-1]}
    text_files = [path for path in files if path.suffix.lower() in TEXT_SUFFIXES]
    env_names: set[str] = set()
    for path in text_files[:300]:
        env_names.update(ENV_RE.findall(read_text(path, 50_000)))

    dimensions = {
        "specialized_interface": 20 if project_type in {"api", "mcp", "cli", "library"} else 10,
        "repeatable_workflow": 20 if any(d in dirs for d in {"scripts", "examples", "workflows", "pipelines"}) else 10,
        "bundled_assets": 15 if any(d in dirs for d in {"templates", "assets", "schemas"}) else 5,
        "documentation": 15 if any(name.startswith("readme") for name in names) and "docs" in dirs else 8,
        "fragile_constraints": 15 if env_names or metadata.get("containerized") or project_type in {"api", "mcp"} else 5,
        "testability": 15 if any(d in dirs for d in {"test", "tests", "__tests__", "examples"}) else 5,
    }
    score = sum(dimensions.values())
    if len(files) < 4:
        score = max(0, score - 20)
    if not text_files:
        score = max(0, score - 20)

    value = "high" if score >= 70 else "medium" if score >= 45 else "low"
    return {
        "score": score,
        "value": value,
        "dimensions": dimensions,
        "environment_variables": sorted(env_names),
        "note": "Heuristic score: confirm with real trigger examples and forward-tests before publishing.",
    }


def parse_skill_frontmatter(path: Path) -> dict:
    text = read_text(path)
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    try:
        data = yaml.safe_load(text[4:end])
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}


def token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


def duplicate_candidates(name: str, description: str, roots: list[Path]) -> list[dict]:
    candidates = []
    wanted_tokens = token_set(name + " " + description)
    for skills_root in roots:
        if not skills_root.exists():
            continue
        for skill_md in skills_root.rglob("SKILL.md"):
            data = parse_skill_frontmatter(skill_md)
            other_name = str(data.get("name") or "")
            other_desc = str(data.get("description") or "")
            if not other_name:
                continue
            other_tokens = token_set(other_name + " " + other_desc)
            union = wanted_tokens | other_tokens
            jaccard = len(wanted_tokens & other_tokens) / len(union) if union else 0.0
            name_ratio = SequenceMatcher(None, name, other_name).ratio()
            similarity = round(max(jaccard, name_ratio), 3)
            if similarity >= 0.45:
                candidates.append({
                    "name": other_name,
                    "path": str(skill_md.parent),
                    "similarity": similarity,
                })
    return sorted(candidates, key=lambda item: item["similarity"], reverse=True)[:10]


def sanitize_analysis_for_sharing(analysis: dict) -> dict:
    """Return an analysis copy without absolute local project or Skill paths."""
    public = deepcopy(analysis)
    source_path = str(public.get("project") or "")
    public["project"] = Path(source_path).name if source_path else str(public.get("name") or "local-project")
    for candidate in public.get("duplicate_candidates") or []:
        if isinstance(candidate, dict):
            candidate.pop("path", None)
    public["privacy"] = {
        "local_paths_omitted": True,
        "note": "Use --include-local-paths only for private local diagnostics.",
    }
    return public


def inspect_project(project_directory: str | Path, skills_roots: list[Path] | None = None, max_files: int = 3000) -> dict:
    root = Path(project_directory).resolve()
    if not root.is_dir():
        raise ValueError(f"Project directory not found: {root}")

    files = list(iter_project_files(root, max_files))
    metadata = detect_metadata(root)
    project_type, type_signals = classify_project(root, files, metadata)
    extension_counts = Counter(path.suffix.lower() or "[no-extension]" for path in files)
    readme = find_readme(root, files)
    readme_usage = extract_readme_usage(root, readme)
    description = ""
    for section in (metadata.get("node"), metadata.get("python"), metadata.get("rust")):
        if isinstance(section, dict) and section.get("description"):
            description = str(section["description"])
            break
    if not description and readme:
        description = str(readme_usage.get("summary") or "")

    name = str(
        next((item.get("name") for item in metadata.get("package_names", []) if item.get("name")), root.name)
    )
    value = score_value(root, files, metadata, project_type)
    default_roots = []
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        default_roots.append(Path(codex_home) / "skills")
    default_roots.append(Path.home() / ".codex" / "skills")
    skill_roots = skills_roots or default_roots
    duplicates = duplicate_candidates(name, description, skill_roots)

    return {
        "project": str(root),
        "name": name,
        "description_sample": description,
        "recommended_skill_type": project_type,
        "type_signals": type_signals,
        "metadata": metadata,
        "inventory": {
            "scanned_files": len(files),
            "extension_counts": dict(extension_counts.most_common(20)),
            "has_readme": bool(readme),
            "has_docs": any("docs" in path.relative_to(root).parts for path in files),
            "has_examples": any("examples" in path.relative_to(root).parts for path in files),
            "has_tests": any(part.lower() in {"test", "tests", "__tests__"} for path in files for part in path.parts),
        },
        "readme_usage": readme_usage,
        "skill_value": value,
        "duplicate_candidates": duplicates,
        "recommendation": (
            "convert" if value["value"] == "high" and not duplicates
            else "review-existing-skill" if duplicates
            else "convert-selectively" if value["value"] == "medium"
            else "do-not-convert-without-more-domain-assets"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a local project for Skill conversion.")
    parser.add_argument("project_directory")
    parser.add_argument("--skills-root", action="append", default=[])
    parser.add_argument("--max-files", type=int, default=3000)
    parser.add_argument("--output", help="Optional JSON output path")
    parser.add_argument(
        "--include-local-paths",
        action="store_true",
        help="Include absolute project and duplicate-Skill paths in local diagnostic output",
    )
    args = parser.parse_args()

    try:
        result = inspect_project(
            args.project_directory,
            [Path(path).resolve() for path in args.skills_root] or None,
            args.max_files,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if not args.include_local_paths:
        result = sanitize_analysis_for_sharing(result)

    output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
