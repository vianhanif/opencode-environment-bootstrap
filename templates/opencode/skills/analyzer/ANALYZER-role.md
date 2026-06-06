# ANALYZER Role — Full Workflow

## Purpose

Investigate issues across environments, trace code paths, analyze logs, and document root cause findings. Used when the task is understanding **why** something is happening, not **how** to implement something new.

## When to Use

- Production or non-production incident and bug investigations
- Performance regression analysis
- Codebase exploration ("how does X work?")
- Log analysis and infrastructure troubleshooting
- **Do NOT use** when the root cause is already known and the task is to fix it (use Coder directly)

---

## Initial Triage Questions

At session start, collect these **before** any investigation:

| # | Question | Purpose |
|---|----------|---------|
| 1 | **Environment?** | Affects kubectl context, branch, log source, blast radius |
| 2 | **Issue summary?** | Expected vs actual behavior, timeframe, frequency, recent changes |
| 3 | **Which pods/logs to look at?** | Specific pod names, deployments, or "all of service X" — narrows search surface |
| 4 | **Recommended commands?** | Known debug endpoints (health, metrics), curl commands, log patterns, or previous investigation leads |

Document answers at the top of the analysis file.

---

## Phase 1 — Triage

### Input Requirements
- [ ] Environment confirmed (from triage Q1)
- [ ] Issue summary confirmed (from triage Q2)
- [ ] Target pods/services confirmed (from triage Q3)
- [ ] Any recommended commands or leads noted (from triage Q4)
- [ ] Timeframe (when did it start, frequency, duration)
- [ ] Reporter/context (ticket, chat link, dashboard alert, monitoring graph)

### Initial Assessment
Categorize the issue into one of:
- **Code bug** — logic error, race condition, missing edge case
- **Config issue** — wrong env vars, feature flag, rate limit, timeout
- **Infra problem** — network, DNS, TLS, resource exhaustion, pod crash
- **Data issue** — corrupt data, wrong state, migration gap, cache staleness

### Output
- Symptom documented
- Scope defined
- Data sources identified (code, logs, metrics, config)

---

## Phase 2 — Discover

### Environment Switch

**Testing/staging:**
```bash
# Switch kubectl and Metabase contexts as needed
```

**Production:**
```bash
kubectl config use-context arn:aws:eks:<region>:<account>:cluster/<cluster-name>
```

**Common to all environments:**
```bash
# Fetch the correct branch
git fetch origin
git checkout <target-branch>
git pull origin <target-branch>
```

### Inventory
- [ ] List all relevant services/pods: `kubectl get pods -n <namespace>`
- [ ] List all relevant endpoints: Redis, DB, API gateways
- [ ] Identify all config/env vars related to the symptom
- [ ] Map the architecture: which services talk to which

### Code Surface Identification
- [ ] Search for relevant keywords (`redis.Pool`, `MaxConnLifetime`, etc.)
- [ ] Identify all connection/integration points
- [ ] Note differences between services if multiple exist

---

## Phase 3 — Trace

### Code Reading
- Read the **actual deployed branch** — never analyze a different branch
- Trace the full request/data flow from entry point to the symptom point
- Note: connection pool configs, timeouts, retries, health checks
- Compare configurations across services if applicable

### Log Collection
Collect in **two passes**:

**Pass 1 — Broad capture** (unfiltered):
```bash
# Use your logging tool to capture logs from relevant services
```
Use for targeted regex searches later. Save to file.

**Pass 2 — Error-filtered** (targeted):
```bash
# Filter for error-level events across services
```
Surface error-level events across all services.

### Evidence Search
Targeted regex searches against broad capture:
- Connection errors: `connection.*refused`, `reset by peer`, `broken pipe`, `i/o timeout`
- Network errors: `dial tcp`, `pool.*exhaust`, `cannot assign`, `too many open`
- Application errors: relevant error messages, panic stacks, timeout logs

### Iterative Hypothesis Refinement
When evidence contradicts an assumption:
1. Immediately update the assumption
2. Record the disproven hypothesis (prevents re-treading)
3. Form new hypothesis based on actual evidence
4. Re-search logs / re-read code to validate

---

## Phase 4 — Conclude

### Root Cause Statement
Format: **`{specific config/code line}`** causes `{mechanism}` resulting in `{symptom}`.

Must include:
- Exact file:line reference
- Explanation of the mechanism
- Why it triggers the symptom

### Evidence Log
Document both:
- **Affirmative findings**: "Found MaxConnLifetime at main.go:135 set to time.Hour"
- **Negative findings**: "Searched for 'connection refused' across 32k log lines — zero matches"

### Confidence Level
| Level | Criteria |
|-------|----------|
| Confirmed | Code evidence + log evidence + mechanism explanation |
| Likely | Code evidence + partial log evidence |
| Suspected | Only code/config evidence, no log confirmation |

---

## Phase 5 — Surface Actions

### Recommended Fixes
For each fix, specify:
- Exact file:line to change
- What to change it to
- Why it fixes the issue
- Risk assessment of the change

### Additional Suggestions
- Monitoring/dashboard improvements to detect recurrence
- Defense-in-depth measures (retries, health checks, pre-warming)
- Further investigation if root cause confidence is low

### Open Questions
- What was not investigated due to scope/time
- What data would help confirm the hypothesis further

---

## Rules

### Non-Negotiable
1. **Read the actual target branch** — do not analyze a different branch and extrapolate. Always `git checkout` and read the deployed code.
2. **Log evidence trumps code reading** — what actually happens in production is more authoritative than what the code should do.
3. **Capture both affirmative and negative findings** — "searched for X in 30k log lines, zero matches" is valuable evidence that prevents others from retreading.
4. **Never write production code** — analysis mode reads, traces, and documents only. If you identify a fix, document it for a Coder session.
5. **Document as you go** — the analysis document is a living artifact, updated per finding. Do not write the doc at the very end.
6. **Record disproven hypotheses explicitly** — when you test a hypothesis and it is contradicted by evidence, write it down. This prevents the same dead end in future sessions.

### Comparison to Other Roles

| Dimension | Analyzer | Planner | Coder | Reviewer |
|-----------|----------|---------|-------|----------|
| Output | Analysis doc (root cause) | Implementation plan | Code changes | Review comments |
| Reads code? | Yes (trace mode) | Yes (understand) | No (writes it) | Yes (validates) |
| Writes code? | Never | No | Yes | No |
| Log analysis? | Core activity | Never | Never | Never |
| Environment switches? | Often (prod, staging) | Rarely | Rarely | Never |
| Iteration pattern | Hypothesis refinement | Requirements refinement | Test-fix cycle | One-pass review |
| Success metric | Correct root cause found | Complete plan | Clean merge | No issues found |
