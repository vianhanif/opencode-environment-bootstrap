# opencode-environment-bootstrap

One-shot bootstrap for an opinionated AI engineering environment. Installs and configures [OpenCode](https://opencode.ai) with role-based multi-agent workflow, shell tooling, and editor/terminal/API-client config in a single run.

## Why

Setting up a new machine for AI-assisted development involves the same tedious steps every time:

1. Install opencode CLI
2. Configure MCP servers, agents, skills, and commands
3. Write workflow rules (session structure, test-fix cycles, delegation annotations)
4. Set up shell aliases and environment exports
5. Configure your editor (Zed), terminal (Ghostty), and API client (Bruno)
6. Remember what you're missing and go back

This project codifies that setup into a single, repeatable, version-controlled package. Run it once on a fresh machine and you get the same environment. Re-run it later to sync updates.

## What you get

| Layer | What | Files |
|-------|------|-------|
| **OpenCode** | 6 custom agents with isolated worktrees and enforcement workflows, `/delegate` orchestrator command for multi-agent DAGs, standalone `@brain` agent for repo knowledge management, session workflow rules, caveman commands, MCP servers (context7, duckdb, firecrawl, lean-ctx, mermaid, metabase, sequential-thinking, serena), plugins (lean-ctx, caveman, delegate-placeholders) | `~/.config/opencode/` |
| **Shell** | Zsh aliases (git, docker, general, pod-app-list), functions (multilogs), environment exports template, lazy-loaders, kubectl completions | `~/.zsh/` |
| **Dev tools** | lean-ctx, glab (GitLab CLI), git-review-cli, opencode-session, kubectl-multi-logs, Bruno collections | Installed by default — skip with `--skip-tools` |
| **Zed** | Vim keybindings, LSP config, lean-ctx context rules | `~/.config/zed/` |
| **Ghostty** | Terminal config (Dracula theme, word-navigation keybinds) | `~/.config/ghostty/` |
| **Bruno** | API client preferences (dark theme, SSL verification off) | `~/Library/Application Support/Bruno/` |

### Agent System — Multi-Agent Workflow with Enforcement

The `/delegate` command orchestrates 5 agents as an annotated DAG — write one message and let subagents execute in dependency order with full context sharing. A 6th agent, `@brain`, runs standalone for repo knowledge bootstrapping.

| Agent | Role | Enforces |
|-------|------|----------|
| `@planner` | Document tasks before coding | Git context, 3-round validation loop, per-scope target branches |
| `@coder` | Implement changes per spec | Plan-first rule, isolated worktree (`~/.opencode-worktree/coder/{repo}/`), commit/push, cleanup |
| `@reviewer` | Validate diffs for correctness | MR confirmation, isolated worktree, post review to MR, cleanup |
| `@tester` | Plan and execute tests | Isolated worktree, document results, suggest mode switch to planner/coder for fixes, cleanup |
| `@analyzer` | Investigate issues and logs | Isolated worktree, document root cause, suggest mode switch to planner/coder for fixes, cleanup |

**Standalone agent** — invoked directly, not via `/delegate`:

| Agent | Role | Enforces |
|-------|------|----------|
| `@brain` | Serena-based repo knowledge manager | Main branch only, isolated worktree, 3-round Q&A validation, `.serena/` safety checks |

**All enforcement steps use the `question` tool** — the AI asks, you confirm. Nothing is auto-evaluated. Every execution agent works in its own `git worktree` so your working directory stays clean.

```bash
# Example — three agents, one /delegate command
/delegate
@planner design auth migration for PROJ-1237
@result @coder implement auth changes
@result @reviewer review the changes
```

See [AGENT-SYSTEM.md](AGENT-SYSTEM.md) for the full breakdown.

The templates are generic — no hardcoded usernames, API keys, or organization-specific URLs. You supply those at install time or add them afterward.

## Usage

One-liner (auto-cleanup, no clone left behind):

```bash
curl -fsSL https://github.com/vianhanif/opencode-environment-bootstrap/raw/main/bootstrap.sh | \
  bash -s -- --config /path/to/local-config.json
```

With inline env vars instead of a config file:

```bash
CONTEXT7_API_KEY=ctx7sk-... FIRECRAWL_API_KEY=fc-... \
  curl -fsSL https://github.com/vianhanif/opencode-environment-bootstrap/raw/main/bootstrap.sh | bash
```

Or clone and run directly:

```bash
git clone https://github.com/vianhanif/opencode-environment-bootstrap.git
cd opencode-environment-bootstrap
python3 installer.py --config my-config.json
```

### Snapshot → Clean → Redeploy

Back up custom files, wipe everything, then reinstall — all via `curl | bash`:

```bash
# 1. Snapshot — save your custom dotfiles and app configs before wiping
curl -fsSL https://github.com/vianhanif/opencode-environment-bootstrap/raw/main/bootstrap.sh | \
  bash -s -- --snapshot ~/bootstrap-backup.zip

# 2. Clean + redeploy — wipe configs + extras (apps stay), then reinstall fresh
curl -fsSL https://github.com/vianhanif/opencode-environment-bootstrap/raw/main/bootstrap.sh | \
  bash -s -- --clean --config /path/to/local-config.json

# Or: use --skip-* flags to control what gets deployed after cleaning:
curl -fsSL https://github.com/vianhanif/opencode-environment-bootstrap/raw/main/bootstrap.sh | \
  bash -s -- --clean --skip-apps --skip-tools --config /path/to/local-config.json

# 3. Restore snapshot on top of fresh deployment
curl -fsSL https://github.com/vianhanif/opencode-environment-bootstrap/raw/main/bootstrap.sh | \
  bash -s -- --restore-snapshot ~/bootstrap-backup.zip --config /path/to/local-config.json
```

### Options

```
--config FILE              JSON/YAML config file with variables
--snapshot FILE            Create ZIP of custom configs and exit
--restore-snapshot FILE    Restore snapshot after deployment
--clean                    Wipe managed configs + extras (apps stay installed)
--skip-opencode            Skip opencode config deployment
--skip-shell               Skip shell config deployment
--skip-tools               Skip dev tool installation (lean-ctx, glab, git-review-cli, etc.)
--skip-apps                Skip app installations (brew cask)
--skip-app-configs         Skip app config deployments
--force                    Overwrite without confirmation
--dry-run                  Show what would be done without modifying anything
--verbose                  Verbose output
```

### Config variables

Set these via environment variables or a JSON/YAML config file:

| Variable | Purpose | Required |
|----------|---------|----------|
| `CONTEXT7_API_KEY` | Context7 docs API | Recommended |
| `FIRECRAWL_API_KEY` | Firecrawl web scraping API | Recommended |
| `PROJECTS_DIR` | Where your code lives (default: `~/projects`) | No |
| `METABASE_URL` | Metabase instance URL | No |
| `METABASE_USER` | Metabase username | No |
| `METABASE_PASS` | Metabase password | No |
| `BRUNO_COLLECTIONS` | JSON array: `[{"name":"X","repo":"git@...","subdir":"dir"}]` | No |

Example config file:

```json
{
  "CONTEXT7_API_KEY": "ctx7sk-...",
  "FIRECRAWL_API_KEY": "fc-...",
  "PROJECTS_DIR": "~/code",
  "BRUNO_COLLECTIONS": [
    {
      "name": "api-collection",
      "repo": "https://gitlab.com/my-org/api-collection.git"
    }
  ],
  "METABASE_URL": "https://metabase.my-org.io",
  "METABASE_USER": "me@example.com",
  "METABASE_PASS": "s3cret"
}
```

## What happens

### First run (fresh machine)

1. **Prompts** — Asks for API keys and project directory (skipped with `--force`)
2. **Homebrew** — Installs `zed`, `ghostty`, `bruno` casks (skipped with `--skip-apps` or if already present)
3. **MCP runtimes** — Checks for `npx` (Node.js), `uvx`, and `serena`; installs missing ones via Homebrew
4. **OpenCode CLI** — Runs the official installer from `opencode.ai`
5. **OpenCode config** — Backs up any existing `~/.config/opencode/`, then deploys agents, skills, commands, plugins, MCPs, and workflow rules
6. **Shell config** — Writes zsh aliases, functions, completions, lazy-loader, and exports template; appends sourcing block to `~/.zshrc`
7. **Dev tools** — Installs lean-ctx, glab, git-review-cli, opencode-session, kubectl-multi-logs, and optionally clones Bruno collections
8. **App configs** — Deploys Zed, Ghostty, and Bruno configuration (skipped with `--skip-app-configs`)
9. **Verify** — Confirms key files exist
10. **Done** — You `source ~/.zshrc`, authenticate `glab auth login`, and add secrets to `~/.zsh/exports.zsh`

### Re-run (sync updates)

1. Existing `~/.config/opencode/` is backed up to `~/.config/opencode/backup-{timestamp}/`
2. All config files are overwritten with the template versions
3. Your old config is safe in the backup directory — restore individual files as needed

### `--clean` (wipe configs + extras)

Removes everything the bootstrap manages, but **leaves apps installed**:

- OpenCode config (`~/.config/opencode/`)
- Shell dotfiles (`~/.zsh/`, `.zshrc` sourcing block)
- App configs (zed settings/keymap/rules, ghostty config, Bruno app support)
- Dev tool symlinks (`kubectl-multi-logs`, `opencode-session`, `lean-ctx`)
- Bruno collections and cloned tool repos (`opencode-session-viewer`)

Safe (not touched): zed, ghostty, bruno, glab, opencode CLI, git-review-cli, lean-ctx binary, pip packages, brew formulae.

Shows a full list of what will be removed and prompts `[y/N]` before executing. Combine with `--config` and `--skip-*` flags to re-deploy specific layers after cleaning. Pass `--snapshot FILE` first to back up custom files before wiping.

### What gets replaced

| File | Replaced? | Recovery |
|------|-----------|----------|
| `~/.config/opencode/opencode.json` | **Yes** | Restore from backup |
| `~/.config/opencode/AGENTS.md` | **Yes** | Restore from backup |
| `~/.config/opencode/package.json` | **Yes** | Restore from backup |
| `~/.config/opencode/skills/*` | **Yes** | Restore from backup |
| `~/.config/opencode/commands/*` | **Yes** | Restore from backup |
| `~/.config/opencode/plugins/*` | **Yes** | Restore from backup |
| `~/.zsh/aliases/*` | **Yes** | Restore from backup |
| `~/.zsh/functions/*` | **Yes** | Restore from backup |
| `~/.zsh/completions/_kubectl` | **Yes** | Restore from backup |
| `~/.zsh/lazyload.zsh` | **Yes** | Restore from backup |
| `~/.zsh/exports.zsh` | **Yes** | **Your API keys are here** — restore before sourcing |
| `~/.zshrc` | **Appended to, not replaced** | The sourcing block is replaced in-place |
| `~/.config/zed/settings.json` | **Yes** | Restore from backup |
| `~/.config/zed/keymap.json` | **Yes** | Restore from backup |
| `~/.config/zed/rules/lean-ctx.md` | **Yes** | Restore from backup |
| `~/.config/ghostty/config` | **Yes** | Restore from backup |
| `~/Library/Application Support/Bruno/preferences.json` | **Yes** | Restore from backup |

### What is NOT included

- **API keys** — Context7, Firecrawl, Metabase credentials are set during install (via config file or prompts) and placed in the opencode config and MCP environment fields. No post-install editing needed unless you want to rotate them.
- **GitLab authentication** — `glab auth login` or `GITLAB_TOKEN` must be set for `git-review-cli` and Bruno collection cloning.
- **Bruno environments** — Contains API keys and service URLs. Copy or configure separately after cloning collections.
- **Kubernetes context** — `kubectl` must already be installed and authenticated for `multilogs` and `pod-app-list` to work.
- **Project-specific aliases** — Add your own in `~/.zsh/aliases/` (the sourcing loop picks up all `*.zsh` files).

## MCP runtime dependencies

The opencode config includes several MCP servers that depend on external runtimes. The installer checks for these and installs missing ones via Homebrew:

| MCP server | Runtime | Installer action |
|------------|---------|------------------|
| duckdb | `uvx` | `brew install uv` if missing |
| firecrawl, mcp-mermaid, metabase, sequential-thinking | `npx` (Node.js) | `brew install node` if missing |
| serena | `serena` binary | Warns if missing (install via `uv tool install serena-agent`) |
| lean-ctx | `lean-ctx` binary | Runs install script from [yvgude/lean-ctx](https://github.com/yvgude/lean-ctx) |
| context7 | None (remote) | Not needed |

The check runs after app installations so Homebrew is ready. Use `--skip-apps` to skip brew-based installs — runtimes will still be flagged if missing.

## Tools & MCP Sources

| Component | Source |
|-----------|--------|
| **OpenCode** CLI | [opencode.ai](https://opencode.ai) |
| **lean-ctx** | [yvgude/lean-ctx](https://github.com/yvgude/lean-ctx) |
| **glab** (GitLab CLI) | [gitlab-org/cli](https://gitlab.com/gitlab-org/cli) |
| **git-review-cli** | [vianhanif/git-review-cli](https://github.com/vianhanif/git-review-cli) |
| **opencode-session** | [vianhanif/opencode-session-viewer](https://github.com/vianhanif/opencode-session-viewer) |
| **kubectl-multi-logs** | [vianhanif/kubectl-multi-logs](https://github.com/vianhanif/kubectl-multi-logs) |
| **context7** MCP | [upstash/context7](https://github.com/upstash/context7) |
| **duckdb** MCP | [motherduckdb/mcp-server-motherduck](https://github.com/motherduckdb/mcp-server-motherduck) |
| **firecrawl** MCP | [firecrawl/firecrawl-mcp-server](https://github.com/firecrawl/firecrawl-mcp-server) |
| **mermaid** MCP | [hustcc/mcp-mermaid](https://github.com/hustcc/mcp-mermaid) |
| **metabase** MCP | [imlewc/metabase-server](https://github.com/imlewc/metabase-server) |
| **sequential-thinking** MCP | [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking) |
| **serena** MCP | [oraios/serena](https://github.com/oraios/serena) |

## Design

The project is structured as:

```
bootstrap.sh       ← Bash entry point, downloads and runs installer
installer.py       ← Python installer, reads templates/ and deploys
templates/         ← Mirror of target file structure, uses $VAR substitution
  opencode/        → ~/.config/opencode/  (config, skills, commands, plugins, AGENTS.md)
  shell/           → ~/.zsh/              (aliases, functions, completions, exports, lazyload)
  zed/             → ~/.config/zed/       (settings, keymap, lean-ctx rules)
  ghostty/         → ~/.config/ghostty/   (terminal config)
  bruno/           → ~/Library/Application Support/Bruno/ (preferences)
```

Template files use Python `string.Template` syntax (`$VAR`). Variables are substituted at deploy time from environment variables, a config file, or interactive prompts. No external Python dependencies — stdlib only.

## Development

```bash
# Test without modifying anything
python3 installer.py --dry-run --verbose

# Test with a custom config
python3 installer.py --dry-run --config my-config.json
```
