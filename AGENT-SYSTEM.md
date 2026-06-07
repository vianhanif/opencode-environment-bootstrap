# Agent System Overview — opencode-environment-bootstrap

This document describes the custom agent system and `/delegate` command configured in `templates/opencode/`.

## The `/delegate` Command

A custom opencode command that orchestrates multi-agent workflows via annotated task delegation.

### Pre-Delegation Validation

Before any subagents are launched, `/delegate` enforces 4 explicit confirmations using the `question` tool (never auto-evaluates):

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

### Planner (`@planner`)

**Purpose:** Understand and document tasks before any coding.

**Enforcements:**
1. **Git & Context** — Confirm repo, remote, target branch, ticket ID & summary (all via `question` tool, never auto-evaluated)
2. **Scope Table** — Each scope item must define its own `Target Branch` for downstream delegation
3. **3-Round Validation Loop** — After producing the doc, enforce minimum 3 rounds of Q&A:
   ```
   Round 1 → Update doc → Present for review
   Round 2 → Update doc → Present for review
   Round 3 → Update doc → Present for review
   ```
4. **Final Confirmation Gate** — Do not proceed until engineer confirms the final doc

**Model:** DeepSeek Reasoner / Kimi K2.5 (high-reasoning)

### Coder (`@coder`)

**Purpose:** Implement code changes incrementally per task documentation.

**Enforcements:**
1. **Plan-First Rule** — If no planned doc/scope provided → STOP and enforce asking to use `@planner` first
2. **Isolated Worktree** — `~/.opencode-worktree/coder/{branch-name}/`
3. **Commit & Push** to targeted remote
4. **Cleanup** — Remove worktree after push (user confirmed)

**Model:** Various tiers per complexity (MiniMax M2.7, MiMo-V2)

### Reviewer (`@reviewer`)

**Purpose:** Review diffs for correctness, risks, and consistency.

**Enforcements:**
1. **Confirm MR** — Explicitly ask for MR number/URL and verify remote
2. **Confirm Branches** — Source and target branch via `question`
3. **Isolated Worktree** — `~/.opencode-worktree/reviewer/{target}-to-{source}/`
4. **Post to MR** — Via `git-review-cli` or `glab`
5. **Cleanup** — Remove worktree after review posted

**Model:** MiMo-V2-Omni / GPT mid-tier

### Tester (`@tester`)

**Purpose:** Assist with manual testing scenarios and test planning.

**Enforcements:**
1. **Isolated Worktree** — `~/.opencode-worktree/tester/{branch-name}/`
2. **Push fixes** if discovered during testing
3. **Cleanup** — Remove worktree after testing complete

### Analyzer (`@analyzer`)

**Purpose:** Investigate issues, trace code paths, analyze logs.

**Enforcements:**
1. **Isolated Worktree** — `~/.opencode-worktree/analyzer/{branch-name}/`
2. **Push fixes** if discovered during analysis
3. **Cleanup** — Remove worktree after analysis complete

**Model:** DeepSeek Reasoner / Kimi K2.5 (high-reasoning)

### Brain (`@brain`) — Standalone Knowledge Agent

**Purpose:** Enforce serena project setup, audit and validate repository memories, and strengthen system knowledge through multi-round Q&A — the repo's institutional memory.

**Invoke:** `/agent brain` only. `mode: "primary"` — not available via `/delegate`.

**Enforcements:**
1. **Phase 1 — Safety Check** — Validate `.serena/` exists, is NOT gitignored, is tracked by git, pushed to remote, has no uncommitted changes, and `onboard_project` has been run. Produces a shareability verdict before proceeding.
2. **Phase 2 — Memory Audit** — Read all project-scoped memories and evaluate against an 8-section completeness checklist (architecture, key symbols, API contracts, data model, configuration, conventions, decision records, dependencies).
3. **Phase 3 — 3-Round Validation** — Multi-round Q&A to surface gaps, clarify assumptions, and strengthen memories with serena's `write_memory`/`edit_memory` tools. Minimum 3 rounds before final gate.
4. **Source Code Safety** — `edit: deny, write: deny` — cannot touch source files. Uses serena memory tools exclusively.

**Model:** DeepSeek Reasoner / Kimi K2.5

---

## Worktree Enforcement Summary

| Agent | Worktree Path | Cleanup Trigger |
|-------|--------------|----------------|
| `@coder` | `~/.opencode-worktree/coder/{branch-name}/` | After commit + push |
| `@tester` | `~/.opencode-worktree/tester/{branch-name}/` | After testing complete |
| `@analyzer` | `~/.opencode-worktree/analyzer/{branch-name}/` | After analysis complete |
| `@reviewer` | `~/.opencode-worktree/reviewer/{target}-to-{source}/` | After review posted to MR |
| `@brain` | `~/.opencode-worktree/brain/{target-branch}/` (protected branches only) | After commit + push or MR |

All enforcement steps use the `question` tool for explicit user confirmation — nothing is auto-evaluated.

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
├── AGENTS.md                  # Configuration instructions
├── commands/
│   ├── delegate.md            # /delegate command definition
│   ├── caveman.md             # Quick commit/review helper
│   └── ...
├── plugins/
│   ├── delegate-placeholders.tsx  # TUI placeholders for /delegate
│   ├── lean-ctx.ts                # Context compression plugin
│   └── caveman/                   # Caveman workflow plugin
└── skills/
    ├── planner/SKILL.md       # Planner agent system prompt
    ├── coder/SKILL.md         # Coder agent system prompt
    ├── reviewer/SKILL.md      # Reviewer agent system prompt
    ├── tester/SKILL.md        # Tester agent system prompt
    ├── analyzer/SKILL.md      # Analyzer agent system prompt
    └── brain/SKILL.md         # Brain agent system prompt (standalone)
```
