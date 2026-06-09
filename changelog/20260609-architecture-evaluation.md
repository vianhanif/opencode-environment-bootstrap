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
- `claude/`: adapter.py → `.claude.json`/`.claude/agents/` + `CLAUDE.md`
- `copilot/`: adapter.py → `~/.copilot/settings.json`/`mcp-config.json`/`agents/`

### What stays (already CLI-agnostic)
- `templates/shell/`, `templates/zed/`, `templates/ghostty/`, `templates/bruno/`
- Dev tool installation (rtk, glab, git-review-cli, opencode-session)
- `bootstrap.sh` entry point

---

## Adapter Feasibility — Per-Operator Analysis

### Common: MCP Server Translation

All three CLIs support MCP with similar schemas. Translation is a direct key-mapping:

| Concept | OpenCode | Claude CLI | Copilot CLI |
|---------|----------|------------|-------------|
| Local server | `{ type: "local", command: ["npx", ...], environment: {...} }` | `{ type: "stdio", command: "npx", args: [...], env: {...} }` | `{ type: "local", command: "npx", args: [...], env: {...} }` |
| Remote server | `{ type: "remote", url: "...", headers: {...} }` | `{ type: "http", url: "...", headers: {...} }` | `{ type: "http", url: "...", headers: {...} }` |
| Env vars | `environment: { KEY: "val" }` | `env: { KEY: "val" }` | `env: { KEY: "val" }` (supports `$VAR` substitution) |
| Disable | `enabled: false` | Omit entry (or remove) | Omit entry |
| Config location | `opencode.json` `mcp` block | `~/.claude.json` `mcpServers` (user) or `.mcp.json` (project) | `~/.copilot/mcp-config.json` (user) or `.mcp.json` (project) |

**Effort: Low** (~20 lines per adapter for MCP). The YAML catalog is the canonical source; each adapter maps `{command, args, type, env}` to its CLI's key names.

---

### OpenCode Adapter (`cli/opencode/adapter.py`)

**Target:**
- `opencode.json` (agent block, MCP block, permission rules)
- `~/.config/opencode/plugins/` (TypeScript plugin files)
- `~/.config/opencode/commands/` (markdown command files)
- `~/.config/opencode/skills/` (SKILL.md + ROLE.md per agent)

**Translation logic:**

| Generic config → | OpenCode output | Notes |
|---|---|---|
| `mcp/*.yaml` → | `opencode.json` `mcp` block | `local` maps to `{type:"local", command: [cmd, ...args], environment: env}`, `http` maps to `{type:"remote", url, headers}` |
| `agent-system/roles/*/role.md` → | `opencode.json` `agent` block | `description` from first line, `prompt: {file:./skills/<name>/SKILL.md}`, `model` from agent config, `mode` from config |
| `agent-system/rules/` → | Inline in AGENTS.md + skill files | AGENTS.md is a generated document referencing generic rules |
| `agent-system/workflows/` → | `commands/delegate.md` + AGENTS.md | The DAG orchestration logic is opencode-specific (`task(subagent_type:)`) |
| Commands → | `commands/*.md` | Copied verbatim (already opencode-format) |
| Plugins → | `plugins/*.ts/.js` | Copied verbatim |

**The adapter is essentially a config generator** that:
1. Reads YAML files from `mcp/` and writes them into `opencode.json`'s `mcp` block
2. Reads role markdown from `agent-system/roles/` and generates the `agent` block referencing `{file:./skills/<name>/SKILL.md}`
3. Copies `cli/opencode/commands/`, `cli/opencode/plugins/`, `cli/opencode/skills/` verbatim

**Effort: Medium** (~150 lines Python). The bulk is scaffolding the opencode.json structure. Skills, commands, and plugins are copied as-is from `cli/opencode/` — they don't need transformation because they're already in opencode format.

---

### Claude CLI Adapter (`cli/claude/adapter.py`)

**Target files:**
- `~/.claude.json` — `mcpServers` block (user-scope MCP config)
  - **Risk**: `~/.claude.json` is auto-managed by Claude CLI. Anthropic advises against manual editing. Safer approach: generate `.mcp.json` (project-scope) or use `claude mcp add` CLI commands instead of writing the file directly.
- `~/.claude/agents/*.agent.md` — subagent definitions
- `~/.claude/CLAUDE.md` — global instructions
- `.claude/settings.json` — project-scope config (permissions, hooks)
- Project `CLAUDE.md` — per-project instructions

**Translation logic:**

