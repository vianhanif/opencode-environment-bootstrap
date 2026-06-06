#!/usr/bin/env python3
"""
opencode-bootstrap — One-shot AI engineering environment setup.

Bootstraps a new machine with:
  - OpenCode CLI + config (agents, skills, commands, MCPs, plugins)
  - Shell config (zsh aliases, functions, exports, completions)
  - App configs (Zed editor, Ghostty terminal, Bruno API client)
  - Optional dev tools (lean-ctx context manager, session helpers)

Usage:
  python3 installer.py [options]

Options:
  --config FILE       JSON/YAML config with variables
  --skip-opencode     Skip opencode config deployment
  --skip-shell        Skip shell config deployment
  --skip-apps         Skip app installations (brew cask)
  --skip-tools        Skip dev tool installations
  --force             Overwrite without confirmation
  --dry-run           Show what would be done
  --verbose           Verbose output

Config variables (env vars or config file):
  PROJECTS_DIR       Code projects location          (default: ~/projects)
  CONTEXT7_API_KEY   Context7 documentation API key  (prompted if missing)
  FIRECRAWL_API_KEY  Firecrawl web scraping API key  (prompted if missing)
  METABASE_URL       Metabase instance URL            (optional)
  METABASE_USER      Metabase username                 (optional)
  METABASE_PASS      Metabase password                 (optional)
  GITLAB_ORG         GitLab org for MR workflows       (optional)
  BRUNO_COLLECTIONS  JSON array of {name, repo, subdir} (optional)

Examples:
  python3 installer.py --force
  PROJECTS_DIR=~/code python3 installer.py --skip-apps
  python3 installer.py --config my-config.json
"""

import os, sys, json, shutil, subprocess, datetime, re, stat
from pathlib import Path
from string import Template


# ── Constants ──

SCRIPT_DIR = Path(__file__).parent.resolve()
TEMPLATES_DIR = SCRIPT_DIR / "templates"
ZSH_SOURCING_HEADER = "# --- opencode-bootstrap: zsh config ---"
ZSH_SOURCING_FOOTER = "# --- /opencode-bootstrap ---"
DEFAULT_PROJECTS = "~/projects"

# Files to skip if they contain secrets (never template-ified)
SKIP_PATTERNS = [
    "environments/", "global-environments.json",
    "collection-security.json",
]

APP_BREW_CASKS = {
    "zed":     {"cask": "zed",     "config": ".config/zed",                       "app_path": "/Applications/Zed.app"},
    "ghostty": {"cask": "ghostty", "config": ".config/ghostty",                   "app_path": "/Applications/Ghostty.app"},
    "bruno":   {"cask": "bruno",   "config": "Library/Application Support/Bruno", "app_path": "/Applications/Bruno.app"},
}


# ── Utility ──

def info(msg):
    print(f"  ✓ {msg}")

def warn(msg):
    print(f"  ⚠ {msg}")

def step(msg):
    print(f"\n━━━ {msg} ━━━")

def run(cmd, **kw):
    kw.setdefault("check", True)
    return subprocess.run(cmd, **kw)


# ── Variable resolution ──

