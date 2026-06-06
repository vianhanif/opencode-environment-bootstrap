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
| **Dev tools** | lean-ctx, glab (GitLab CLI), git-review-cli, opencode-session, kubectl-multi-logs, Bruno collections | Installed by default — skip with `--skip-tools` |
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
--skip-tools         Skip dev tool installation (lean-ctx, glab, git-review-cli, etc.)
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

```bash
python3 installer.py --config my-config.json
```

## Awareness: what will happen

### First run (fresh machine)

1. **Prompts** — Asks for API keys and project directory (skipped with `--force`)
2. **Homebrew** — Installs `zed`, `ghostty`, `bruno` casks (skipped if present)
3. **OpenCode CLI** — Runs the official installer from `opencode.ai`
4. **OpenCode config** — Backs up any existing `~/.config/opencode/`, then deploys agents, skills, commands, plugins, MCPs, and workflow rules
5. **Shell config** — Writes zsh aliases, functions, completions, lazy-loader, and exports template; appends sourcing block to `~/.zshrc`
6. **Dev tools** — Installs lean-ctx, glab, git-review-cli, opencode-session, kubectl-multi-logs, and optionally clones Bruno collections
7. **App configs** — Deploys Zed, Ghostty, and Bruno configuration
8. **Verify** — Confirms key files exist
9. **Done** — You `source ~/.zshrc`, authenticate `glab auth login`, and add secrets to `~/.zsh/exports.zsh`

### Re-run (sync updates)

1. Existing `~/.config/opencode/` is backed up to `~/.config/opencode/backup-{timestamp}/`
2. All config files are overwritten with the template versions
3. Your old config is safe in the backup directory — restore individual files as needed

### What gets replaced

| File | Replaced? | Recovery |
|------|-----------|----------|
| `~/.config/opencode/opencode.json` | **Yes** | Restore from backup |
| `~/.config/opencode/AGENTS.md` | **Yes** | Restore from backup |
| `~/.config/opencode/package.json` | **Yes** | Restore from backup |
| `~/.config/opencode/.gitignore` | **Yes** | Restore from backup |
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

### What is NOT included (you add these yourself)

- **API keys and secrets** — Context7, Firecrawl, Metabase credentials. Set via env vars or add to `~/.zsh/exports.zsh` after install.
- **GitLab authentication** — `glab auth login` or `GITLAB_TOKEN` must be set for `git-review-cli` and Bruno collection cloning.
- **Bruno environments** — Contains API keys and service URLs. Copy or configure separately after cloning collections.
- **Kubernetes context** — `kubectl` must already be installed and authenticated for `multilogs` and `pod-app-list` to work.
- **Project-specific aliases** — Add your own in `~/.zsh/aliases/` (the sourcing loop picks up all `*.zsh` files).

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
  opencode/        → ~/.config/opencode/  (config, skills, commands, plugins, AGENTS.md)
  shell/           → ~/.zsh/              (aliases, functions, completions, exports, lazyload)
  zed/             → ~/.config/zed/       (settings, keymap, lean-ctx rules)
  ghostty/         → ~/.config/ghostty/   (terminal config)
  bruno/           → ~/Library/Application Support/Bruno/ (preferences)
```

Template files use Python `string.Template` syntax (`$VAR`). Variables are substituted at deploy time from environment variables, a config file, or interactive prompts. No external Python dependencies — stdlib only.
