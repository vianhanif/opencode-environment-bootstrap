# 9Router Integration: Evaluation & Implementation Plan

## Task Overview

Evaluate and plan integration of [9Router](https://github.com/decolua/9router) — an AI proxy/router — into the `opencode-environment-bootstrap` project to enable dynamic agent model routing with 3-tier fallback, built-in RTK compression, and multi-provider support.

### What Is Changing

- **opencode.json** — Add 9Router as a custom provider via `@ai-sdk/openai-compatible`, optionally switch agent `model` fields
- **installer.py** — Add optional 9Router installation (`ensure_9router()`)
- **AGENTS.md** — Document 9Router as a local tool
- **AGENT-SYSTEM.md** — Document routing layer
- **plugins/rtk.ts** — Resolve overlap with 9Router's built-in RTK

### Why It Is Needed

- **Zero downtime**: Auto-fallback when quota exhausted or rate-limited
- **Cost optimization**: Route cheap tasks to free/cheap tiers, premium tasks to subscription
- **Provider flexibility**: 60+ providers through one endpoint
- **Token savings**: 9Router has RTK built-in (20-40% compression)

### Success Criteria

1. 9Router provider entry exists in `opencode.json` (disabled by default)
2. Installer can optionally install 9Router via npm
3. Documentation covers setup, config, and RTK interaction
4. No breaking changes to existing configuration
5. Users can opt in by: enabling provider → installing 9Router → setting models

---

## Scope Table

| # | Scope | Target Branch | Repository / Service | Complexity | Estimate |
|---|-------|---------------|---------------------|------------|----------|
| 1 | Phase 0: Research & Validation | `feature/20260609-9router-evaluation` | opencode-environment-bootstrap | Low | 1h |
| 2 | Phase 1: Template changes | `feature/20260609-9router-evaluation` | opencode-environment-bootstrap | Low | 2h |
| 2a | `opencode.json` — add 9Router provider block | same | templates/opencode/ | Low | 30m |
| 2b | `AGENTS.md` — add 9Router to Local Tools | same | templates/opencode/ | Low | 15m |
| 2c | `AGENT-SYSTEM.md` — document routing layer | same | repo root | Low | 15m |
| 2d | agent model overrides (optional/commented) | same | templates/opencode/opencode.json | Low | 15m |
| 3 | Phase 2: Installer changes | `feature/20260609-9router-evaluation` | opencode-environment-bootstrap | Medium | 2h |
| 3a | `ensure_9router()` function | same | installer.py | Low | 30m |
| 3b | Update CLEAN_PATHS, verify list | same | installer.py | Low | 15m |
| 3c | Add `INSTALL_9ROUTER` config variable | same | installer.py | Low | 15m |
| 3d | Interactive prompt for optional install | same | installer.py | Low | 30m |
| 4 | Phase 3: RTK overlap resolution | `feature/20260609-9router-evaluation` | opencode-environment-bootstrap | Medium | 1h |
| 5 | Phase 4: Post-install helper command | `feature/20260609-9router-evaluation` | opencode-environment-bootstrap | Low | 30m |
| 6 | Release prep & testing | `feature/20260609-9router-evaluation` | opencode-environment-bootstrap | Low | 1h |

---

## Detailed Plan

### Phase 0: Research & Validation

Before coding, resolve these unknowns:

1. **Model name format**: Run 9Router locally, call `GET /v1/models`, confirm exact model ID strings. Test that `9router/cc/claude-opus-4-7` works as OpenCode agent `model` value
2. **API key requirement**: Confirm whether 9Router requires an `apiKey` header for local requests, or accepts a dummy value
3. **RTK interaction**: Test both `plugins/rtk.ts` and 9Router active simultaneously — check for double-compression or errors
4. **Provider model limits**: Capture `limit.context` and `limit.output` values for each model

### Phase 1: Template Changes

#### 1a. `templates/opencode/opencode.json`

Add disabled-by-default 9Router provider:

```json
"9router": {
  "enabled": false,
  "npm": "@ai-sdk/openai-compatible",
  "name": "9Router AI Proxy",
  "options": {
    "baseURL": "http://localhost:20128/v1",
    "apiKey": "{env:9ROUTER_API_KEY}"
  },
  "models": {
    "cc/claude-opus-4-7": {
      "name": "Claude Opus 4-7 (via 9Router)",
      "limit": { "context": 200000, "output": 65536 }
    },
    "cc/kimi-k2": {
      "name": "Kimi K2 (via 9Router)",
      "limit": { "context": 128000, "output": 32768 }
    },
    "free/kiro": {
      "name": "Kiro Free (via 9Router)",
      "limit": { "context": 128000, "output": 16384 }
    }
  }
}
```

Add commented agent model overrides in the `agent` sections:

```jsonc
// 9Router variant (enable above + uncomment to use):
// "model": "9router/cc/claude-opus-4-7",
```

#### 1b. `templates/opencode/AGENTS.md`

Add 9Router to "Local Tools" section with install instructions, setup steps, and RTK note.

#### 1c. `AGENT-SYSTEM.md`

Add routing architecture section under the Agent System Overview, noting the 3-tier fallback and configuration path.

### Phase 2: Installer Changes

#### 2a. `ensure_9router()` function

Pattern follows `ensure_rtk()` exactly:

```python
def ensure_9router(vars, dry_run=False):
    if shutil.which("9router"):
        return
    step("Dev tool: 9router (AI Proxy Router)")
    if not shutil.which("npm"):
        warn("npm not found — skipping. Install Node.js first.")
        return
    if dry_run:
        info("[dry-run] Would run: npm install -g 9router")
        return
    try:
        run(["npm", "install", "-g", "9router"])
        info("9router installed globally")
    except subprocess.CalledProcessError:
        warn("9router install failed. Retry: npm install -g 9router")
```

#### 2b. Update data structures

- Add `Path.home() / ".local" / "bin" / "9router"` to `CLEAN_PATHS`
- Add `"9router"` to `_verify_binary` check list
- Add `"INSTALL_9ROUTER": os.environ.get("INSTALL_9ROUTER", "false")` to defaults

#### 2c. Interactive prompt

Add `ensure_9router()` call in main phase 4 (dev tools section), guarded by `INSTALL_9ROUTER` variable.

### Phase 3: RTK Overlap Resolution

**Option A (Recommended): Keep both, document overlap**

- 9Router has RTK built-in and always-on
- `plugins/rtk.ts` adds a second layer of compression
- Document that if using 9Router, `rtk.ts` can be disabled by commenting it out
- Add comment in `opencode.json`:
  ```jsonc
  "plugin": [
    // "rtk.ts",  // 9Router has built-in RTK — disable if using 9Router
  ]
  ```

### Phase 4: Post-Install Helper

Create `templates/opencode/commands/9router.md`:

```markdown
---
description: Check 9Router status and quick-start guide
---

Checks if 9Router is running and provides help.

- Check status: `curl -s http://localhost:20128/v1/models`
- Open dashboard: open http://localhost:20128/dashboard
- Docs: https://github.com/decolua/9router
```

---

## Branch Naming

`feature/20260609-9router-evaluation` — single branch for all phases.

---

## Commit Format

```
{type}: {short description}

- Key change 1
- Key change 2
```

---

## MR Requirements

- Summary of changes
- Link to this plan doc: `changelog/20260609-9router-evaluation-plan.md`
- Testing notes (model name validation, installer dry-run, existing config preserved)
- Risks / limitations (9Router must be running; RTK overlap; new dependency)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| 9Router model names don't match OpenCode format | Config broken | Validate before merging; test with live 9Router |
| Double RTK compression | Token waste or errors | Document; add opt-out comment on `rtk.ts` |
| 9Router port conflict | Agent downtime | Document port change procedure |
| Existing users unaffected | None | Provider is disabled by default; no breaking changes |
