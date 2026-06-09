# Agent System Overview — opencode-environment-bootstrap

This document describes the custom agent system and `/delegate` command configured in `templates/opencode/`.

## The `/delegate` Command

A custom opencode command that orchestrates multi-agent workflows via annotated task delegation.

### Pre-Delegation Validation

Before any subagents are launched, `/delegate` enforces 4 explicit confirmations using the `question` tool (never auto-evaluates). These values become **shared context** injected into every subagent's task prompt, including the computed `WORKTREE_PATH`:

| # | Item | Question |
|---|------|----------|
| 1 | **Git Repository** | "Are you running this from within a git repository? If yes, what is the repo path?" |
| 2 | **Git Remote Origin** | "What is the git remote origin URL for this work?" |
| 3 | **Target Branch** | "Which base branch should the work target? (e.g. `main`, `aus-testing`, `develop`)" |
| 4 | **Ticket ID & Summary** | "What is the ticket ID and a short summary? (e.g. PROJ-1234: short description)" |

These values become **shared context** injected into every subagent's task prompt.

### Annotations & Delegation

| Annotation | Delegates To | Description |
|-----------|-------------|-------------|
| `@planner` | `task(subagent_type: "planner")` | Plan and document before coding |
| `@coder` | `task(subagent_type: "coder")` | Implement code changes |
| `@reviewer` | `task(subagent_type: "reviewer")` | Review diffs and MRs |
| `@tester` | `task(subagent_type: "tester")` | Manual testing and test planning |
| `@analyzer` | `task(subagent_type: "analyzer")` | Investigate issues and trace code paths |

### Dependency Chaining

- `@result` before a role → depends on ALL preceding annotated tasks since the last `@result`
- Without `@result` → root task, no dependency — runs immediately
- Tasks in the same dependency tier with no inter-dependency **may run in parallel**

### Execution Flow

```
Validate → Parse annotations → Build DAG → Execute roots → Collect results → Inject into dependents → Report
```

---

## Custom Agents

Six agents total: five delegation agents and one standalone knowledge agent. Each references a `SKILL.md` file as its system prompt.

### Delegation Agents (`mode: "all"`)

These participate in `/delegate` DAG orchestration and can be invoked directly via `/agent <name>`. All five have `mode: "all"`.

### Overriding Agent Models

Each agent's model is set via an env var, with a default baked into `opencode.json` at install time:

| Agent | Env Var | Default |
|-------|---------|---------|
| **Planner** | `$MODEL_PLANNER` | `opencode-go/deepseek-v4-pro` |
| **Coder** | `$MODEL_CODER` | `opencode-go/deepseek-v4-flash` |
| **Reviewer** | `$MODEL_REVIEWER` | `opencode-go/deepseek-v4-pro` |
| **Tester** | `$MODEL_TESTER` | `opencode-go/deepseek-v4-flash` |
| **Analyzer** | `$MODEL_ANALYZER` | `opencode-go/deepseek-v4-pro` |
| **Brain** | `$MODEL_BRAIN` | `opencode-go/deepseek-v4-pro` |

**To override**, set the env var in `~/.zsh/exports.local.zsh` (never overwritten by bootstrap):

```zsh
# ~/.zsh/exports.local.zsh
export MODEL_PLANNER="anthropic/claude-sonnet-4-20250514"
export MODEL_CODER="opencode-go/deepseek-v4-flash"
```

Then re-run bootstrap to bake new values into `opencode.json`:

```bash
source ~/.zshrc
curl -fsSL https://github.com/vianhanif/opencode-environment-bootstrap/raw/main/bootstrap.sh | \
  bash -s -- --config /path/to/local-config.json
```

### Planner (`@planner`)

**Purpose:** Understand and document tasks before any coding.

**Enforcements:**
1. **Git & Context** — Confirm repo, remote, target branch, ticket ID & summary (all via `question` tool, never auto-evaluated)
2. **Create Worktree** — Creates `.worktrees/{ticket-id}-{short-desc}/` via `git worktree add`, confirms with user, stores `WORKTREE_PATH` in task doc
3. **Scope Table** — Each scope item must define its own `Target Branch` for downstream delegation
4. **3-Round Validation Loop** — After producing the doc, enforce minimum 3 rounds of Q&A:
   ```
   Round 1 → Update doc → Present for review
   Round 2 → Update doc → Present for review
   Round 3 → Update doc → Present for review
   ```
5. **Final Confirmation Gate** — Do not proceed until engineer confirms the final doc

**Model:** deepseek v4 pro

### Coder (`@coder`)

**Purpose:** Implement code changes incrementally per task documentation.

