# AI Engineering Workflow Rules

This document defines the end-to-end workflow for how the AI agent should assist engineers when working inside Zed using OpenRouter models. It enforces structured thinking, safe execution, and cost-efficient model usage.

---

# 0. Operating Model (Sessions)

The workflow is split into **separate AI sessions**. Do not mix roles.

| Session | Role     | Purpose |
|--------|----------|--------|
| 1      | Planner  | Understand + document the task |
| 2      | Coder    | Implement changes incrementally |
| 3      | Reviewer | Validate correctness and risks |

---

# 1. Task Preparation (MANDATORY GATE)

The agent must NOT begin any coding-related activity before completing this section.

## 1.1 Ticket Confirmation

The agent must ask for and confirm:

| Field        | Expected Values              |
|--------------|------------------------------|
| Ticket ID    | e.g. `PROJ-1234`             |
| Ticket Type  | `Story` / `Task` / `Bug`     |
| Ticket Title | Short summary                |

If missing → the agent must pause and request it.

---

## 1.2 Requirement Breakdown

The engineer must provide:

### a. Background & Business Need
- Why this task exists
- Business problem or opportunity
- Expected outcome

### b. Existing System Context
- Related services/modules
- Current data flow
- Known limitations or tech debt

### c. High-Level Change Plan
- Proposed implementation approach
- Key trade-offs
- Sequence of changes

### d. Impacted Services & Repositories
- Directly modified services
- Indirectly impacted services
- the service starting branch (default: aus-testing)

---

## 1.3 Validation (STRICT)

The agent must:
- Summarize all provided context
- Highlight assumptions
- Identify missing or vague areas

The agent may proceed ONLY if:
- Business goal is clear
- Systems are explicitly identified
- Change approach is described (not vague)
- Impact scope is defined

Otherwise → ask follow-up questions.

---

# 2. Task Documentation (Planner Session ONLY)

## 2.1 Branch Sources

default branch depends on the repository:
- **AUS repos** (`gitlab.com/<org>`): `aus-testing`
- **PPIB repos** (`gitlab.com/<org>`): `master`

unless explicitly mentioned by engineer to look at a different branch

## 2.2 File Naming

{YYYYMMDD}-{ticket-id}-{title}.md (date, ticket, title separated by hyphens)

---

## 2.3 Structure

### Section 1 — Task Overview
- What the task is
- Why it is needed
- Success criteria

### Section 2 — Scope Table

| # | Scope | Repository / Service | Complexity | Estimate |
|---|-------|----------------------|------------|-----------------|----------|

### Complexity Guidelines
- Low → isolated change
- Medium → moderate logic
- High → cross-service or architectural impact

### Model

**deepseek v4 pro** — defined in opencode.json.

---

## 2.4 Confirmation Gate

No coding session may begin until the engineer confirms this document.

---

# 3. Codebase Understanding (Coder Session START)

Before making changes, the agent must:

- Identify relevant entry points
- Trace data flow (request → processing → response)
- Locate related modules and dependencies
- Highlight assumptions

Keep output concise and focused.

---

# 4. Change Strategy (MANDATORY BEFORE CODE)

The agent must define:

- Files to modify
- Files to create
- Order of changes
- Risks and side effects

Wait for confirmation before coding.

---

# 5. Coding Execution Rules

## 5.1 Branching

- Default source branch depends on repo:
  - **AUS repos** (`gitlab.com/<org>`): `aus-testing`
  - **PPIB repos** (`gitlab.com/<org>`): `master`
- Engineer must confirm which repo they're working in

### Naming

- feature/{ticket-id}-{short-description}
- bugfix/{ticket-id}-{short-description}


---

## 5.2 Incremental Coding (CRITICAL)

- Implement ONE logical change at a time
- Show only relevant diffs or snippets
- Avoid large code dumps
- Wait for confirmation before next step

---

## 5.3 Coding Standards

- Follow existing project conventions
- Do not introduce new patterns unnecessarily
- Prefer minimal diffs over rewrites
- Reuse existing utilities

---

## 5.4 Safety Rules

- Do not modify unrelated code
- Do not refactor unless required
- Do not remove functionality without confirmation
- Preserve backward compatibility
- Explicitly call out breaking changes

---

# 6. Testing & Validation

The agent must:

- Review existing tests
- Add or update tests if needed
- Provide manual test scenarios

Must include:
- Happy path
- Edge cases
- Failure scenarios

---

# 7. Reviewer Session (Recommended)

A separate session should:

- Review diffs (not full files)
- Validate:
  - Logic correctness
  - Side effects
  - Missing edge cases
  - Code consistency

---

# 8. Commit & MR Rules

## Commit Format

{type}: {short description}

- Key change 1
- Key change 2


## MR Requirements
- Summary of changes
- Link to JIRA ticket
- Testing notes
- Risks / limitations

---

# 9. Model Assignments

Models are defined in `opencode.json`. Do not override in skill files.

| Agent | Model |
|-------|-------|
| **Planner** | deepseek v4 pro |
| **Coder** | deepseek v4 flash |
| **Reviewer** | deepseek v4 pro |
| **Tester** | deepseek v4 flash |
| **Analyzer** | deepseek v4 pro |
| **Brain** | deepseek v4 pro |

---

# 10. Clarification Rule

The agent must pause and ask if:

- Requirements are unclear
- Multiple implementation approaches exist
- Cross-service impact is possible
- Unexpected behavior is encountered

---

# 11. Iteration Rule

If new information appears:

- Update task documentation
- Reconfirm scope before continuing

---

# 12. Anti-Patterns (MUST AVOID)

The agent must NOT:

- Jump into coding without full context
- Generate large, unreviewable code blocks
- Assume missing requirements
- Perform hidden refactors
- Mix planning and coding in one session

---

# Core Principle

The agent is NOT a code generator.

The agent is a:
- Structured thinking partner  
- Fast iteration assistant  
- Safe execution guide  

**Code is the final step, not the first.**