def resolve_variables(args):
    """Resolve template variables from env, config file, or prompts."""
    vars = {
        "USER": os.environ.get("USER", "developer"),
        "HOME": os.environ.get("HOME", f"/home/{os.environ.get('USER', 'developer')}"),
    }

    # Defaults
    defaults = {
        "PROJECTS_DIR": os.environ.get("PROJECTS_DIR", DEFAULT_PROJECTS),
        "GITLAB_ORG": os.environ.get("GITLAB_ORG", ""),
        "CONTEXT7_API_KEY": os.environ.get("CONTEXT7_API_KEY", ""),
        "FIRECRAWL_API_KEY": os.environ.get("FIRECRAWL_API_KEY", ""),
        "METABASE_URL": os.environ.get("METABASE_URL", ""),
        "METABASE_USER": os.environ.get("METABASE_USER", ""),
        "METABASE_PASS": os.environ.get("METABASE_PASS", ""),
        "INSTALL_DEV_TOOLS": os.environ.get("INSTALL_DEV_TOOLS", "false"),
    }

    # Load config file if provided
    if args.config:
        path = Path(args.config)
        if path.suffix in (".json",):
            cfg = json.loads(path.read_text())
        elif path.suffix in (".yml", ".yaml"):
            try:
                import yaml
                cfg = yaml.safe_load(path.read_text())
            except ImportError:
                cfg = {}
                warn(f"PyYAML not installed, ignoring {path}")
        else:
            cfg = {}
        defaults.update({k: v for k, v in cfg.items() if v})

    # Env vars override config file
    for key in defaults:
        env_val = os.environ.get(key)
        if env_val:
            defaults[key] = env_val
        elif key in vars:
            continue
        else:
            vars[key] = defaults[key] if defaults[key] else ""

    # Apply to vars (preserve non-primitive types like lists/dicts)
    for key, val in defaults.items():
        if val is not None:
            if isinstance(val, (str, int, float, bool)):
                vars[key] = str(val)
            else:
                vars[key] = val

    # Prompt for critical missing values (non-interactive if --force)
    if not args.dry_run and not sys.stdin.isatty():
        # Non-interactive mode — just use env/defaults
        pass
    elif not args.dry_run and not args.force:
        if not vars.get("CONTEXT7_API_KEY"):
            resp = input("  Context7 API key (or Enter to skip): ").strip()
            if resp:
                vars["CONTEXT7_API_KEY"] = resp
        if not vars.get("FIRECRAWL_API_KEY"):
            resp = input("  Firecrawl API key (or Enter to skip): ").strip()
            if resp:
                vars["FIRECRAWL_API_KEY"] = resp
        resp = input(f"  Projects directory [{vars.get('PROJECTS_DIR', DEFAULT_PROJECTS)}]: ").strip()
        if resp:
            vars["PROJECTS_DIR"] = resp

    # Expand ~ in paths
    for key in ("PROJECTS_DIR",):
        v = vars.get(key, "")
        if v.startswith("~/"):
            vars[key] = str(Path(v).expanduser())

    return vars


# ── Template engine ──

def render_template(template_path, vars):
    """Read a template file and substitute $VARIABLE references."""
    content = template_path.read_text()
    return Template(content).safe_substitute(**vars)


def deploy_file(src, dst, vars=None, backup_dir=None, dry_run=False):
    """Render and deploy a single template file. Returns deployed path or None."""
    dst = Path(str(dst).replace("$HOME", vars.get("HOME", "~")).replace("~", vars.get("HOME", "~")))
    dst = dst.expanduser()

    if backup_dir and dst.exists() and not dry_run:
        rel = dst.relative_to(Path.home()) if dst.is_relative_to(Path.home()) else Path(dst.name)
        bk = backup_dir / rel
        bk.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dst, bk)

    content = template_path.read_text()
    if vars:
        content = Template(content).safe_substitute(**vars)

    if dry_run:
        print(f"  [dry-run] Would write: {dst}")
        return dst

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(content)
    return dst


def deploy_tree(src_dir, dst_root, vars, backup_dir=None, dry_run=False, skip=None):
    """Deploy an entire template tree preserving relative paths."""
    skip = skip or []
    deployed = []
    for f in sorted(src_dir.rglob("*")):
        if not f.is_file():
            continue
        if any(p in str(f) for p in skip):
            continue
        rel = f.relative_to(src_dir)
        dst = dst_root / rel
        deploy_file(f, dst, vars, backup_dir, dry_run)
        deployed.append(dst)
    return deployed


# ── Backup ──

def create_backup(path):
    """Create a timestamped backup. Returns backup path or None."""
    if not path.exists():
        return None
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.parent / f"{path.name}-backup-{ts}"
    if backup.exists():
        shutil.rmtree(backup)
    shutil.copytree(path, backup)
    return backup


# ── OpenCode installation ──

def ensure_opencode(vars, dry_run=False):
    """Install opencode CLI if not present."""
    step("OpenCode CLI")

    existing = shutil.which("opencode")
    if existing:
        info(f"Already installed at {existing}")
        # Try updating
        if not dry_run:
            try:
                run(["opencode", "--version"], capture_output=True)
            except Exception:
                warn("opencode binary found but not working — may need reinstall")
        return

    # Install via script
    info("Installing opencode...")
    if dry_run:
        info("[dry-run] Would run: curl -fsSL https://opencode.ai/install.sh | bash")
        return

    try:
        run(["curl", "-fsSL", "https://opencode.ai/install.sh"], check=False)
        warn("Install script requires manual confirmation. Run it yourself:")
        print("  curl -fsSL https://opencode.ai/install.sh | bash")
    except FileNotFoundError:
        warn("curl not available. Install opencode manually:")
        print("  curl -fsSL https://opencode.ai/install.sh | bash")


