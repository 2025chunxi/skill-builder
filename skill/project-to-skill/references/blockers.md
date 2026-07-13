# Blockers Reference

Conditions that prevent a project from becoming a Skill. Use the explanation templates when reporting to the user — always respond in the same language the user is using.

## Table of Contents

- Hard blockers: daemon, GUI, hardware, root/kernel access, real-time loop.
- Soft blockers: large dependencies, paid credentials, platform limits, OAuth.
- Partial convertibility: separate reusable interfaces from blocked runtime parts.

---

## Hard Blockers (absolute — no workaround)

### B1: Persistent daemon process

**Condition**: The tool's value only exists while a background server/process stays running continuously (e.g., a database server, message broker, always-on microservice).

**Why it blocks**: Skills are instructions and bundled resources, not long-lived services. A helper process may be started during a task, but the Skill should not depend on an unmanaged daemon staying alive across unrelated turns.

**Exception**: If the project *also* exposes a REST API or CLI interface that returns results in a single call, those interfaces are convertible even if the daemon mode is not.

**English template**:
```
❌ Cannot be converted to a Skill

Reason: This tool requires a continuously running background process (daemon/server).
Skills execute within a single response turn — all processes end when the response ends.
There is no persistent runtime between conversations.

Core blocker: Requires a persistent daemon

Alternative:
- If the service exposes a REST API, that can be wrapped as an API Skill
- If it has a CLI mode that returns results in a single call, that can be wrapped as a CLI Wrapper
- Otherwise, run it as a standalone Docker container or system service and have the agent call its API
```

**Chinese template**:
```
❌ 无法转化为 Skill

原因：该工具需要一个持续运行的后台进程（守护进程/服务器）。
Skill 在单次响应周期内执行——响应结束时所有进程也随之结束。
对话之间不存在持久的运行时。

核心阻断：需要持久后台进程

替代方案：
- 如该服务暴露了 REST API，可封装为 API Skill
- 如有单次调用即返回结果的 CLI 模式，可封装为 CLI Wrapper
- 否则建议以 Docker 容器或系统服务独立运行，再由 Agent 调用其 API
```

---

### B2: GUI / display rendering required

**Condition**: The tool's primary output is a GUI window, or it requires a display server (X11, Wayland, macOS Quartz) to function at all.

**Why it blocks**: The execution environment has no display. GUI-dependent tools will crash at startup with `DISPLAY not set` or similar errors.

**Exception**: Many GUI tools have a headless or batch mode (e.g., `ffmpeg` is headless even though video editing GUIs exist). Always check before declaring unconvertible.

**English template**:
```
❌ Cannot be converted to a Skill

Reason: This tool requires a graphical display environment to run.
The execution environment has no display server — the tool will crash on startup.

Core blocker: Requires GUI / display

Alternative:
- Check if the tool has a --headless, --batch, or CLI mode (many GUI tools do)
- If headless mode exists, we can wrap that subset
- Otherwise, use the tool locally where a display is available
```

---

### B3: Physical hardware device

**Condition**: The tool requires a camera, microphone, USB device, serial port, GPIO pins, Bluetooth, or any physical hardware to function.

**Why it blocks**: The execution environment is containerized with no hardware passthrough.

**Exception**: If the tool can accept pre-recorded file input instead of live hardware input (e.g., transcribe from audio file rather than microphone), that file-based interface is convertible.

**English template**:
```
❌ Cannot be converted to a Skill

Reason: This tool requires a physical hardware device (camera / mic / USB / GPIO).
The execution environment is a container with no hardware passthrough.

Core blocker: Requires physical hardware

Alternative:
- If the tool can read from a file instead (e.g., audio file instead of live mic), we can wrap the file-based interface
- If there's a cloud/API version that accepts uploads, we can wrap that as an API Skill
```

