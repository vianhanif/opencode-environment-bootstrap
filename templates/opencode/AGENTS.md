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

| Session | Role | Purpose | When |
|---------|------|---------|------|
| 1 | Planner | Understand + document the task | Before any coding |
| 2 | Coder | Implement changes incrementally | After planning is complete |
| 3 | Reviewer | Validate correctness and risks | For complex changes |
| 4 | Tester | Execute test plans, verify behavior | After coding, or in test-fix cycles |
| 5 | Analyzer | Investigate issues, trace code, analyze logs | Bug/incident investigation |

```
Primary flow (ideal):
  Session 1 (Planner)  →  Session 2 (Coder)  →  Session 3 (Reviewer)
      Document              Implement              Validate

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

### Delegation Annotations (Multi-Agent Workflow)
Annotate tasks with role prefixes to delegate to role-specific subagents. The parent agent interprets these as a DAG, resolving dependencies and delegating in order.

| Annotation | Role | Delegates via |
|-----------|------|--------------------------------------|
| `@plan` | Planner | task(subagent_type: "plan") |
| `@code` | Coder | task(subagent_type: "code") |
| `@review` | Reviewer | task(subagent_type: "review") |
| `@test` | Tester | task(subagent_type: "test") |
| `@analyze` | Analyzer | task(subagent_type: "analyze") |

Each custom agent is defined in `opencode.json` with its own model, system prompt, and permission set. Tasks delegated via `@plan` and `@analyze` can also be invoked directly as primary agents via `/agent plan` or `/agent analyze`.

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
@plan implement go-task-orbit into core, replacing existing worker
@result @code make changes in branch refactor-worker
@result @review review the changes against main
```

Parallel + sequential:
```
@code fix payment timeout bug
@code add logging to notification service
@result @test verify both changes
```

Use the `/delegate` command to trigger this workflow.

### Branch Sources
- Default: `main` (or the project's default branch)
- Create feature branches from the default branch

### File Naming
Task docs: `{YYYYMMDD}-{ticket-id}-{title}.md` **(ENFORCED — all task docs must follow this format; date, ticket, and title separated by hyphens)**

### Changelogs
Task documentation lives in the `changelog/` folder (singular) in each service repository. Do NOT use `changelogs/` (plural).

---

## Model Selection

| Role | Recommended | Avoid |
|------|-------------|-------|
| **Planner** | Claude Opus, DeepSeek Reasoner, Kimi K2.5, GLM-5 | Fast models |
| **Coder** | Claude Sonnet, GPT-mini, MiniMax M2.7, MiMo-V2 | Overthinking |
| **Reviewer** | MiMo-V2-Omni, GPT mid-tier | None |

### Cost Target
~80% usage should be Coder models

Track periodically via session logs to review session counts by model.

### OpenCode Go LLM Tiers
- **Fast** (simple/bulk tasks): MiniMax M2.5, MiniMax M2.7
- **Mid-tier** (moderate coding): MiMo-V2-Omni, MiMo-V2-Pro
- **Advanced** (complex architecture): Kimi K2.5, GLM-5

| LLM | Best For |
|-----|----------|
| GLM-5 | Best quality |
| Kimi K2.5 | Best reasoning/architecture |
| MiniMax M2.7 | Best value |
| MiniMax M2.5 | Cheapest bulk/refactor |
| MiMo-V2-Omni | Balanced alternative |

### MiniMax Known Issue & Workaround

MiniMax M2.5/M2.7 has a recurring JSON serialization bug in tool calls:
- Numbers passed as strings (`"7300"` instead of `7300`)
- Arrays/objects passed as JSON-encoded strings (`"[{...}]"` instead of `[{...}]`)

**Mitigations:**
1. **Plugin** (`minimax-tool-fix.ts` in `~/.config/opencode/plugins/`) auto-fixes tool args before execution — silently handles the common cases above
2. **If a tool call fails** with `SchemaError` — retry; the model will often self-correct on the second attempt
3. **For complex tool chains** (multi-step with many args) — switch to MiMo-V2-Omni or Claude Sonnet which don't have this issue

---

## Read First
- `PLANNER-role.md` - Full workflow rules
- `CODER-role.md` - Implementation rules + 10 coding principles
- `REVIEWER-role.md` - Review checklist
- `TESTER-role.md` - Testing guidelines

---

## Anti-Patterns (MUST AVOID)

- [ ] Jump into coding without full context
- [ ] Generate large, unreviewable code blocks
- [ ] Assume missing requirements
- [ ] Perform hidden refactors
- [ ] Mix planning and coding in one session
- [ ] No coding without task documentation
- [ ] No mixed sessions (plan + code in one turn)
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
On first use in a project directory, run Serena onboarding to index the codebase:
- The agent should call `serena_check_onboarding_performed` at session start
- If not yet onboarded, call `serena_onboarding` and follow the instructions
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

The Skill files are in: `~/.config/opencode/skills`

Available skills:
- `planner` - Load for planning sessions
- `coder` - Load for coding sessions
- `reviewer` - Load for review sessions
- `tester` - Load for testing guidance
- `analyzer` - Load for production issue investigation and root cause analysis

# opencode-handoff — Session Handoff
<!-- handoff -->

When context grows long or noisy, use `/handoff <goal>` instead of writing a manual restart summary. This plugin:
- Analyzes full conversation history to extract key decisions, file references, and remaining work
- Opens a new session with an editable draft prompt containing `@file` refs for context
- Provides a `read_session` tool in the new session to fetch full transcripts if needed

**When to use:** Context Management trigger (long/inconsistent/noisy) → use `/handoff` instead of manual restart summary.

**After handoff:** Load relevant skill (planner/coder/reviewer/tester/analyzer) in the new session to continue.

**Example:**
```
/handoff continue implementing the user auth feature from this session
```

<!-- /handoff -->

# lean-ctx — Context Engineering Layer
<!-- lean-ctx-rules-v10 -->

## Mode Selection
- Editing the file? → `full` first, then `diff` for re-reads
- Context only? → `map` or `signatures`
- Large file? → `aggressive` or `entropy`
- Specific lines? → `lines:N-M`
- Unsure? → `auto`

Anti-pattern: NEVER use `full` for files you won't edit — use `map` or `signatures`.

## File Editing
Use native Edit/Write/StrReplace — unchanged. lean-ctx replaces READ only.
If Edit requires Read and Read is unavailable, use `ctx_edit(path, old_string, new_string)`.
NEVER loop on Edit failures — switch to ctx_edit immediately.

Fallback only if a lean-ctx tool is unavailable: use native equivalents.
<!-- /lean-ctx -->
