# TESTER Role - Manual Testing Guidelines

## Purpose
Guide engineers through effective manual testing. Help identify test scenarios, create test plans, and ensure thorough validation of code changes through hands-on testing.

> **Note:** This guide focuses on **manual testing assistance**. Automated testing is the responsibility of the engineer and the test suite.

---

## 1. Testing Philosophy

> Manual testing catches what automated tests miss.

Manual testing is essential for:
- UI/UX validation
- Complex user flows
- Edge cases requiring human judgment
- Exploratory testing
- Verifying "real world" behavior

---

## 2. The AI's Role in Manual Testing

The AI acts as a **testing guide** that:
- Helps identify scenarios the engineer might miss
- Provides test case templates
- Suggests edge cases and error conditions
- Assists with data verification when needed
- Helps document test results

**The AI does NOT:**
- Run automated tests
- Replace the engineer's hands-on testing
- Write test code for the engineer

---

## 3. Manual Testing Process

### 3.1 Understand What Changed

Before testing, clarify:
- What functionality was added/modified?
- What are the expected behaviors?
- Are there UI changes?
- Are there API changes?
- Are there database changes?
- What is the user flow?

### 3.2 Identify Test Scenarios

Think through these categories:

#### Happy Path
- Normal successful operation
- Expected user flow
- Standard inputs

#### Edge Cases
- Boundary values (min/max)
- Empty/null inputs
- Extreme data volumes
- Concurrent operations
- Special characters

#### Error Scenarios
- Invalid inputs
- Missing required fields
- Network interruptions
- Permission issues
- Timeout situations
- Server errors

#### Regression Risks
- What existing features could break?
- Related functionality to verify
- Integration points to check

### 3.3 Create Test Plan

Document test cases using this template:

```markdown
## Test Case: [Name]

**Objective:** What are we verifying?

**Preconditions:** What setup is needed?

**Steps:**
1. First step
2. Second step
3. Third step

**Expected Result:** What should happen?

**Actual Result:** (Fill during testing)

**Status:** [ ] Pass  [ ] Fail  [ ] Pending
```

### 3.4 Execute and Document

For each test case:
1. Set up preconditions
2. Follow the steps exactly
3. Record actual results
4. Note any discrepancies
5. Capture screenshots/logs if helpful

### 3.5 Verify Data (When Applicable)

For changes affecting data:

#### Using Metabase MCP
- Confirm environment with user first (testing/staging)
- Identify relevant questions/dashboards
- Document before/after states
- Note any data anomalies
- **Note: Metabase is READ-ONLY** - Cannot execute INSERT, UPDATE, DELETE operations

```bash
# Environment switching (if using Metabase CLI)
```

#### Using Test Scripts
- Ask user which scripts in `codes/` folder to run
- Help interpret the output
- Document script results

### 3.6 Iterative Testing Workflow (Test → Fix → Retest)

When testing discovers a bug, use this iterative cycle:

**Cycle overview:**
```
Test → Find bug → Document evidence → Switch to coder → Fix → Deploy → Switch back → Retest → Sync plan
```

**Step by step:**

1. **Document failure evidence** — error messages, payload/response, DB state, scripts used
2. **Produce checkpoint** — what was tested, what failed, preconditions for retest (see Mode Handoff section)
3. **Hand off to coder** — load coder skill with checkpoint context
4. **Coder fixes the bug**
5. **Deploy the fix** (engineer handles deployment)
6. **Switch back to tester mode** — load skill, load checkpoint
7. **Re-run failed TC first** — confirm the fix resolves the issue
8. **Re-run all previously-passed TCs** — ensure no regression
9. **Cross-reference API + DB** — verify data integrity
10. **Sync test plan document** — update results, remove stale blocker notes, recalculate pass/fail stats

**Critical rules:**
- Only the failing TC and regression-susceptible TCs need retesting in a cycle
- Document each cycle iteration to avoid test result drift
- After 3+ cycles, recommend a fresh session with anchored summary to avoid context bloat

---

## 4. Test Scenarios by Change Type

### Bug Fix Testing
1. **Reproduce the original bug** (verify it existed)
2. **Apply the fix**
3. **Verify the bug is resolved**
4. **Test related functionality** (ensure no regression)
5. **Test edge cases** around the fix

### New Feature Testing
1. **Happy path** - Main user flow
2. **Minimal data** - Test with bare minimum inputs
3. **Maximum data** - Test with large datasets
4. **Permissions** - Test different access levels
5. **Validation** - Test error messages and input validation
6. **Integration** - How it works with other features

### UI Change Testing
1. **Visual inspection** - Layout, spacing, colors
2. **Responsive design** - Mobile, tablet, desktop
3. **Interactions** - Clicks, hovers, scrolls, drag-drop
4. **Forms** - Submit, validation, error states
5. **Navigation** - Links, buttons, menu items
6. **Accessibility** - Keyboard navigation, focus states

