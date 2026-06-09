### Task Overview

Refactor the `opencode-environment-bootstrap` code installation structure into a scalable, infrastructure-oriented architecture with three layers:

1. **Agent system** as generic CLI-agnostic configuration
2. **OpenCode CLI** as the default CLI integration for MCPs & agent system
3. **Extendable adapter pattern** for other agent CLI operators (Claude CLI, Copilot CLI)

### Current Problems

| Issue | Location | Impact |
|-------|----------|--------|
| Monolithic `templates/opencode/` bundles agent skills + MCPs + commands + plugins | `templates/opencode/` | Locked to opencode — can't reuse agent methodology for other CLIs |
| MCP definitions exist only in opencode.json format | `opencode.json:3-97` | No single source of truth; every new CLI target requires manual reformatting |
| Agent methodology embedded in CLI-specific templates | `templates/opencode/skills/*/`, `AGENTS.md` | Session lifecycle, delegation DAG, worktree strategy not reusable |
| Hardcoded opencode CLI install path | `installer.py:244-271` | No `--cli` flag concept |
| Verification only checks opencode binary | `installer.py:978` | Can't validate multi-CLI installs |

### Scope Table

| # | Scope | Target Branch | Complexity | Description |
|---|-------|---------------|------------|-------------|
| 1 | Extract agent system into CLI-agnostic `agent-system/` | `feature/20260609-agent-system-layer` | Medium | Move role definitions, workflows, rules out of `templates/opencode/skills/` into pure markdown, strip opencode-specific references |
| 2 | Create `mcp/` YAML catalog | `feature/20260609-mcp-catalog` | Low | One `.yaml` per MCP server (context7, firecrawl, duckdb, etc.) as the canonical source |
| 3 | Write `cli/opencode/` adapter | `feature/20260609-opencode-adapter` | Medium | `adapter.py` that reads `agent-system/` + `mcp/` and generates `opencode.json`, opencode commands, and plugins |
| 4 | Refactor `installer.py` with `--cli` flag | `feature/20260609-cli-aware-installer` | Medium | Add CLI selection phase, route through adapter, restructure deploy and verify steps |
| 5 | Add `cli/claude/` adapter stub | `feature/20260609-claude-adapter-stub` | Low | Minimal structure + README for future Claude Code CLI support |
| 6 | Add `cli/copilot/` adapter stub | `feature/20260609-copilot-adapter-stub` | Low | Minimal structure + README for future Copilot CLI support |

### Architecture

```
agent-system/ + mcp/ → cli/{name}/adapter.py → CLI-specific config (~/.config/opencode/)
```

**Layer 1 — `agent-system/`** (CLI-agnostic):
- `roles/{name}/` — pure markdown role definitions (what a planner/coder does)
- `workflows/` — session lifecycle, delegation DAG, test-fix cycle
- `rules/` — code principles, anti-patterns, safety rules

**Layer 2 — `mcp/`** (CLI-agnostic):
- One YAML per MCP server: `{ command, args, type, env, enabled }`
- All seven existing servers (context7, firecrawl, duckdb, mermaid, metabase-\*, sequential-thinking, serena)

**Layer 3 — `cli/{name}/`** (CLI-specific):
- `opencode/`: adapter.py → `opencode.json` (agent block, MCP block, plugins, commands, skills)
- `claude/`: adapter.py → `.claude.json` `mcpServers` + custom instructions
- `copilot/`: adapter.py → Copilot hosts.json + context config

### What stays (already CLI-agnostic)
- `templates/shell/`, `templates/zed/`, `templates/ghostty/`, `templates/bruno/`
- Dev tool installation (rtk, glab, git-review-cli, opencode-session)
- `bootstrap.sh` entry point

### Risks / Limitations

- **Scope 1 (extract agent-system)**: Must carefully separate generic methodology from opencode-specific syntax (`{file:./skills/}`, `task(subagent_type:)`). Risk of over-abstracting — keep skill files pragmatic.
- **Scope 3 (opencode adapter)**: Adapter must produce output identical to current templates. Review by comparing generated opencode.json against the known-good version.
- **Scope 4 (installer refactor)**: The `--clean`, `--snapshot`, and `--verify` flags must remain functional across all code paths. Test each flag combination.
- **Backward compatibility**: Existing installations (already deployed `~/.config/opencode/`) must continue working. Only new installs see the new structure.