| Generic config → | Claude CLI output | Format | Notes |
|---|---|---|---|
| `mcp/*.yaml` → | `.mcp.json` `mcpServers` block | JSON | Prefer `.mcp.json` over `~/.claude.json` to avoid corrupting auto-managed state |
| `agent-system/roles/planner/role.md` → | `~/.claude/agents/planner.agent.md` | YAML frontmatter + Markdown body | `tools:` from permission config, `model:` mapped to Claude model IDs (sonnet/opus/haiku), body = role.md content. **Limitation**: Claude subagents cannot spawn other subagents, so Planner→Coder DAG delegation isn't natively supported. |
| `agent-system/roles/coder/role.md` → | `~/.claude/agents/coder.agent.md` | Same | `disallowedTools` map from `permission: deny` |
| `agent-system/workflows/` → | `CLAUDE.md` (transformed) | Markdown | Workflow rules (session lifecycle, DAG) become instructions in CLAUDE.md. The `/delegate` DAG pattern needs rethinking — Claude has no `task()` tool, so multi-agent orchestration must be done manually via `@agent-name` mentions in CLAUDE.md. |
| `agent-system/rules/` → | `CLAUDE.md` + `.claude/rules/` | Markdown | Code principles, anti-patterns → `CLAUDE.md`. Path-scoped rules (e.g., `src/api/*` → `.claude/rules/api-conventions.md`) |
| Global config → | `.claude/settings.json` | JSON | `permissions`, `hooks` — direct mapping. `model` → `"primaryModel"`, shell → `"shell"` |

**Structural differences that impact adapter complexity:**

| OpenCode concept | Claude equivalent | Gap |
|---|---|---|
| `agent` block with `mode: all` (primary + subagent) | `*.agent.md` files | Claude uses separate files, not a JSON block. Semantically equivalent. |
| `permission: { edit: "deny", bash: "allow" }` | `disallowedTools: ["Write", "Edit"]`, `permissionMode: "default"` | Similar but different key names and granularity. OpenCode supports glob patterns in bash rules; Claude only allows `disallowedTools` list. |
| `task()` tool for subagent delegation | No equivalent | **BIG GAP**. Claude subagents cannot nest. The Planner→Coder→Reviewer DAG orchestration would need external coordination (a wrapper script that invokes `claude --agent planner ...`, then `claude --agent coder ...` sequentially, passing context). |
| `/delegate` slash command | No native DAG | Can be approximated with `CLAUDE.md` instructions + `@agent-name` mentions, but not enforced |
| `{file:./skills/...}` prompt references | Skills are auto-loaded by relevance | Different loading mechanism. Claude skills are loaded on-demand via `/skill-name` or when the model detects relevance. |

**Effort: Medium-High** (~250 lines Python + external orchestration script). MCP translation is straightforward. Agent translation is medium. The DAG orchestration gap is the hard part — needs either a wrapper/orchestrator script or accepting that Claude gets a simplified single-agent setup.

---

### Copilot CLI Adapter (`cli/copilot/adapter.py`)

**Target files:**
- `~/.copilot/mcp-config.json` — MCP server definitions (user-scope)
- `~/.copilot/agents/*.agent.md` — subagent definitions
- `~/.copilot/copilot-instructions.md` — personal global instructions
- `.github/copilot-instructions.md` — per-project instructions
- `.github/hooks/*.json` — lifecycle hooks

**Translation logic:**

| Generic config → | Copilot CLI output | Format | Notes |
|---|---|---|---|
| `mcp/*.yaml` → | `~/.copilot/mcp-config.json` | JSON | Direct mapping. Copilot requires `tools: "*"` allowlist on each server. |
| `agent-system/roles/planner/role.md` → | `~/.copilot/agents/planner.agent.md` | YAML frontmatter + Markdown body | `mcp-servers:` can be scoped to an agent. `model:` → Copilot ignores in CLI (only VS Code respects it). Tools allowlist via `tools:`. **Limitation**: prompt limit is 30,000 chars. |
| `agent-system/workflows/` → | `AGENTS.md` (primary) + `~/.copilot/copilot-instructions.md` | Markdown | Copilot reads `AGENTS.md` natively — so the workflow doc name matches. Multi-agent orchestration is model-driven (Copilot autonomously decides when to delegate), not DAG-based. No `/delegate` equivalent. |
| `agent-system/rules/` → | `AGENTS.md` + `.github/instructions/*.instructions.md` | Markdown | Path-specific rules via `applyTo` glob frontmatter. |
| Global config → | `~/.copilot/settings.json` | JSONC | Model, theme, permission defaults. |

**Key differences:**

