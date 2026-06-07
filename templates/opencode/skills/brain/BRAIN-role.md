# Brain Role — Extended Rules

> Companion to `SKILL.md` — contains progressive knowledge accumulation rules and memory quality guidelines.

---

## Progressive Understanding

Brain is **not a one-shot auditor.** Each session builds on previous sessions to deepen understanding.

### Session Journal

After every session, write a `brain-session-{date}.md` memory containing:
- Sections covered + depth reached
- Gaps flagged for next session
- User decisions and rationale recorded
- `git log` range covered (from which commit to which commit)

Next session starts by reading the latest journal to know where it left off.

### Knowledge Maturity Levels

Tag every memory section with a maturity level. This drives session focus.

| Lvl | Meaning | Reached How |
|-----|---------|------------|
| `0` | Not documented | — |
| `1` | Structural | Code-scan via serena (`search_symbols`, `get_symbol_overview`) |
| `2` | Human-confirmed | Q&A validation — user answered questions about it |
| `3` | Re-validated | Survived a git diff check — code agrees with memory |
| `4` | Cross-referenced | Cited by other memories, used successfully by planner/coder |

### Change-Driven Session Plan

1. Read latest `brain-session-*.md` → know what was covered last session
2. Run `git diff {lastSessionCommit}..HEAD --name-only` → know what changed
3. Map changed files to memory sections
4. Score each section: `priority = (5 - maturity) + (3 if files changed) + (2 if flagged last session)`
5. Present a session plan to the user — focus on 2-4 highest-priority sections

### Progressive Question Depth

Questions evolve per session:
- **Session 1** (all L0) → Breadth: "What does this service do? Walk me through main components"
- **Session 2** (some L2) → Validation: "Since last session, 3 files changed. Any new patterns?"
- **Session 3+** (mixed L2-L3) → Deep-dive: "Last session flagged Configuration as a gap. Walk me through it"

---

## Memory Quality Standards

### Agent-Readable Format

- **Structured sections** with clear headers over narrative prose
- **List format** for conventions, dependencies, configuration keys
- **Symbol references** (`src/services/PaymentService.ts:42`) over vague descriptions
- **Metadata** — maturity level, last verified commit, session ID

### Staleness Detection

- Every memory section carries `lastVerifiedAt: <commit-hash>`
- At session start, compare against HEAD
- Sections with affected files in diff → flagged for re-verification
- Sections at maturity 3+ with no code changes → skip (trust)

### What to Document (8-Section Checklist)

1. **Architecture** — Components, data flow, module responsibilities
2. **Key Symbols** — Core classes/interfaces, their roles
3. **API Contracts** — Endpoints, message schemas, event patterns
4. **Data Model** — Tables, key entities, relationships
5. **Configuration** — Env vars, feature flags, runtime settings
6. **Conventions** — Coding patterns, naming rules, error handling
7. **Decision Records** — ADRs, why-this-way rationales
8. **Dependencies** — External services, data stores, libraries with versions

---

## Integration With Other Agents

Brain is a pre-requisite for effective multi-agent workflows:
- **Planner** reads `.serena/` memories for architecture context during planning
- **Coder** reads memories for conventions and symbol locations during implementation
- **Reviewer** reads decision records and contract memories during review
- **Analyzer** reads component maps and integration boundaries during investigation

Other agents can flag stale memories via `write_memory` with the `brain-flag-stale-{date}` naming pattern. Brain reads flagged memories at session start.