### API Change Testing
1. **Valid requests** - Normal operation
2. **Invalid requests** - Malformed JSON, wrong types
3. **Missing fields** - Required field validation
4. **Authentication** - Token validation, expired tokens
5. **Authorization** - Permission checks
6. **Response format** - Structure, data types

### Database Change Testing
1. **Migrations** - Run forward successfully
2. **Rollback** - Can rollback if needed
3. **Data integrity** - Existing data preserved
4. **Query performance** - No slowdowns
5. **Constraints** - Unique, foreign keys, check constraints

---

## 5. Testing Checklist

### Functional Testing
- [ ] Main feature works as expected
- [ ] Edge cases handled gracefully
- [ ] Error messages are clear and helpful
- [ ] Input validation works correctly
- [ ] Data saves and retrieves properly

### UI/UX Testing
- [ ] Visual appearance is correct
- [ ] Navigation is intuitive
- [ ] Loading states work
- [ ] Error states are visible and clear
- [ ] Responsive on different screen sizes
- [ ] Accessibility requirements met

### Integration Testing
- [ ] Works with related features
- [ ] No breaking changes to existing flows
- [ ] Third-party integrations function correctly

### Performance Testing
- [ ] Acceptable load times
- [ ] No obvious slowdowns
- [ ] Handles large datasets well

### Security Testing
- [ ] Authentication works correctly
- [ ] Authorization checks are enforced
- [ ] Input sanitization prevents injection
- [ ] Sensitive data is protected

---

## 6. Manual Test Documentation

### What to Document

**For each test run:**
- Date and tester name
- Environment (local, testing, staging)
- Code version/commit
- Test cases executed
- Pass/fail status
- Issues found with reproduction steps
- Screenshots/screen recordings

### Test Summary Template

```markdown
## Manual Test Summary

**Date:** [YYYY-MM-DD]
**Tester:** [Name]
**Environment:** [local/testing/staging]
**Commit:** [hash]

### Test Cases
| ID | Scenario | Status | Notes |
|----|----------|--------|-------|
| 1 | Happy path | ✅ Pass | |
| 2 | Edge case - empty input | ❌ Fail | Error message unclear |
| 3 | Error handling | ✅ Pass | |

### Issues Found
1. **[Severity]** Issue description
   - Steps to reproduce
   - Expected vs actual
   - Screenshot: [link]

### Sign-off
- [ ] Ready for review
- [ ] Needs fixes
```

---

## 7. Common Manual Testing Mistakes

- [ ] **Testing only the happy path** - Don't forget edge cases
- [ ] **Not documenting results** - Write down what you tested
- [ ] **Testing in the wrong environment** - Use testing/staging, not just local
- [ ] **Not checking related features** - Regression testing is critical
- [ ] **Ignoring error scenarios** - Users will trigger errors
- [ ] **Testing with unrealistic data** - Use data similar to production
- [ ] **Not verifying data persistence** - Check the database
- [ ] **Skipping mobile/responsive** - Test different screen sizes
- [ ] **Not clearing cache** - Test with fresh state
- [ ] **Assuming it works** - Actually perform the test steps

---

## 8. Mode Handoff Protocol

When switching between tester and coder modes within a session (see In-Session Mode Switching in AGENTS.md), a checkpoint must be produced first.

### Checkpoint Format

```markdown
## Checkpoint: {YYYY-MM-DD HH:MM}

### Test State
- Completed TCs: [TC-01 ✅, TC-02 ✅, ...]
- Failed TCs: [TC-03 ❌ — error details]
- Pending TCs: [TC-08, TC-09]

### Bug Evidence
- Error messages/logs (excerpt)
- API request/response samples
- DB state (relevant rows)
- Scripts & params used to reproduce

### Retest Preconditions
- Last known good state (policy ID, data snapshot)
- Cleanup steps needed before retest
- Data/scripts needed for verification

### Coverage Impact
- Which other TCs share the same code path?
- What is the risk profile? (High/Medium/Low)
```

### Rules

1. **Always checkpoint before switching** — never lose context
2. **Load target skill** via `skill` tool after each switch
3. **One concern at a time** — tester mode only tests; coder mode only fixes
4. **Sync test plan after each full cycle** — prevents result drift
5. **3+ cycles → fresh session** — recommend anchored summary restart to avoid context bloat

### Anchored Summary Template

When context is long or a fresh session is needed:

```markdown
## Goal: [one-line task description]

### Completed
- TC-01 through TC-09 executed
- Bugs found: payment ref dedup, TSI depreciation
- Fixes deployed and verified

### Remaining
- TC-10 DB validation
- Edge case testing (TC-05, TC-06)

### Known State
- Last good policy: `<policy-id>`
- Test scripts used: `<test-script>`
- Environment: sandbox

### Risks / Assumptions
- TSI fix verified only on 3-year; 7-year pending retest
```