| OpenCode concept | Copilot CLI equivalent | Gap |
|---|---|---|
| `agent` block | `agents/*.agent.md` | Same concept, different file format |
| `permission` granularity | `tools: ["read", "edit"]` allowlist | Less granular (no glob patterns for bash). Simpler but less powerful. |
| `task()` / `/delegate` DAG | Model-driven autonomous delegation | **No DAG support**. Copilot decides if/when to delegate. Cannot enforce Planner→Coder→Reviewer ordering. |
| `{file:./skills/...}` | `SKILL.md` auto-load by relevance | Similar concept, different loading mechanism |
| Plugin system | Full plugin system (`copilot plugin`) | Both have plugin systems but incompatible APIs |
| CLI-specific commands | No custom slash commands | OpenCode's `/delegate`, `/caveman` have no Copilot equivalent |
| ACP (Agent Client Protocol) | **Available** | Copilot exposes ACP for external orchestration. Can build a wrapper that implements DAG logic externally, calling Copilot as a subprocess. |

**Effort: Medium-High** (~300 lines Python + optional ACP wrapper). MCP translation is easy. Agent translation is straightforward. The DAG gap is similar to Claude — needs external orchestration. Copilot has the advantage of ACP support for building that external orchestrator.

---

### Critical Finding: The DAG Orchestration Gap

The biggest challenge across all adapters is **multi-agent DAG orchestration**:

| Capability | OpenCode (native) | Claude CLI | Copilot CLI |
|---|---|---|---|
| Subagent spawning | `task()` tool | ❌ Not allowed | Model-driven (autonomous) |
| Sequential DAG | `/delegate` command | ❌ No native support | ❌ No native support |
| Context passing | Automatic via `@result` | ❌ Manual | ❌ Model-decided |
| Worktree isolation | Manual (git worktree) | `isolation: worktree` field | ❌ No built-in |
| External orchestration | N/A (native) | Shell wrapper needed | ACP protocol available |

**Three approaches to bridge the gap:**

| Approach | Works for | Effort | Reliability |
|----------|-----------|--------|-------------|
| **A. Simplified single-agent config** — Claude/Copilot get MCPs + role instructions but no multi-agent orchestration. The agent role (planner/coder/reviewer) is selected at CLI launch time via `claude --agent planner`. | Claude, Copilot | Low | High (no orchestration = no orchestration bugs) |
| **B. Shell wrapper orchestration** — A script `bin/opencode-delegate` that runs `claude --agent planner "..."` then `claude --agent coder "..."` passing context files between steps. | Claude | Medium | Medium (context passing via files, no feedback loop) |
| **C. ACP-based orchestrator** — A Python/Node daemon implementing DAG logic, driving Copilot via ACP protocol. | Copilot | High | High (ACP is designed for this) |

**Recommendation for v1:** Approach A (simplified single-agent) for both Claude and Copilot. Ship the DAG orchestration as an optional add-on per CLI, not a blocker for the adapter architecture.

### What stays (already CLI-agnostic)
- `templates/shell/`, `templates/zed/`, `templates/ghostty/`, `templates/bruno/`
- Dev tool installation (rtk, glab, git-review-cli, opencode-session)
- `bootstrap.sh` entry point

### Risks / Limitations

- **Scope 1 (extract agent-system)**: Must carefully separate generic methodology from opencode-specific syntax (`{file:./skills/}`, `task(subagent_type:)`). Risk of over-abstracting — keep skill files pragmatic.
- **Scope 3 (opencode adapter)**: Adapter must produce output identical to current templates. Review by comparing generated opencode.json against the known-good version.
- **Scope 4 (installer refactor)**: The `--clean`, `--snapshot`, and `--verify` flags must remain functional across all code paths. Test each flag combination.
- **Backward compatibility**: Existing installations (already deployed `~/.config/opencode/`) must continue working. Only new installs see the new structure.
- **Claude adapter risks**: Writing to `~/.claude.json` is discouraged by Anthropic as it's auto-managed. Must use `.mcp.json` and `claude mcp add` CLI commands instead.
- **Copilot agent prompt limit**: 30,000 chars per agent profile. Long ROLE.md files may be truncated — need a strategy (summarize, split into instructions files).
- **Model mapping**: OpenCode uses `opencode-go/deepseek-v4-pro` while Claude uses `sonnet/opus/haiku` and Copilot uses `gpt-5.2` or its own model names. The adapter needs a model name translation table.
- **Multi-agent DAG is not portable**: The methodology (Planner→Coder→Reviewer→Tester) works natively only in OpenCode. For Claude/Copilot, it requires external orchestration (Approach A for simplicity, B/C for full fidelity).