**Enforcements:**
   1. **Confirm/Reuse Worktree** — Detects `WORKTREE_PATH` from task doc or shared context, confirms with user; creates one if missing
   2. **Plan-First Rule** — If no planned doc/scope provided → STOP and enforce asking to use `@planner` first
   3. **Commit & Push** to targeted remote

**Model:** deepseek v4 flash

### Reviewer (`@reviewer`)

**Purpose:** Review diffs for correctness, risks, and consistency.

**Enforcements:**
1. **Confirm MR** — Explicitly ask for MR number/URL and verify remote
2. **Confirm Branches** — Source and target branch via `question`
3. **No Worktree** — Does NOT create or use a worktree; all review context comes from MR via `git-review-cli`
4. **Post to MR** — Via `git-review-cli` or `glab`

**Model:** deepseek v4 pro

### Tester (`@tester`)

**Purpose:** Assist with manual testing scenarios and test planning.

**Enforcements:**
1. **Conditional Worktree** — Creates/reuses worktree only if creating new test code; skips for existing test execution
2. **Document Test Results** — Record findings, then suggest switching to planner/coder mode to fix discovered bugs

### Analyzer (`@analyzer`)

**Purpose:** Investigate issues, trace code paths, analyze logs.

**Enforcements:**
1. **Document Root Cause** — Record findings and recommended actions, then suggest switching to planner/coder mode to implement fixes

**Model:** deepseek v4 pro

### Brain (`@brain`) — Standalone Knowledge Agent

**Purpose:** Enforce serena project setup, audit and validate repository memories, and strengthen system knowledge through multi-round Q&A — the repo's institutional memory.

**Invoke:** `/agent brain` only. `mode: "primary"` — not available via `/delegate`.

**Enforcements:**
1. **Main Branch Only** — Rejects feature/bugfix WIP branches. Must run from the confirmed main/default branch. Branch name is never hardcoded — always asked at session start.
2. **Phase 1 — Safety Check** — Validate `.serena/` exists, is NOT gitignored, is tracked by git, pushed to remote, has no uncommitted changes, and `onboard_project` has been run. Produces a shareability verdict before proceeding.
3. **Create Worktree** — Creates `.worktrees/brain-{YYYYMMDD}/` via `git worktree add -b`, confirms with user
4. **Phase 2 — Memory Audit** — Read all project-scoped memories and evaluate against an 8-section completeness checklist (architecture, key symbols, API contracts, data model, configuration, conventions, decision records, dependencies).
5. **Phase 3 — 3-Round Validation** — Multi-round Q&A to surface gaps, clarify assumptions, and strengthen memories with serena's `write_memory`/`edit_memory` tools. Minimum 3 rounds before final gate.
6. **Source Code Safety** — `edit: deny, write: deny` — cannot touch source files. Uses serena memory tools exclusively.

**Model:** deepseek v4 pro

---

## Example Workflow

### Full Lifecycle

```
/delegate
@planner design auth system migration for PROJ-1237
@result @coder implement auth changes
@coder implement billing changes
@result @reviewer review both
@result @tester run integration tests
```

### Parallel + Sequential

```
/delegate
@coder fix payment timeout bug for PROJ-1235
@coder add logging to notification service for PROJ-1236
@result @tester verify both changes
```

---

## File Layout

```
templates/opencode/
├── opencode.json              # Agent & MCP definitions
├── AGENTS.md                  # Agent workflow rules, session structure, commit formats
├── commands/
│   ├── delegate.md            # /delegate command definition
│   ├── caveman.md             # Quick commit/review helper
│   └── ...
├── plugins/
│   ├── delegate-placeholders.tsx  # TUI placeholders for /delegate

│   └── caveman/                   # Caveman workflow plugin
└── skills/
    ├── planner/
    │   ├── SKILL.md               # Planner agent system prompt
    │   └── PLANNER-role.md        # Full workflow rules (ticket confirmation, branching, coding standards)
    ├── coder/
    │   ├── SKILL.md               # Coder agent system prompt
    │   └── CODER-role.md          # Implementation rules (pre-coding, change strategy, 10 principles)
    ├── reviewer/
    │   ├── SKILL.md               # Reviewer agent system prompt
    │   └── REVIEWER-role.md       # Code review rules (checklist, output format, constraints)
    ├── tester/
    │   ├── SKILL.md               # Tester agent system prompt
    │   └── TESTER-role.md         # Manual testing guidelines (scenarios, checklist, handoff protocol)
    ├── analyzer/
    │   ├── SKILL.md               # Analyzer agent system prompt
    │   └── ANALYZER-role.md       # Investigation workflow (triage, discover, trace, conclude)
    └── brain/
        ├── SKILL.md               # Brain agent system prompt (standalone, serena knowledge)
        └── BRAIN-role.md          # Progressive understanding rules (session journal, maturity levels, memory quality)
```
