# AGENTS.md

## Context
This is an AI engineering workflow configuration directory. Not a code project.

---

## Core Principle
Act as a structured engineering assistant, not a blind code generator.
**Code is the final step, not the first.**

---

## Key Conventions

### Sessions (Required)
Every development task uses **role-focused sessions**. Keep each session aligned to one goal; use skill switching within a session only for the test-fix cycle.

| Session | Role | Purpose (from opencode.json) | When |
|---------|------|-----------------------------|------|
| 1 | Planner | Understand and document tasks before any coding | Before any coding |
| 2 | Coder | Implement code changes incrementally per task documentation | After planning is complete |
| 3 | Reviewer | Review diffs for correctness, risks, and consistency | For complex changes |
| 4 | Tester | Execute test plans and verify behavior | After coding, or in test-fix cycles |
| 5 | Analyzer | Investigate issues, trace code paths, and analyze logs | Bug/incident investigation |
| B | Brain | Enforce serena setup, audit project memories, strengthen repo knowledge through Q&A | Repo onboarding / knowledge refresh |

```
Primary flow (ideal):
  Session B (Brain)  →  Session 1 (Planner)  →  Session 2 (Coder)  →  Session 3 (Reviewer)
      Onboard/Refresh       Document              Implement              Validate

  Brain is standalone (via /agent brain, not part of /delegate). Run once per repo
  or after major changes. Skips if .serena/ memories exist and are recent.

Test-fix cycle (same session, skill switching):
  Tester skill → find bug → Coder skill → fix → Tester skill → retest
```

#### In-Session Mode Switching (Test-Fix Cycle)
When testing discovers a bug, **tester and coder may switch within the same session** for rapid iteration. This is the only allowed case of in-session role mixing.

Rules:
1. **Always produce a checkpoint** before switching modes — see Tester SKILL.md for format
2. **Load the target skill** via the `skill` tool at each switch
3. **Do not mix concerns** — when in coder mode, fix only; when in tester mode, verify only
4. **Sync the test plan** after each fix cycle to prevent result drift

### Pre-Delegation Validation (`/delegate`)
Before any delegation, the `/delegate` command enforces — using **explicit `question` tool** (never auto-evaluates):
1. **Git repo is confirmed** — user is asked to confirm the repo path
2. **Git remote origin is confirmed** — user is asked to confirm the remote origin URL
3. **Target branch is confirmed** — user must specify the base branch
4. **Ticket ID & summary is confirmed** — e.g. `PROJ-1234: short description`

These values become **shared context** injected into every subagent's task prompt.

### Subagent Worktree Enforcement
Each execution agent enforces its own isolated worktree:

| Agent | Worktree Path | Cleanup Trigger |
|-------|--------------|----------------|
| `@coder` | `~/.opencode-worktree/coder/{repo}/{branch-name}/` | After commit + push |
| `@tester` | `~/.opencode-worktree/tester/{repo}/{branch-name}/` | After testing complete |
| `@analyzer` | `~/.opencode-worktree/analyzer/{repo}/{branch-name}/` | After analysis complete |
| `@reviewer` | `~/.opencode-worktree/reviewer/{repo}/{target}-to-{source}/` | After review posted to MR |
| `@brain` | `~/.opencode-worktree/brain/{repo}/{main-branch}/` (always, from `setup/brain-{date}`) | After commit + push or MR |

> `{repo}` is the repository folder name (e.g., `core`, `api`). This enables running multiple repo sessions in parallel under the same agent type — e.g., `~/.opencode-worktree/brain/core/main/` and `~/.opencode-worktree/brain/api/main/`.

### Delegation Annotations (Multi-Agent Workflow)
Annotate tasks with role prefixes to delegate to role-specific subagents. The parent agent interprets these as a DAG, resolving dependencies and delegating in order.

| Annotation | Role | Delegates via |
|-----------|------|--------------------------------------|
| `@planner` | Planner | task(subagent_type: "planner") |
| `@coder` | Coder | task(subagent_type: "coder") |
| `@reviewer` | Reviewer | task(subagent_type: "reviewer") |
| `@tester` | Tester | task(subagent_type: "tester") |
| `@analyzer` | Analyzer | task(subagent_type: "analyzer") |

