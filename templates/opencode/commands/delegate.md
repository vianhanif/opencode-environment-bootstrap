---
description: Delegate annotated tasks to role-specific subagents with dependency chaining
---

Parse the multi-line annotated prompt and execute as a role-delegation workflow.

## Pre-Delegation Validation

Before building the task graph, **explicitly ask the user to confirm** each of the following using the `question` tool. Do NOT auto-evaluate or run git commands to check — always ask.

### 1. Git Repository
- Use `question` to ask: "Are you running this from within a git repository? If yes, what is the repo path?"
- Do NOT auto-run `git rev-parse` — ask explicitly

### 2. Git Remote Origin
- Use `question` to ask: "What is the git remote origin URL for this work?"
- Do NOT auto-run `git remote get-url origin` — ask explicitly

### 3. Target Branch
- Use `question` to ask: "Which base branch should the work target? (e.g. `main`, `aus-testing`, `develop`)"
- Default: `main`
- Confirm explicitly before proceeding

### 4. Ticket ID & Summary
- Use `question` to ask: "What is the ticket ID and a short summary? (e.g. PROJ-1234: short description)"
- If the annotation text already contains both → confirm with user via question; if not → ask for them

### 5. Document Shared Context
Collect the confirmed values as **shared context** that will be passed to every subagent:

```
Git Repo Path: /path/to/repo
Git Remote Origin: git@github.com:org/repo.git
Target Branch: main
Ticket ID: PROJ-1234
Ticket Summary: short description
```

## Annotation Format

Each line is a task. Prefix with a role annotation and optional `@result` marker:

```
@planner <description>
@result @coder <description>
@result @reviewer <description>
```

| Annotation | Subagent Type | Delegates via |
|-----------|---------------|-------------|
| `@planner` | planner | task(subagent_type: "planner") |
| `@coder` | coder | task(subagent_type: "coder") |
| `@reviewer` | reviewer | task(subagent_type: "reviewer") |
| `@tester` | tester | task(subagent_type: "tester") |
| `@analyzer` | analyzer | task(subagent_type: "analyzer") |

Each custom agent is defined in `opencode.json` with its own model, system prompt, and permission set.

## Dependency Rules

- `@result` before a role = **depends on ALL preceding annotated tasks** since the last `@result` (or start of list)
- Without `@result` = **root task**, no dependency — can run immediately
- Tasks in the same dependency tier with no inter-dependency **may run in parallel**

## Inject Context into Subagent Tasks

When calling `task(subagent_type: "...")` for each annotated step, **inject the shared context** at the top of the prompt so every subagent has the confirmed values:

```markdown
## Shared Context (from delegate)
- Git Repo: {path}
- Remote Origin: {url}
- Target Branch: {branch}
- Ticket: {id} — {summary}
```

## Execution

1. **Validate** — run the Pre-Delegation Validation steps above
2. **Parse** — extract all `@annotations` and build the dependency graph
3. **Execute** — fire root tasks first via `task(subagent_type: "<type>")`, inject shared context into each prompt
4. **Collect** — gather upstream results, pass as context to dependent tasks
5. **Report** — progress per task, final summary

## Examples

Sequential three-step with explicit ticket:
```
@planner implement go-task-orbit into core, replacing existing worker for PROJ-1234
@result @coder make changes in branch refactor-worker
@result @reviewer review the changes against main
```

Parallel + sequential:
```
@coder fix payment timeout bug for PROJ-1235
@coder add logging to notification service for PROJ-1236
@result @tester verify both changes
```

Full lifecycle:
```
@planner design auth system migration for PROJ-1237
@result @coder implement auth changes
@coder implement billing changes
@result @reviewer review both
@result @tester run integration tests
```