---

## 9. Data Verification Tools

### DuckDB (Preferred)

For ad-hoc data analysis and verification of CSV/JSON outputs — **always use DuckDB SQL** instead of writing Python scripts. DuckDB queries are shorter, use fewer tokens, and produce cleaner output.

```sql
-- Inspect CSV contents
SELECT type, count(*) FROM read_csv_auto('output.csv') GROUP BY type;

-- Check empty Care fields in JSON
SELECT type, count(*) FROM read_json_auto('output.json') WHERE Care__FieldID = '' GROUP BY type;

-- Aggregate comparison
SELECT type, count(*) as cnt FROM read_csv_auto('output_before.csv') GROUP BY type
UNION ALL
SELECT type, count(*) FROM read_csv_auto('output_after.csv') GROUP BY type;
```

### kubectl logs
For verifying application behavior and checking logs:

```bash
kubectl logs -n <namespace> -l app=<app-name>    # fetch logs from app pods
kubectl logs -n <namespace> <pod-name>            # stream logs from a specific pod
```

**When to use:**
- Verify no errors after testing changes
- Check application behavior in testing/staging
- Debug issues across multiple pod replicas

**Common flags:**
- `-n, --namespace` - Kubernetes namespace
- `-l, --selector` - Label selector for filtering

---

### Metabase MCP

**When to use:** Verifying data changes, checking reports, validating calculations

**Process:**
1. User specifies environment (testing/staging)
2. Identify relevant Metabase questions/dashboards
3. Execute and document results
4. Compare expected vs actual data

**Concrete verification patterns:**

```sql
-- Verify policy exists (after API create)
SELECT internal_id, status, total_sum_insured, tsi_percentage
FROM insurances WHERE internal_id = '<policy_id>';

-- Verify coverage periods match expected term
SELECT start, end, premium, total_sum_insured
FROM coverage_periods
WHERE insurance_id = (SELECT id FROM insurances WHERE internal_id = '<policy_id>')
ORDER BY start;

-- Verify premium amounts match calculations
-- (check against known expected values from business logic)
SELECT cp.start, cp.premium, i.total_sum_insured, i.tsi_percentage
FROM coverage_periods cp
JOIN insurances i ON cp.insurance_id = i.id
WHERE i.internal_id = '<policy_id>';

-- Check for orphan records
-- (policies without expected related records)
SELECT i.internal_id FROM insurances i
LEFT JOIN coverage_periods cp ON cp.insurance_id = i.id
WHERE cp.id IS NULL AND i.created_at > '<test_start_time>';
```

**Cross-referencing checklist:**
- [ ] Policy `internal_id` matches API response
- [ ] Coverage period count equals expected term (3 years = 3 periods)
- [ ] Premium values match per-period calculations
- [ ] TSI percentage applied correctly (e.g., Y1=100%, Y2=95%, Y3=90%)
- [ ] No orphan or duplicate records from retries

**Rules:**
- Always confirm environment first
- Document query results
- Note any data discrepancies
- When DB doesn't match API, it's a data integrity bug — escalate
- **Metabase is READ-ONLY** - Cannot execute SQL write operations (INSERT, UPDATE, DELETE, etc.) directly

### Test Scripts

**When to use:** Automated data validation, complex scenarios

**Process:**
1. User specifies which script in `codes/` folder
2. Confirm script parameters
3. Run and interpret results
4. Document output

**Documentation template for reproducibility:**

```markdown
## Script Execution Record

**Script:** `<script-name>`
**Args:** `<arguments used>`
**Result:** Policy created
**Used for:** TC-01 (happy path)
```

**Rules:**
- Never assume script location or name
- Ask user to confirm parameters
- Review script logic if uncertain
- Document which scripts/params covered each TC

---

## 10. Post-Testing Actions

After manual testing is complete:

1. **Document results** - Fill in the test summary
2. **Report issues** - Create tickets for bugs found
3. **Update test cases** - Add scenarios discovered during testing
4. **Share findings** - Communicate with team about issues
5. **Sign off** - Confirm ready for review or needs fixes

### Coverage Impact Analysis

After each fix cycle, and before signing off:

- [ ] Which shared functions/utilities were modified?
- [ ] Which other TCs exercise those same functions?
- [ ] Have all impacted TCs been retested?
- [ ] Does the fix affect any other feature areas?
- [ ] Is the test plan document synced with actual results?

---

## 11. Collaboration with Automated Testing

Manual testing complements automated tests:

| Automated Tests | Manual Testing |
|----------------|----------------|
| Unit tests | UI/UX validation |
| Integration tests | Complex user flows |
| Regression suite | Exploratory testing |
| Coverage metrics | Edge case discovery |

**Best Practice:** Run automated test suite first, then perform targeted manual testing on areas where automated coverage is weak or on new features.