# ── App installation (Homebrew) ──

def ensure_apps(vars, dry_run=False):
    """Install configured apps via Homebrew."""
    step("Applications (Homebrew)")

    if not shutil.which("brew"):
        info("Homebrew not found. Install it first:")
        info("  /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
        return

    def _is_installed(name, cfg):
        if shutil.which(name):
            return True
        app_path = cfg.get("app_path", "")
        if app_path and os.path.isdir(app_path):
            return True
        return False

    to_install = []
    for name, cfg in APP_BREW_CASKS.items():
        if not _is_installed(name, cfg):
            to_install.append(name)

    if not to_install:
        info("All apps already installed")
        return

    if dry_run:
        info(f"[dry-run] Would install: {', '.join(to_install)}")
        return

    info(f"Installing: {', '.join(to_install)}")
    try:
        run(["brew", "install", "--cask"] + to_install)
    except subprocess.CalledProcessError:
        warn("Some apps failed to install. Check brew output above.")


# ── Dev tools ──

REPOS = {
    "kubectl-multi-logs":  "https://github.com/vianhanif/kubectl-multi-logs.git",
    "git-review-cli":      "https://github.com/vianhanif/git-review-cli.git",
    "opencode-session":    "https://github.com/vianhanif/opencode-session-viewer.git",
}

def _clone_repo(url, dest, dry_run=False):
    """Clone a git repo shallowly. Returns True on success."""
    if not shutil.which("git"):
        warn("git not found — skipping clone")
        return False
    if dry_run:
        info(f"[dry-run] Would clone {url} to {dest}")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", "--depth", "1", url, str(dest)])
    return True

def _pip_install(path, dry_run=False):
    """pip install -e a local path."""
    pip = shutil.which("pip3") or shutil.which("pip")
    if not pip:
        warn("pip not found — skip pip install")
        return False
    if dry_run:
        info(f"[dry-run] Would run: {pip} install -e {path}")
        return True
    run([pip, "install", "-e", str(path)])
    return True

def _symlink(target, name, dry_run=False):
    """Symlink target to ~/.local/bin/{name}."""
    local_bin = Path.home() / ".local" / "bin"
    link = local_bin / name
    if link.exists() or link.is_symlink():
        return True
    if dry_run:
        info(f"[dry-run] Would symlink: {link} → {target}")
        return True
    local_bin.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target)
    info(f"Symlinked: {link}")
    return True


def ensure_lean_ctx(vars, dry_run=False):
    """Ensure lean-ctx binary is installed."""
    if shutil.which("lean-ctx"):
        return
    step("Dev tool: lean-ctx")
    if dry_run:
        info("[dry-run] Would run install script")
        return
    info("Installing lean-ctx...")
    try:
        run(["curl", "-fsSL",
             "https://raw.githubusercontent.com/nicerpc/lean-ctx/main/install.sh"],
            check=False)
        warn("Install script may require manual steps. See: https://github.com/nicerpc/lean-ctx")
    except FileNotFoundError:
        warn("curl not available. Install lean-ctx manually.")

def ensure_glab(vars, dry_run=False):
    """Ensure glab (GitLab CLI) is installed."""
    if shutil.which("glab"):
        return
    step("Dev tool: glab (GitLab CLI)")
    if dry_run:
        info("[dry-run] Would run: brew install glab")
        return
    if not shutil.which("brew"):
        warn("Homebrew not found — install glab manually: brew install glab")
        return
    try:
        run(["brew", "install", "glab"])
    except subprocess.CalledProcessError:
        warn("glab install failed. Retry: brew install glab")

def ensure_git_review_cli(vars, dry_run=False):
    """Install git-review-cli via pip."""
    if shutil.which("git-review-cli"):
        return
    step("Dev tool: git-review-cli")
    if dry_run:
        info("[dry-run] Would pip install git-review-cli")
        return
    try:
        _pip_install(REPOS["git-review-cli"], dry_run)
    except Exception as e:
        warn(f"git-review-cli install failed: {e}")
        info("Manual: pip3 install git+https://github.com/vianhanif/git-review-cli.git")

