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
| **OpenCode** | 5 custom agents (plan/code/review/test/analyze), session workflow rules, `/delegate` command, caveman commands, lean-ctx plugin | `~/.config/opencode/` |
| **Shell** | Zsh aliases (git, docker, general, pod-app-list), functions (multilogs), environment exports template, lazy-loaders, kubectl completions | `~/.zsh/` |
| **Zed** | Settings, keymap, lean-ctx rules | `~/.config/zed/` |
| **Ghostty** | Terminal config (Dracula theme, word-navigation keybinds) | `~/.config/ghostty/` |
| **Bruno** | API client preferences (dark theme, SSL verification off) | `~/Library/Application Support/Bruno/` |

The templates are generic — no hardcoded usernames, API keys, or organization-specific URLs. You supply those at install time or add them afterward.

## Usage

```bash
curl -fsSL https://github.com/vianhanif/opencode-environment-bootstrap/raw/main/bootstrap.sh | bash
```

Or clone and run directly:

```bash
git clone https://github.com/vianhanif/opencode-environment-bootstrap.git
cd opencode-environment-bootstrap
python3 installer.py
```

### Options

```
--config FILE        JSON/YAML config file with variables
--skip-opencode      Skip opencode config deployment
--skip-shell         Skip shell config deployment
--skip-apps          Skip app installations (brew cask)
--skip-app-configs   Skip app config deployments
--force              Overwrite without confirmation
--dry-run            Show what would be done without modifying anything
--verbose            Verbose output
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

Example config file:

```json
{
  "CONTEXT7_API_KEY": "ctx7sk-...",
  "FIRECRAWL_API_KEY": "fc-...",
  "PROJECTS_DIR": "~/code"
}
```

```bash
python3 installer.py --config my-config.json
```

## Awareness: what will happen

### First run (fresh machine)

1. **Homebrew** — Installs `zed`, `ghostty`, `bruno` casks (skipped if present)
2. **OpenCode CLI** — Runs the official installer from `opencode.ai`
3. **Prompts** — Asks for API keys and project directory (skipped with `--force`)
4. **Backup** — No existing config to back up
5. **Deploy** — Writes all config files to their locations
6. **Shell** — Appends a sourcing block to `~/.zshrc` (idempotent, detects and replaces its own block)
7. **Verify** — Confirms key files exist
8. **Done** — You `source ~/.zshrc` and add secrets to `~/.zsh/exports.zsh`

### Re-run (sync updates)

1. Existing `~/.config/opencode/` is backed up to `~/.config/opencode/backup-{timestamp}/`
2. All config files are overwritten with the template versions
3. Your old config is safe in the backup directory — restore individual files as needed

### What gets replaced

| File | Replaced? | Recovery |
|------|-----------|----------|
| `~/.config/opencode/opencode.json` | **Yes** | Restore from backup |
| `~/.config/opencode/AGENTS.md` | **Yes** | Restore from backup |
| `~/.config/opencode/skills/*` | **Yes** | Restore from backup |
| `~/.config/opencode/commands/*` | **Yes** | Restore from backup |
| `~/.zsh/aliases/*` | **Yes** | Restore from backup (if you had custom aliases) |
| `~/.zsh/exports.zsh` | **Yes** | **Your API keys are here** — restore before sourcing |
| `~/.zshrc` | **Appended to, not replaced** | The sourcing block is replaced in-place |
| `~/.config/zed/settings.json` | **Yes** | Restore from backup |
| `~/.config/ghostty/config` | **Yes** | Restore from backup |
| `~/Library/Application Support/Bruno/preferences.json` | **Yes** | Restore from backup |

### What is NOT included (you add these yourself)

- **API keys and secrets** — Context7, Firecrawl, Metabase credentials. Set via env vars or add to `~/.zsh/exports.zsh` after install.
- **Kubernetes aliases and port-forwards** — These are organization-specific. The template ships generic git/docker aliases and `pod-app-list` only.
- **Project-specific aliases** — Add your own in `~/.zsh/aliases/` (the sourcing loop picks up all `*.zsh` files).
- **[kubectl-multi-logs](https://github.com/vianhanif/kubectl-multi-logs)** — The `multilogs` function is included but requires this tool. Install it separately or clone to `$PROJECTS_DIR/codes/kubectl-multi-logs/`.
- **Bruno collections and environments** — These contain API keys and service URLs. Clone or copy them separately.
- **Personal tool documentation** — The AGENTS.md template excludes docs for `git-review-cli`, `opencode-session`, and similar personal tools. Add your own under a `## Local Tools` section.

## Development

```bash
# Test without modifying anything
python3 installer.py --dry-run --verbose

# Test with a custom config
python3 installer.py --dry-run --config my-config.json
```

## Design

The project is structured as:

```
bootstrap.sh       ← Bash entry point, downloads and runs installer
installer.py       ← Python installer, reads templates/ and deploys
templates/         ← Mirror of target file structure, uses $VAR substitution
  opencode/        → ~/.config/opencode/
  shell/           → ~/.zsh/
  zed/             → ~/.config/zed/
  ghostty/         → ~/.config/ghostty/
  bruno/           → ~/Library/Application Support/Bruno/
```

Template files use Python `string.Template` syntax (`$VAR`). Variables are substituted at deploy time from environment variables, a config file, or interactive prompts. No external Python dependencies — stdlib only.