Each custom agent is defined in `opencode.json` with its own model, system prompt, and permission set. All five agents (`@planner`, `@coder`, `@reviewer`, `@tester`, `@analyzer`) have `mode: "all"` so they can be used both as primary agents (via `/agent <name>`) and as subagents (via delegation).

**`@brain` is `mode: "primary"`** — invoke directly via `/agent brain` for serena memory setup, audit, and knowledge strengthening. Not available as a delegation target.

**Dependency rules:**
- `@result` before a role = depends on ALL preceding annotated tasks since the last `@result`
- Without `@result` = root task, no dependency

**Execution:**
1. Parent parses all `@annotations` → builds dependency graph
2. Executes root tasks first via `task(subagent_type: "<role>")` — each agent gets its own model, prompt, permissions, and clean session context
3. For each dependent tier: collects upstream results, injects as context, delegates
4. Tracks progress via `todowrite`

**Examples:**

Sequential three-step:
```
@planner implement go-task-orbit into core, replacing existing worker
@result @coder make changes in branch refactor-worker
@result @reviewer review the changes against main
```

Parallel + sequential:
```
@coder fix payment timeout bug
@coder add logging to notification service
@result @tester verify both changes
```

Use the `/delegate` command to trigger this workflow.

### Branch Sources & Confirmation

- Source and target branches are **always confirmed at session start** via the `question` tool — never auto-detected or assumed
- Each agent enforces its own branch rules: `@coder`/`@tester`/`@analyzer` ask for target branch, `@brain` enforces main branch only
- Feature branch naming: `feature/{ticket-id}-{short-description}`
- Bugfix branch naming: `bugfix/{ticket-id}-{short-description}`

### File Naming
Task docs: `{YYYYMMDD}-{ticket-id}-{title}.md` **(ENFORCED — all task docs must follow this format; date, ticket, and title separated by hyphens)**

### Changelogs
Task documentation lives in the `changelog/` folder (singular) in each service repository. Do NOT use `changelogs/` (plural).

---

## Model Selection

Models are defined in `opencode.json` per agent. Do not override in SKILL.md.

| Agent | Model |
|-------|-------|
| **Planner** | deepseek v4 pro |
| **Coder** | deepseek v4 flash |
| **Reviewer** | deepseek v4 pro |
| **Tester** | deepseek v4 flash |
| **Analyzer** | deepseek v4 pro |
| **Brain** | deepseek v4 pro

---

## Read First

Each role has a dedicated doc covering its lifecycle, rules, and outputs:

| Doc | Sections | Role |
|-----|----------|------|
| `PLANNER-role.md` | Ticket Confirmation → Requirement Breakdown → Validation → Branch Sources → File Naming → Structure → Confirmation Gate → Branching → Incremental Coding → Coding Standards → Safety Rules → Commit Format → MR Requirements | Planner |
| `CODER-role.md` | Purpose → Activation → Pre-Coding Requirements → Change Strategy → Coding Execution → 10 Coding Principles → Testing & Validation → Model → General Rules → Context Management | Coder |
| `REVIEWER-role.md` | Purpose → Activation → Pre-Review Requirements → Review Checklist → Output Format → Enhanced Checks → Constraints → Model → Post-Review | Reviewer |
| `TESTER-role.md` | Purpose → Testing Philosophy → AI Role → Manual Testing Process → Test Scenarios by Change Type → Checklist → Documentation → Common Mistakes → Mode Handoff Protocol → Data Verification Tools → Post-Testing → Automated Testing Collab | Tester |
| `ANALYZER-role.md` | Purpose → When to Use → Initial Triage → Phase 1 Triage → Phase 2 Discover → Phase 3 Trace → Phase 4 Conclude → Phase 5 Surface Actions → Rules | Analyzer |
| `BRAIN-role.md` | Progressive Understanding (Session Journal, Maturity Levels, Change-Driven Plans, Progressive Questions) → Memory Quality Standards (Format, Staleness, 8-Section Checklist) → Agent Integration | Brain |

---

## Anti-Patterns (MUST AVOID)