def ensure_opencode_session(vars, dry_run=False):
    """Clone opencode-session-viewer and symlink."""
    if shutil.which("opencode-session"):
        return
    step("Dev tool: opencode-session")
    projects_dir = Path(vars.get("PROJECTS_DIR", "~/projects")).expanduser()
    dest = projects_dir / "codes" / "opencode-session-viewer"

    if dest.exists() and (dest / "opencode-session.py").exists():
        _symlink(dest / "opencode-session.py", "opencode-session", dry_run)
        return

    if dry_run:
        info(f"[dry-run] Would clone to {dest} and symlink")
        return

    _clone_repo(REPOS["opencode-session"], dest, dry_run)
    script = dest / "opencode-session.py"
    if script.exists():
        _symlink(script, "opencode-session", dry_run)
        info("opencode-session installed")

def ensure_kubectl_multi_logs(vars, dry_run=False):
    """Clone kubectl-multi-logs and install."""
    if shutil.which("kubectl-multi-logs"):
        return
    step("Dev tool: kubectl-multi-logs")
    projects_dir = Path(vars.get("PROJECTS_DIR", "~/projects")).expanduser()
    dest = projects_dir / "codes" / "kubectl-multi-logs"

    if dest.exists() and (dest / "kubectl-multi-logs").exists():
        _symlink(dest / "kubectl-multi-logs", "kubectl-multi-logs", dry_run)
        return

    if dry_run:
        info(f"[dry-run] Would clone to {dest}, pip install, and symlink")
        return

    _clone_repo(REPOS["kubectl-multi-logs"], dest, dry_run)
    if (dest / "setup.py").exists() or (dest / "pyproject.toml").exists():
        _pip_install(dest, dry_run)
    script = dest / "kubectl-multi-logs"
    if script.exists():
        _symlink(script, "kubectl-multi-logs", dry_run)

def ensure_bruno_collections(vars, dry_run=False):
    """Clone Bruno collections from config."""
    raw = vars.get("BRUNO_COLLECTIONS", "")
    if not raw:
        return

    import json as _json
    try:
        collections = _json.loads(raw) if isinstance(raw, str) else raw
    except _json.JSONDecodeError:
        warn("BRUNO_COLLECTIONS is not valid JSON — skipping")
        return

    if not isinstance(collections, list):
        collections = [collections]

    step("Bruno collections")
    projects_dir = Path(vars.get("PROJECTS_DIR", "~/projects")).expanduser()
    base = projects_dir / "bruno" / "collections"

    for col in collections:
        name = col.get("name", col.get("repo", "unknown"))
        repo = col.get("repo", "")
        subdir = col.get("subdir", "")
        if not repo:
            continue
        dest = base / name
        if dest.exists():
            info(f"Collection '{name}' already exists at {dest}")
            continue
        if dry_run:
            info(f"[dry-run] Would clone {repo} to {dest}")
            continue
        try:
            _clone_repo(repo, dest, dry_run)
        except Exception as e:
            warn(f"Failed to clone collection '{name}': {e}")


# ── OpenCode config deployment ──

def deploy_opencode_config(vars, dry_run=False):
    """Backup and deploy opencode config from templates."""
    step("OpenCode configuration")

    opencode_dir = Path.home() / ".config" / "opencode"
    src_dir = TEMPLATES_DIR / "opencode"

    if not src_dir.exists():
        info("No opencode templates found — skipping")
        return

    # Backup
    backup = None
    if not dry_run:
        backup = create_backup(opencode_dir)
        if backup:
            info(f"Backup: {backup}")

    # Deploy
    if dry_run:
        # Just show files
        for f in sorted(src_dir.rglob("*")):
            if f.is_file():
                rel = f.relative_to(src_dir)
                dst = opencode_dir / rel
                print(f"  [dry-run] {dst}")
        return

    # Remove existing (backup was already made) and re-create
    if opencode_dir.exists():
        shutil.rmtree(opencode_dir)
    opencode_dir.mkdir(parents=True)

    for f in sorted(src_dir.rglob("*")):
        if not f.is_file():
            continue
        if f.name.endswith((".pyc", ".pyo")):
            continue
        rel = f.relative_to(src_dir)
        dst = opencode_dir / rel
        deploy_file(f, dst, vars)
        info(str(dst))

    info("OpenCode config deployed")


# ── Shell config deployment ──