**Chinese template**:
```
❌ 无法转化为 Skill

原因：该工具需要访问物理硬件设备（摄像头 / 麦克风 / USB / GPIO）。
执行环境是容器化环境，无硬件直通。

核心阻断：需要物理硬件设备

替代方案：
- 如该工具支持从文件读取输入（如从音频文件而非麦克风），可封装文件处理接口
- 如有支持文件上传的云端/API 版本，可封装为 API Skill
```

---

### B4: Kernel-level / root access required

**Condition**: The tool requires `sudo`/root privileges, kernel modules, direct disk/partition access, raw socket operations, or system call interception.

**Why it blocks**: The environment is sandboxed and cannot escalate privileges.

**English template**:
```
❌ Cannot be converted to a Skill

Reason: This tool requires kernel-level or root privileges that are not available in the sandboxed execution environment.

Core blocker: Requires root / kernel access

Alternative: No direct alternative. Run this tool in a local environment with the required privileges.
```

**Chinese template**:
```
❌ 无法转化为 Skill

原因：该工具需要内核级或 root 权限，在沙箱化的执行环境中无法获取。

核心阻断：需要 root / 内核级访问权限

替代方案：无直接替代。请在本地拥有完整权限的环境中运行此工具。
```

---

### B5: Real-time bidirectional state loop

**Condition**: The tool operates as a real-time game loop, physics engine, or any system requiring continuous synchronous state updates that cannot be batched into discrete requests.

**Why it blocks**: Skills are request-response, not event-loop based. There is no mechanism for continuous back-and-forth state updates within or between turns.

**Exception**: If the tool supports "run N steps and return result" batch mode, that is convertible.

**English template**:
```
❌ Cannot be converted to a Skill

Reason: This tool requires a continuous real-time event loop (game engine tick / physics simulation / real-time sync).
Skills operate on a request-response model with no persistent event loop.

Core blocker: Requires real-time bidirectional state

Alternative:
- If the tool supports a batch/offline simulation mode ("run N steps, return result"), we can wrap that
- Otherwise, not convertible as a Skill
```

**Chinese template**:
```
❌ 无法转化为 Skill

原因：该工具需要持续的实时事件循环（游戏引擎帧更新 / 物理仿真 / 实时双向同步）。
Skill 采用请求-响应模型，不存在持久事件循环。

核心阻断：需要实时双向状态循环

替代方案：
- 如工具支持批量/离线仿真模式（"运行 N 步，返回结果"），可封装该模式
- 否则无法转化为 Skill
```

---

## Soft Blockers (workable with caveats)

### S1: Very large dependencies (> 2 GB download)

Downloading > 2 GB is slow and may time out. Tell the user this is a "heavy" skill, confirm before proceeding, and add a warning to the generated SKILL.md:

```markdown
> ⚠️ **First-run note**: Dependencies require ~[X] GB download. First run may take [Y] minutes.
```

---

### S2: Paid API / commercial credentials required

Not a blocker. Convert the skill normally. In Setup, clearly state:
- Which env var to set
- Where to get the key (link to signup page)
- Whether a free tier exists and its limits

---

### S3: Platform-specific (Windows / macOS only)

Check if the tool has a Linux equivalent or runs under a compatibility layer. If not available on Linux, add a `compatibility` frontmatter field:

```yaml
compatibility: "macOS/Windows only — this tool is not natively available on Linux; some features may not work in this environment"
```

---

### S4: Complex OAuth / browser-based login only

If the tool only supports browser-based OAuth and no API-key or token-file alternative:
- Document the one-time token acquisition flow
- Show how to export the token to an env var for subsequent use
- Note this in the Setup section

---

## Partial Convertibility

Before declaring a project unconvertible, run this checklist:

```
□ Does it have a CLI mode, headless mode, or API mode that avoids the blocker?
□ Is there an official cloud/hosted version with an HTTP API?
□ Can the useful OUTPUT be obtained via a different interface or tool?
□ Can we convert a subset of features that don't hit the blocker?
```

If any answer is YES → convert the convertible subset and document the rest as limitations in a `## Limitations` section in the generated SKILL.md.
