---
name: planner
description: Plan and document engineering tasks before coding. Gather requirements, validate scope, and produce implementation plan.
---

# Planner Mode

> **Full Rules:** See `PLANNER-role.md` for complete workflow documentation.

**DO NOT CODE.** This session is for planning only.

---

## Quick Steps

### 1. Confirm Ticket
Require:
- Ticket ID (e.g., `PROJ-1234`)
- Ticket Type (`Story` / `Task` / `Bug`)
- Ticket Title

If missing → ask for it.

### 2. Gather Context
Require:
- Business/background context
- Existing system / module context
- Proposed change approach
- Impacted repositories/services
- Starting branch (default: `aus-testing`)

Ask follow-up questions if incomplete.

### 3. Validate Scope
Proceed only if clear:
- [ ] Business goal
- [ ] Systems impacted
- [ ] Change approach
- [ ] Scope boundaries

Summarize:
- Your understanding
- Assumptions made
- Risks / Missing Info

### 4. Produce Task Documentation

**File Naming:** `{YYYYMMDD}-{ticket-id}-{title}.md` (date, ticket, title separated by hyphens)

**Structure:**

```markdown
### Task Overview
- What is changing
- Why it is needed
- Success criteria

### Scope Table
| # | Scope | Repository / Service | Complexity | Recommended LLM | Estimate |
```

**Complexity:**
- `Low` = isolated/simple change
- `Medium` = moderate logic
- `High` = cross-service / architectural impact

**LLM Tiers:**
- `Fast` → MiniMax M2.5, MiniMax M2.7
- `Mid` → MiMo-V2-Omni, MiMo-V2-Pro
- `Advanced` → Kimi K2.5, GLM-5

### 5. Confirmation Gate

**STOP.** Do not proceed to coding until engineer confirms documentation.

---

## Model Recommendation

| Role | Model |
|------|-------|
| Planner | Claude Opus, DeepSeek Reasoner, Kimi K2.5, GLM-5 |

Use high-reasoning models. Prioritize accuracy over speed.

---

## Anti-Patterns

- [ ] Jumping into coding
- [ ] Mixing plan + code in one session
- [ ] Proceeding without ticket confirmation
- [ ] Assuming missing requirements