def deploy_shell_config(vars, dry_run=False):
    """Deploy shell config and update .zshrc."""
    step("Shell configuration")

    zsh_dir = Path.home() / ".zsh"
    src_dir = TEMPLATES_DIR / "shell"
    zshrc = Path.home() / ".zshrc"

    # Deploy zsh config files
    if src_dir.exists():
        if dry_run:
            for f in sorted(src_dir.rglob("*")):
                if f.is_file():
                    rel = f.relative_to(src_dir)
                    print(f"  [dry-run] {zsh_dir / rel}")
        else:
            zsh_dir.mkdir(parents=True, exist_ok=True)
            for f in sorted(src_dir.rglob("*")):
                if not f.is_file():
                    continue
                rel = f.relative_to(src_dir)
                dst = zsh_dir / rel
                deploy_file(f, dst, vars)
                info(f"shell/{rel}")
    else:
        info("No shell templates — skipping")

    # Update .zshrc (idempotent)
    if dry_run:
        if zshrc.exists() and ZSH_SOURCING_HEADER not in zshrc.read_text():
            print(f"  [dry-run] Would add sourcing block to {zshrc}")
        elif not zshrc.exists():
            print(f"  [dry-run] Would create {zshrc}")
        return

    if not zshrc.exists():
        zshrc.write_text(f"""# Zsh config — managed by opencode-bootstrap
{generate_zshrc_block(vars)}
""")
        info(f"Created {zshrc}")
        return

    content = zshrc.read_text()
    if ZSH_SOURCING_HEADER in content:
        # Replace existing block
        pattern = re.compile(
            rf"{re.escape(ZSH_SOURCING_HEADER)}.*?{re.escape(ZSH_SOURCING_FOOTER)}",
            re.DOTALL,
        )
        if pattern.search(content):
            content = pattern.sub(generate_zshrc_block(vars), content)
            zshrc.write_text(content)
            info(f"Updated sourcing block in {zshrc}")
        else:
            warn("Sourcing header found but footer missing — appending new block")
            zshrc.write_text(content.rstrip() + "\n\n" + generate_zshrc_block(vars) + "\n")
    else:
        zshrc.write_text(content.rstrip() + "\n\n" + generate_zshrc_block(vars) + "\n")
        info(f"Added sourcing block to {zshrc}")


def generate_zshrc_block(vars):
    """Generate the .zshrc sourcing section."""
    return f"""{ZSH_SOURCING_HEADER}
export OPCODE_PROJECTS_DIR="{vars.get('PROJECTS_DIR', DEFAULT_PROJECTS)}"
export PATH="$HOME/.local/bin:$PATH"
export PATH="$HOME/.opencode/bin:$PATH"
[[ -f ~/.zsh/exports.zsh ]] && source ~/.zsh/exports.zsh
for file in ~/.zsh/aliases/*.zsh; do [[ -f "$file" ]] && source "$file"; done
for file in ~/.zsh/functions/*.zsh; do [[ -f "$file" ]] && source "$file"; done
[[ -f ~/.zsh/lazyload.zsh ]] && source ~/.zsh/lazyload.zsh
{ZSH_SOURCING_FOOTER}"""


# ── App config deployment (Zed, Ghostty, Bruno) ──

APP_CONFIG_MAP = {
    "zed":     (".config/zed",                  TEMPLATES_DIR / "zed"),
    "ghostty": (".config/ghostty",              TEMPLATES_DIR / "ghostty"),
    "bruno":   ("Library/Application Support/Bruno", TEMPLATES_DIR / "bruno"),
}