- [ ] Jump into coding without full context
- [ ] Generate large, unreviewable code blocks
- [ ] Assume missing requirements
- [ ] Perform hidden refactors
- [ ] Mix planning and coding in one session
- [ ] No coding without task documentation
- [ ] No large code dumps (show diffs/snippets only)
- [ ] Modify test scripts to fix a validation bug — fix the source layer; test scripts are diagnostic tools, not the fix target
- [ ] Present neutral test results when expected behavior is violated — explicitly flag it as a bug with severity

---

## General Behavior

- Do not assume missing requirements
- Ask clarifying questions when requirements are unclear or incomplete
- Highlight assumptions before proceeding when context is uncertain
- Reconfirm scope if new information changes the task

### Before Starting on a New Project
If a codebase indexing MCP (e.g., Serena) is configured, run onboarding on first use:
- Call the indexing tool at session start
- This enables symbol-level code operations (find_symbol, rename, etc.)

---

## Safety Rules

- Do not modify unrelated code
- Do not refactor unless required by the task
- Do not remove functionality without confirmation
- Preserve backward compatibility unless explicitly approved otherwise
- Explicitly call out breaking changes / side effects

---

## Implementation Standards

- Follow existing project conventions and architecture
- Reuse existing utilities/patterns before introducing new ones
- Prefer minimal diffs over broad rewrites
- Keep changes scoped to the requested task only

---

## Workflow Discipline

- Work incrementally in logical steps
- Implement one logical change at a time unless instructed otherwise
- Keep output concise and focused on relevant diffs/snippets

---

## Testing

- Review existing tests before adding new ones
- Add/update tests when behavior changes require coverage
- Provide manual test scenarios when relevant

### Reviewer — Test Execution
- **Do NOT run tests locally if CI pipeline is green.** Trust CI, focus on static analysis.
- Only run tests locally when CI is unavailable or results are ambiguous.

---

## Branch Defaults

- Assume starting branch is the project's default branch unless specified otherwise
- Feature branch naming: `feature/{ticket-id}-{short-description}`
- Bugfix branch naming: `bugfix/{ticket-id}-{short-description}`

---

## Context Management

If conversation context becomes long, inconsistent, or noisy:
- Recommend starting a fresh session
- Provide restart summary including:
  - Ticket / Task
  - Confirmed Scope
  - Completed Work
  - Remaining Steps
  - Risks / Assumptions

---

## Commit & MR Rules

### Commit Format
```
{type}: {short description}

- Key change 1
- Key change 2
```

### MR Requirements
- Summary of changes
- Link to JIRA ticket
- Testing notes
- Risks / limitations

**MR Description Template:**
```
## Summary
<brief description of changes>

## JIRA
<JIRA ticket URL>

## Testing
<how to test, test results, manual scenarios>

## Risks / Limitations
<any risks, breaking changes, or known limitations>
```

---

## Context7 MCP Usage

<!-- context7 -->
Use Context7 MCP to fetch current documentation whenever the user asks about a library, framework, SDK, API, CLI tool, or cloud service -- even well-known ones like React, Next.js, Prisma, Express, Tailwind, Django, or Spring Boot. This includes API syntax, configuration, version migration, library-specific debugging, setup instructions, and CLI tool usage. Use even when you think you know the answer -- your training data may not reflect recent changes. Prefer this over web search for library docs.

**Do not use for:** refactoring, writing scripts from scratch, debugging business logic, code review, or general programming concepts.

### Steps

1. Always start with `resolve-library-id` using the library name and the user's question, unless the user provides an exact library ID in `/org/project` format
2. Pick the best match (ID format: `/org/project`) by: exact name match, description relevance, code snippet count, source reputation (High/Medium preferred), and benchmark score (higher is better). If results don't look right, try alternate names or queries (e.g., "next.js" not "nextjs", or rephrase the question). Use version-specific IDs when the user mentions a version
3. `query-docs` with the selected library ID and the user's full question (not single words)
4. Answer using the fetched docs
<!-- context7 -->

## Skill Files Location

Skill files are in: `~/.config/opencode/skills`

Available skills:
- `planner` - Load for planning sessions
- `coder` - Load for coding sessions
- `reviewer` - Load for review sessions
- `tester` - Load for testing guidance
- `analyzer` - Load for production issue investigation and root cause analysis
- `brain` - Load for serena memory setup, audit, and knowledge strengthening

