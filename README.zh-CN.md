# project-to-skill

用于判断本地项目是否值得转换成 Codex Skill，并自动生成、校验和打包结果。

> 当前状态：`v0.1.0-beta`。确定性工作流已经测试；自然语言触发仍需在更多
> Codex 版本和项目类型中持续验证。

[English](README.md)

## 主要能力

- 分析项目生态、元数据、文件、测试、文档和环境变量名称。
- 判断转换 Skill 是否真的增加价值，避免只包装通用提示词。
- 检查本机已有 Skill，发现高相似度重复项。
- 从 README 提取安装命令和最多三个带来源位置的真实示例。
- 脱敏疑似凭据，默认移除源项目和已安装 Skill 的绝对路径。
- 生成 `SKILL.md`、`agents/openai.yaml`、eval 和项目分析。
- 执行 Python 3.11 兼容的严格校验并打包为 `.skill`。

## 安装

从最新 GitHub Release 下载 `project-to-skill.skill`，将归档中的
`project-to-skill` 顶层目录安装到 `$CODEX_HOME/skills` 或
`~/.codex/skills`，然后新建 Codex 任务以重新加载元数据。

GitHub 安装器可使用源码路径 `skill/project-to-skill`。

## 构建与验证

要求 Python 3.11 或更高版本，以及 PyYAML 6.x。

```bash
python -m pip install -r requirements.txt
python scripts/build_release.py
```

输出：`dist/project-to-skill.skill`。

构建会运行 README 提取和安全回归测试、严格 Skill 校验、归档检查，以及覆盖
整个仓库的密钥、PII、个人路径和归档安全扫描。

## 隐私边界

生成的 Skill 默认不包含源项目或本机已安装 Skill 的绝对路径。独立分析器也
默认脱敏，只有私有本地诊断才应使用 `--include-local-paths`。

README 提取有来源依据，但不代表命令已经执行成功。发布生成的 Skill 前仍需
实际运行保留的命令和示例。

## 许可证

MIT，详见 [LICENSE](LICENSE)。