def deploy_app_configs(vars, dry_run=False):
    """Deploy application config files."""
    step("Application configurations")

    for name, (rel_dst, src_dir) in APP_CONFIG_MAP.items():
        if not src_dir.exists():
            continue
        dst_root = Path.home() / rel_dst

        if dry_run:
            for f in sorted(src_dir.rglob("*")):
                if f.is_file():
                    rel = f.relative_to(src_dir)
                    print(f"  [dry-run] {dst_root / rel}")
            continue

        dst_root.mkdir(parents=True, exist_ok=True)
        for f in sorted(src_dir.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(src_dir)
            dst = dst_root / rel
            deploy_file(f, dst, vars)
        info(f"{name} config deployed")


# ── Verification ──

def verify_deployment(vars, dry_run=False):
    """Verify that key files were deployed correctly."""
    if dry_run:
        return

    step("Verification")
    checks = [
        (Path.home() / ".config" / "opencode" / "opencode.json", "OpenCode config"),
        (Path.home() / ".config" / "opencode" / "AGENTS.md", "OpenCode AGENTS.md"),
        (Path.home() / ".config" / "opencode" / "skills" / "planner" / "SKILL.md", "Planner skill"),
        (Path.home() / ".zsh" / "aliases" / "git.zsh", "Shell aliases"),
        (Path.home() / ".zsh" / "lazyload.zsh", "Lazyload"),
    ]

    all_ok = True
    for path, label in checks:
        if path.exists():
            info(f"{label}: {path}")
        else:
            warn(f"{label}: not found at {path}")
            all_ok = False

    if all_ok:
        info("All checks passed")
    else:
        warn("Some files were not deployed. Check templates/ directory.")
    return all_ok


# ── Summary ──

def print_summary(vars):
    """Print post-installation summary."""
    print()
    print("=" * 56)
    print("  opencode-bootstrap: Setup complete!")
    print("=" * 56)
    print()
    print("  Next steps:")
    print(f"    1. source ~/.zshrc")
    print("    2. Add your secrets to ~/.zsh/exports.zsh (API keys, etc.)")
    print("    3. If you skipped Context7/Firecrawl keys, add them later:")
    print("       export CONTEXT7_API_KEY='...'")
    print("       export FIRECRAWL_API_KEY='...'")
    print("    4. Restart opencode to load new config")
    print("    5. If using git-review-cli, authenticate glab:")
    print("       glab auth login  # or set GITLAB_TOKEN")
    print("    6. Test multilogs: multilogs --help")
    print("    7. If Bruno collections were cloned, open Bruno and")
    print("       add the collection directories as workspaces")
    print()
    print(f"  Config used:")
    for key in ("PROJECTS_DIR", "GITLAB_ORG", "METABASE_URL"):
        val = vars.get(key, "")
        if val:
            print(f"    {key}={val}")
    print()
    print(f"  Backup (if any): ~/.config/opencode/backup-*")
    print(f"  Docs: https://github.com/vianhanif/opencode-environment-bootstrap")


# ── Main ──

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="OpenCode environment bootstrap",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--config", help="JSON/YAML config file with variables")
    parser.add_argument("--skip-opencode", action="store_true", help="Skip opencode config deployment")
    parser.add_argument("--skip-shell", action="store_true", help="Skip shell config deployment")
    parser.add_argument("--skip-apps", action="store_true", help="Skip app installations")
    parser.add_argument("--skip-app-configs", action="store_true", help="Skip app config deployments")
    parser.add_argument("--skip-tools", action="store_true", help="Skip dev tool installations")
    parser.add_argument("--force", action="store_true", help="Overwrite without confirmation")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if args.dry_run:
        print("◈ DRY RUN — no files will be modified ◈")

    vars = resolve_variables(args)

    if args.verbose:
        print(f"\nTemplate variables:")
        for k, v in sorted(vars.items()):
            if any(secret in k.lower() for secret in ("key", "pass", "token", "secret")):
                print(f"  {k}=***")
            else:
                print(f"  {k}={v}")

    # Phase 1: Install apps (optional)
    if not args.skip_apps:
        ensure_apps(vars, args.dry_run)

    # Phase 2: Install opencode CLI
    if not args.skip_opencode:
        ensure_opencode(vars, args.dry_run)
        deploy_opencode_config(vars, args.dry_run)

    # Phase 3: Shell config
    if not args.skip_shell:
        deploy_shell_config(vars, args.dry_run)

    # Phase 4: Dev tools
    if not args.skip_tools:
        ensure_lean_ctx(vars, args.dry_run)
        ensure_glab(vars, args.dry_run)
        ensure_git_review_cli(vars, args.dry_run)
        ensure_opencode_session(vars, args.dry_run)
        ensure_kubectl_multi_logs(vars, args.dry_run)
        ensure_bruno_collections(vars, args.dry_run)

    # Phase 5: App configs
    if not args.skip_app_configs:
        deploy_app_configs(vars, args.dry_run)

    # Phase 6: Verify
    verify_deployment(vars, args.dry_run)

    # Summary
    if not args.dry_run:
        print_summary(vars)


if __name__ == "__main__":
    main()
