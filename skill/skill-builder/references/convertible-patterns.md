# Convertible Patterns Reference

Full type taxonomy and content templates. Read the relevant section after Phase 3 architecture decision.

---

## Table of Contents

1. [CLI Wrapper](#1-cli-wrapper)
2. [Library Skill](#2-library-skill)
3. [API Skill](#3-api-skill)
4. [MCP Server Skill](#4-mcp-server-skill)
5. [Knowledge Skill](#5-knowledge-skill)
6. [Workflow Skill](#6-workflow-skill)
7. [Hybrid Patterns](#7-hybrid-patterns)

---

## 1. CLI Wrapper

**When**: The project is invoked as a shell command.
Examples: `ffmpeg`, `yt-dlp`, `tesseract`, `pandoc`, `imagemagick`, `jq`, `ripgrep`, `whisper`.

### Directory structure
```
<skill-name>/
├── SKILL.md
└── scripts/
    ├── __init__.py
    └── run.py          # optional: if output parsing is complex
```

### SKILL.md body template

```markdown
## Setup
```bash
[exact install command: pip install X, uv add X, npm install X, brew install X, etc.]
```
Prefer project-local environments when possible. Only document global/system install flags when the target environment actually requires them.

Verify: `<tool> --version`

## Core Usage

### [Most common task]
```bash
<tool> [flags] <input> [output]
```

### [Second task]
```bash
<tool> [flags] <input>
```

## Flag Reference

| Flag | Type | Description | Example |
|---|---|---|---|
| `-f` | string | Output format | `-f mp4` |
| `--quality` | int | Quality 0-100 | `--quality 80` |

## Examples

### Example 1: [Descriptive name]
```bash
<tool> [complete realistic command]
```
Output: [what gets produced and where]

## Error Handling

| Error | Cause | Fix |
|---|---|---|
| `command not found` | Not installed | Run setup command |
| `[common error]` | [cause] | [fix] |
```

### Content rules
- Include the `--version` verification step so the agent can confirm install succeeded
- Specify whether output goes to stdout, a file, or a directory
- Show pipe examples if stdin/stdout piping is a common pattern
- Note any permissions issues (sudo required? specific file permissions?)

---

## 2. Library Skill

**When**: The project is a language package imported in code.
Examples: `akshare`, `pandas`, `reportlab`, `pillow`, `playwright`, `scipy`.

### Directory structure
```
<skill-name>/
├── SKILL.md
├── scripts/
│   ├── __init__.py
│   └── fetch.py        # name matches the primary function
└── references/
    └── api-ref.md      # if >30 important functions
```

### SKILL.md body template

```markdown
## Setup
```bash
pip install <package-name>
```
Use a virtual environment or project-local package manager when the repository already has one.

[Additional deps if any:]
```bash
pip install dep1 dep2
```

## Core Usage

### [Most common use case]
```python
import <package>

result = <package>.<primary_function>(<realistic_args>)
print(result)
```

### [Second use case]
```python
import <package>

df = <package>.<function>(<realistic_args>)
df.to_csv('output.csv', index=False)
```

## Key Functions

| Function | Args | Returns | Example |
|---|---|---|---|
| `module.func()` | arg1: str | DataFrame | `module.func('000001')` |

→ Full API reference: `references/api-ref.md`

## Examples

### Example 1: [Complete realistic task]
```python
import <package>

data = <package>.<function>(<real_looking_args>)
print(data.head())
```

## Error Handling

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError` | Not installed | Run pip install above |
| `[library error]` | [cause] | [fix] |
```

### Content rules
- Use realistic argument values in examples (real stock codes, real dates, real filenames)
- For data-returning functions: show how to print or inspect the result
- If the library needs initialization (API key, config object): show it in Setup
- For libraries with >30 functions: summarize the top 10 in SKILL.md, link to `references/api-ref.md`

---

## 3. API Skill

**When**: The project is a remote REST or GraphQL service accessed over HTTP.
Examples: OpenAI API, Stripe API, any weather or data API.

### Directory structure
```
<skill-name>/
├── SKILL.md
├── scripts/
│   ├── __init__.py
│   └── client.py       # thin request wrapper
└── references/
    └── endpoints.md    # full endpoint reference
```

### SKILL.md body template

```markdown
## Setup

Set the API key as an environment variable (never hardcode it):
```bash
export <SERVICE>_API_KEY="your-key-here"
```
Get a key at: [signup URL]

[If official SDK exists:]
```bash
pip install <sdk-package>
```

Base URL: `https://api.<service>.com/v1`

## Authentication

Every request requires this header — the env var approach keeps secrets out of code:
```python
import os
headers = {
    "Authorization": f"Bearer {os.environ['<SERVICE>_API_KEY']}",
    "Content-Type": "application/json"
}
```

### OAuth / Token-based auth (if applicable)
```python
import os, requests

# Step 1: exchange credentials for a token
token_response = requests.post(
    "https://auth.<service>.com/oauth/token",
    data={"grant_type": "client_credentials",
          "client_id": os.environ['<SERVICE>_CLIENT_ID'],
          "client_secret": os.environ['<SERVICE>_CLIENT_SECRET']}
)
access_token = token_response.json()["access_token"]

# Step 2: use the token in subsequent requests
headers = {"Authorization": f"Bearer {access_token}"}
```

## Core Endpoints

### [Primary endpoint]
```python
import os, requests

response = requests.post(
    "https://api.<service>.com/v1/<endpoint>",
    headers={"Authorization": f"Bearer {os.environ['<SERVICE>_API_KEY']}",
             "Content-Type": "application/json"},
    json={"param1": "value1", "param2": "value2"}
)
data = response.json()
print(data)
```

## Error Handling

| Status | Meaning | Fix |
|---|---|---|
| 401 | Invalid API key | Verify env var is set and correct |
| 429 | Rate limit | Add exponential backoff retry |
| 422 | Invalid request | Check request body against endpoint docs |

Rate limit: [X req/min or req/day]

→ Full endpoint list: `references/endpoints.md`
```

### Content rules
- Always read the API key from an env var — never hardcode
- Show the full request including headers, not just the URL
- Include response parsing: show `.json()` and how to extract key fields
- For paginated endpoints: show how to walk pages
- If there's an official Python SDK, prefer it over raw `requests`

---

## 4. MCP Server Skill

**When**: The project is itself an MCP (Model Context Protocol) server — it exposes tools that other agents can call.
Examples: a GitHub MCP server, a custom internal API wrapped as MCP, any project with `mcp_server` or FastMCP in its stack.

### Directory structure
```
<skill-name>/
├── SKILL.md
├── scripts/
│   ├── __init__.py
│   └── start_server.sh  # startup helper if needed
└── references/
    └── tools.md         # full tool list with args and return types
```

### SKILL.md body template

```markdown
## Overview
[What external service or data this MCP server exposes, and when to connect to it.]

## Setup

Install the server:
```bash
[npm install -g <package> / pip install <package> / clone + build]
```

Install the MCP Python SDK (needed to call this server from Python):
```bash
pip install mcp
```

Set credentials:
```bash
export <SERVICE>_API_KEY="..."
```

## Transport

This server uses [stdio / streamable HTTP].

[For stdio:]
Configure in your MCP client:
```json
{
  "mcpServers": {
    "<name>": {
      "command": "<executable>",
      "args": ["<arg1>"],
      "env": { "<SERVICE>_API_KEY": "your-key" }
    }
  }
}
```

[For HTTP:]
Start the server:
```bash
<start command>  # default port: XXXX
```
Connect from MCP client at: `http://localhost:XXXX/mcp`

## Available Tools

| Tool | Description | Key args |
|---|---|---|
| `<tool_name>` | [what it does] | `arg1: str`, `arg2: int` |

→ Full tool reference with schemas: `references/tools.md`

## Usage Pattern

```python
# Example: calling this MCP server from Python via the MCP SDK
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def use_server():
    async with stdio_client(StdioServerParameters(
        command="<executable>", args=["<arg>"]
    )) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("<tool_name>", {"arg1": "value"})
            print(result)

asyncio.run(use_server())
```

## Error Handling

| Error | Cause | Fix |
|---|---|---|
| Connection refused | Server not started | Run start command above |
| `Tool not found` | Wrong tool name | Check references/tools.md for exact names |
| Auth error | Missing env var | Set the required env vars in Setup |
```

### Content rules
- Identify the transport type (stdio vs HTTP) from the project README
- List all available tools with their argument schemas
- Show how to invoke the server from a client, not just how to start it
- Note any stateful behavior (session vs stateless)

---

## 5. Knowledge Skill

**When**: The project is a methodology, framework, SOP, design pattern, or documentation set with no code to run.

### Directory structure
```
<skill-name>/
├── SKILL.md
└── references/
    ├── process.md      # detailed step-by-step breakdown
    └── examples.md     # 3-5 worked examples
```

### SKILL.md body template

```markdown
## Overview
[What this methodology is, what problem it solves, when to apply it. 2–3 sentences.]

## When to Apply

Use this when:
- [Condition 1]
- [Condition 2]

Do NOT use this when:
- [Anti-pattern 1 — important to be specific here]

## Core Process

### Step 1: [Name]
[What to do, why it matters, what the output is.]
Decision point: if [X] then [Y]; if [Z] then [W].

### Step 2: [Name]
[Input from Step 1. What transformation happens. Output.]

### Step N: [Final step]
[Description. Final output format.]

## Key Principles

1. **[Principle]**: [Why it matters — one sentence]
2. **[Principle]**: [Why it matters]

## Output Format

Always produce output in this structure:
```
[Exact template]
```

## Quick Reference
- [ ] [Checklist item 1]
- [ ] [Checklist item 2]

→ Detailed process: `references/process.md`
→ Worked examples: `references/examples.md`
```

### Content rules
- "When NOT to apply" is as important as "when to apply" — prevents mis-triggering
- Decision trees for branching logic are more useful than linear step lists
- The Output Format section is critical: tell the agent exactly what to produce
- Examples should show the full input → process → output arc

---

## 6. Workflow Skill

**When**: The project involves 3+ tools working together in a defined sequence.
Examples: a data pipeline (fetch → clean → analyze → visualize), a content pipeline (research → draft → review → format).

### Directory structure
```
<skill-name>/
├── SKILL.md
├── scripts/
│   ├── __init__.py
│   └── pipeline.py     # orchestrates the full flow if deterministic
└── references/
    ├── tools.md        # docs for each tool in the pipeline
    └── examples.md
```

### SKILL.md body template

```markdown
## Overview
[What this workflow produces. What tools it chains. When to run it.]

## Setup
```bash
pip install tool1 tool2 tool3
```
All deps in one install call because pip resolves version conflicts across packages simultaneously.

[Credentials:]
```bash
export <SERVICE>_API_KEY="..."
```

## Pipeline

```
[Input] → [Step 1: tool1] → [Step 2: tool2] → [Step 3: tool3] → [Output]
```

### Step 1: [Name] (tool: tool1)
Input: [what comes in]
Output: [what comes out]
```python/bash
[exact code or command]
```

### Step 2: [Name] (tool: tool2)
Input: output from Step 1 ([format])
Output: [what comes out]

### Step N: Output
[Final output: format, location, how to use it]

## Run Full Pipeline
```bash
python scripts/pipeline.py --input <file> --output <dir>
```

## Error Recovery

| Step | Common failure | Resume from here? | Fix |
|---|---|---|---|
| Step 1 | [error] | No | [fix] |
| Step 2 | [error] | Yes (keep Step 1 output) | [fix] |
```

### Content rules
- Show the pipeline as a flow diagram at the top — the sequence is the main idea
- Each step should state its input source explicitly (previous step's output or original input?)
- If intermediate outputs can be reused (resume from step N), document this
- Note which steps are slow so the agent can set user expectations

---

## 7. Hybrid Patterns

Some projects span multiple types. Handle as:

| Combination | Strategy |
|---|---|
| CLI + Library (same tool has both interfaces) | Pick whichever the user needs; mention the other in Overview |
| API + Knowledge (API has specific best practices) | Use API Skill type; add a `## Best Practices` section |
| MCP server + REST API (same project exposes both) | Use MCP Server type; document the REST API in references/ as an alternative |
| Multiple tools in a domain | Workflow Skill referencing each tool's own docs in references/ |
| Methodology that uses specific tools | Knowledge Skill with a `## Required Tools` setup section |