## Local Tools

The following tools are installed by `opencode-environment-bootstrap`. The AI agent should use them when relevant.

### glab — GitLab CLI
Primary interface for GitLab merge requests and project management.

```bash
glab mr view <id>              # View MR details
glab mr diff <id>              # View MR diff
glab mr note <id> -m "review"  # Post a comment on MR
glab api <endpoint>            # Direct API access
```

### git-review-cli — MR Review Tool
Automates MR diff fetching, local checkout, and review posting.

```bash
git-review-cli https://gitlab.com/org/project/-/merge_requests/123
git-review-cli https://gitlab.com/org/project/-/merge_requests/123 --caveman   # Quick review
git-review-cli https://gitlab.com/org/project/-/merge_requests/123 --deep      # Deep review
git-review-cli <MR_ID>                    # Shorthand (current repo)
git-review-cli <ID> --post /tmp/review.md # Post a review file
```

**Prerequisite:** Authenticate glab first (`glab auth login` or set `GITLAB_TOKEN`).

### opencode-session — Session Viewer
View and search OpenCode session history from the local SQLite database.

```bash
opencode-session              # List recent sessions
opencode-session ses_xxx      # View session details
opencode-session -s 'text'    # Search session content
```

Can be used inside OpenCode TUI as: `!opencode-session ses_xxx` or `!opencode-session -s 'text'`

### multilogs — Kubernetes Log Aggregation
Aggregate logs from multiple Kubernetes pods across services.

```bash
multilogs -s 10m -o <app1> <app2>     # Fetch last 10 min to file
multilogs <app-name>                   # Stream logs from all pods
multilogs -h                           # Show help
```

**Gotcha:** When called from a non-interactive shell (e.g., via `bash` tool), prepend `source ~/.zshrc`:
```bash
source ~/.zshrc && multilogs -s 10m -o core-api core-worker
```

### pod-app-list — List Kubernetes Apps
Lists all unique `app` labels from running pods.

```bash
pod-app-list   # Returns sorted, deduplicated app names
```

---

# lean-ctx — Context Engineering Layer
<!-- lean-ctx-rules-v11 -->

## Tool Mapping (MANDATORY — use instead of native equivalents)
| Instead of | Use | Example |
|------------|-----|---------|
| Read/cat/head/tail | `ctx_read(path, mode)` | `ctx_read("src/main.rs", "full")` |
| Grep/rg/find | `ctx_search(pattern, path)` | `ctx_search("fn handle", "src/")` |
| Shell/bash (single command) | `ctx_shell(command)` | `ctx_shell("cargo test")` |
| Shell scripts (multi-statement, variable assignments) | `bash` | worktree creation, cleanup scripts |
| Edit (when Read unavailable) | `ctx_edit(path, old, new)` | `ctx_edit("f.rs", "old", "new")` |

## ctx_read Mode Selection
| Goal | Mode | When |
|------|------|------|
| Edit this file | `full` | Before any edit |
| Understand API | `signatures` | Context-only, won't edit |
| Re-read after edit | `diff` | Post-edit verification |
| Large file overview | `map` | >500 lines, won't edit |
| Specific region | `lines:N-M` | Know exact location |

## Workflow (follow this order)
1. **Orient:** `ctx_overview(task)` or `ctx_compose(task, path)` for unfamiliar tasks
2. **Locate:** `ctx_search(pattern, path)` for exact text; `ctx_semantic_search(query)` for concepts
3. **Read:** `ctx_read(path, mode)` with appropriate mode from table above
4. **Edit:** `ctx_edit(path, old_string, new_string)` or native Edit if available
5. **Verify:** `ctx_read(path, "diff")` + `ctx_shell("test command")`
6. **Record:** `ctx_knowledge(action="remember", content="...")` for non-obvious findings

## Session
- **Start:** `ctx_session(action="status")` + `ctx_knowledge(action="wakeup")`
- **End:** `ctx_session(action="decision", content="what was done + next steps")`
- **On [CHECKPOINT]:** `ctx_session(action="task", value="current status")`

NEVER use native Read/Grep/Shell when ctx_* equivalents are available.
<!-- /lean-ctx -->
