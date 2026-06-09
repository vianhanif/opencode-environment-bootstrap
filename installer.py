#!/usr/bin/env python3
"""
opencode-bootstrap — One-shot AI engineering environment setup.

Bootstraps a new machine with:
  - OpenCode CLI + config (agents, skills, commands, MCPs, plugins)
  - Shell config (zsh aliases, functions, exports, completions)
  - App configs (Zed editor, Ghostty terminal, Bruno API client)
  - Optional dev tools (session helpers)

Usage:
  python3 installer.py [options]

Options:
  --config FILE       JSON/YAML config with variables
  --skip-opencode     Skip opencode config deployment
  --skip-shell        Skip shell config deployment
  --skip-apps         Skip app installations (brew cask)
  --skip-app-configs  Skip app config deployments
  --skip-tools        Skip dev tool installations
  --force             Overwrite without confirmation
  --dry-run           Show what would be done
  --verbose           Verbose output
  --snapshot FILE     Create ZIP snapshot of custom files and exit
  --restore-snapshot FILE  Restore snapshot after deployment
  --clean             Remove managed configs + extras (apps stay installed)
  --verify            Run comprehensive installation verification (standalone or after deploy)

Config variables (env vars or config file):
  PROJECTS_DIR       Code projects location          (default: ~/projects)
  CONTEXT7_API_KEY   Context7 documentation API key  (prompted if missing)
  FIRECRAWL_API_KEY  Firecrawl web scraping API key  (prompted if missing)
  METABASE_URL       Metabase instance URL            (optional)
  METABASE_USER      Metabase username                 (optional)
  METABASE_PASS      Metabase password                 (optional)
  BRUNO_COLLECTIONS  JSON array of {name, repo, subdir} (optional)

Examples:
  python3 installer.py --force
  PROJECTS_DIR=~/code python3 installer.py --skip-apps
  python3 installer.py --config my-config.json
"""

import os, sys, json, shutil, subprocess, datetime, re, stat, zipfile
from pathlib import Path
from string import Template


def _prompt_input(prompt):
    """Read input from the terminal, even when stdin is piped (e.g. curl | bash)."""
    try:
        with open("/dev/tty", "r") as tty:
            sys.stdout.write(prompt)
            sys.stdout.flush()
            return tty.readline().strip()
    except (OSError, IOError):
        return input(prompt).strip()


# ── Constants ──

SCRIPT_DIR = Path(__file__).parent.resolve()
TEMPLATES_DIR = SCRIPT_DIR / "templates"
ZSH_SOURCING_HEADER = "# --- opencode-bootstrap: zsh config ---"
ZSH_SOURCING_FOOTER = "# --- /opencode-bootstrap ---"
DEFAULT_PROJECTS = "~/projects"

VERSION_FILE = SCRIPT_DIR / "VERSION"
BOOTSTRAP_VERSION = VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else "unknown"

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
        "CONTEXT7_API_KEY": os.environ.get("CONTEXT7_API_KEY", ""),
        "FIRECRAWL_API_KEY": os.environ.get("FIRECRAWL_API_KEY", ""),
        "METABASE_URL": os.environ.get("METABASE_URL", ""),
        "METABASE_USER": os.environ.get("METABASE_USER", ""),
        "METABASE_PASS": os.environ.get("METABASE_PASS", ""),
        "INSTALL_DEV_TOOLS": os.environ.get("INSTALL_DEV_TOOLS", "false"),
        "MODEL_PLANNER": os.environ.get("MODEL_PLANNER", "opencode-go/deepseek-v4-pro"),
        "MODEL_CODER": os.environ.get("MODEL_CODER", "opencode-go/deepseek-v4-flash"),
        "MODEL_REVIEWER": os.environ.get("MODEL_REVIEWER", "opencode-go/deepseek-v4-pro"),
        "MODEL_TESTER": os.environ.get("MODEL_TESTER", "opencode-go/deepseek-v4-flash"),
        "MODEL_ANALYZER": os.environ.get("MODEL_ANALYZER", "opencode-go/deepseek-v4-pro"),
        "MODEL_BRAIN": os.environ.get("MODEL_BRAIN", "opencode-go/deepseek-v4-pro"),
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

    content = src.read_text()
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
    "git-review-cli":      "git+https://github.com/vianhanif/git-review-cli.git",
    "opencode-session":    "https://github.com/vianhanif/opencode-session-viewer.git",
}

def _clone_repo(url, dest, dry_run=False):
    """Clone a git repo shallowly, or pull if already exists. Returns True on success."""
    if not shutil.which("git"):
        warn("git not found — skipping clone")
        return False
    if dry_run:
        info(f"[dry-run] Would clone {url} to {dest}")
        return True
    if dest.exists():
        info(f"Repo exists at {dest} — pulling latest")
        try:
            run(["git", "-C", str(dest), "pull", "--ff-only"], check=False)
        except subprocess.CalledProcessError:
            warn(f"git pull failed for {dest}")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", "--depth", "1", url, str(dest)])
    return True

def _pip_install(url, dry_run=False):
    """pip install from a git URL."""
    if not shutil.which("python3"):
        warn("python3 not found — skip pip install")
        return False
    if dry_run:
        info(f"[dry-run] Would run: python3 -m pip install {url}")
        return True
    run(["python3", "-m", "pip", "install", str(url)])
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


def ensure_rtk(vars, dry_run=False):
    """Ensure rtk (Rust Token Killer) is installed."""
    if shutil.which("rtk"):
        return
    step("Dev tool: rtk (Rust Token Killer)")
    if dry_run:
        info("[dry-run] Would run: brew install rtk")
        return
    if shutil.which("brew"):
        try:
            run(["brew", "install", "rtk"])
            return
        except subprocess.CalledProcessError:
            warn("brew install rtk failed — trying curl install")
    info("Installing rtk via curl...")
    try:
        run(["bash", "-c",
             "curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/master/install.sh | sh"],
            check=False)
        if not shutil.which("rtk"):
            warn("Install script finished but rtk not found in PATH")
    except FileNotFoundError:
        warn("curl not available. Install rtk manually: brew install rtk")

def _init_rtk_opencode(vars, dry_run=False):
    """Configure rtk as an OpenCode plugin."""
    if not shutil.which("rtk"):
        return
    step("RTK: OpenCode plugin")
    if dry_run:
        info("[dry-run] Would run: rtk init -g --opencode")
        return
    try:
        run(["rtk", "init", "-g", "--opencode"], check=False)
        info("RTK OpenCode plugin installed")
    except FileNotFoundError:
        warn("rtk binary not found — skip plugin setup")

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

def _is_python_git_review_cli(path):
    """Check if the given git-review-cli is the Python version (not Node.js)."""
    try:
        result = subprocess.run(
            [str(path), "--version"],
            capture_output=True, text=True, timeout=5,
        )
        return "git-review-cli" in result.stdout and result.returncode == 0
    except Exception:
        return False

def _remove_conflicting_git_review_cli(dry_run=False):
    """Remove any non-Python git-review-cli that would shadow the pip install."""
    for loc in ["/usr/local/bin/git-review-cli", "/usr/local/lib/node_modules/git-review-cli"]:
        p = Path(loc)
        if p.exists() or p.is_symlink():
            if dry_run:
                info(f"[dry-run] Would remove conflicting {loc}")
            else:
                info(f"Removing conflicting {loc} (non-Python git-review-cli)")
                p.unlink(missing_ok=True)

def ensure_git_review_cli(vars, dry_run=False):
    """Install git-review-cli via pip and symlink to ~/.local/bin."""
    existing = shutil.which("git-review-cli")
    if existing:
        if _is_python_git_review_cli(existing):
            return
        info(f"Found non-Python git-review-cli at {existing} — will reinstall")
        _remove_conflicting_git_review_cli(dry_run)
    step("Dev tool: git-review-cli")
    if dry_run:
        info("[dry-run] Would pip install git-review-cli")
        return
    try:
        _pip_install(REPOS["git-review-cli"], dry_run)
    except Exception as e:
        warn(f"git-review-cli install failed: {e}")
        info("Manual: pip3 install git+https://github.com/vianhanif/git-review-cli.git")
        return
    # Symlink to ~/.local/bin in case pip installed it off PATH
    pip_path = shutil.which("git-review-cli")
    if pip_path:
        _symlink(Path(pip_path), "git-review-cli", dry_run)

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

def _symlink_multilogs(script, name, vars, dry_run):
    """Create a symlink for multilogs (with both names)."""
    _symlink(script, name, dry_run)
    if name == "kubectl-multi-logs":
        _symlink(script, "multilogs", dry_run)


def ensure_kubectl_multi_logs(vars, dry_run=False):
    """Clone kubectl-multi-logs and install."""
    if shutil.which("kubectl-multi-logs") and shutil.which("multilogs"):
        return
    step("Dev tool: kubectl-multi-logs")
    projects_dir = Path(vars.get("PROJECTS_DIR", "~/projects")).expanduser()
    dest = projects_dir / "codes" / "kubectl-multi-logs"

    if dest.exists() and (dest / "kubectl-multi-logs").exists():
        _symlink_multilogs(dest / "kubectl-multi-logs", "kubectl-multi-logs", vars, dry_run)
        return

    if dry_run:
        info(f"[dry-run] Would clone to {dest}, pip install, and symlink")
        return

    _clone_repo(REPOS["kubectl-multi-logs"], dest, dry_run)
    if (dest / "setup.py").exists() or (dest / "pyproject.toml").exists():
        _pip_install(dest, dry_run)
    script = dest / "kubectl-multi-logs"
    if script.exists():
        _symlink_multilogs(script, "kubectl-multi-logs", vars, dry_run)

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


# ── MCP runtime checks ──

def ensure_mcp_runtimes(vars, dry_run=False):
    """Check that tools required by configured MCP servers are available.

    Warns if missing and optionally installs via Homebrew when apps phase is active.
    """
    deps = []

    if not shutil.which("npx"):
        deps.append(("npx (Node.js)", "brew install node", "node"))
    if not shutil.which("uvx"):
        deps.append(("uvx", "brew install uv", "uv"))

    if not deps:
        return

    step("MCP runtime dependencies")

    # serena is optional — just warn
    if not shutil.which("serena"):
        warn("serena binary not found — serena MCP will be disabled")

    for label, brew_cmd, brew_pkg in deps:
        if dry_run:
            info(f"[dry-run] Would install: {brew_pkg} via Homebrew")
            continue
        r = subprocess.run(["brew", "list", brew_pkg], capture_output=True, text=True)
        if r.returncode == 0:
            warn(f"{label} is installed but not in PATH — may need shell restart")
            continue
        info(f"Installing {brew_pkg} via Homebrew...")
        subprocess.run(brew_cmd.split(), capture_output=True)
        if shutil.which(brew_pkg.replace("brew install ", "")):
            info(f"  ✓ {label} installed")
        else:
            warn(f"{label} install may have failed — install manually: {brew_cmd}")


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
        for f in sorted(src_dir.rglob("*")):
            if f.is_file():
                rel = f.relative_to(src_dir)
                dst = opencode_dir / rel
                print(f"  [dry-run] {dst}")
        return None

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

    # Record bootstrap version
    ver_file = opencode_dir / ".bootstrap-version"
    ver_file.write_text(BOOTSTRAP_VERSION + "\n")

    info("OpenCode config deployed")
    return backup


# ── Shell config ──

def deploy_shell_config(vars, dry_run=False):
    """Deploy shell config files."""
    step("Shell configuration")

    src_dir = TEMPLATES_DIR / "shell"
    dst_root = Path.home() / ".zsh"

    if not src_dir.exists():
        info("No shell templates found — skipping")
        return

    deploy_tree(src_dir, dst_root, vars, dry_run=dry_run)

    # Add sourcing block to .zshrc
    zshrc = Path.home() / ".zshrc"
    if dry_run:
        if zshrc.exists():
            print(f"  [dry-run] Would add sourcing block to {zshrc}")
        else:
            print(f"  [dry-run] Would create {zshrc} with sourcing block")
        return

    if not zshrc.exists() or ZSH_SOURCING_HEADER not in zshrc.read_text():
        block = (
            f"\n{ZSH_SOURCING_HEADER}\n"
            f'for f in "$HOME/.zsh/aliases"/*.zsh; do [[ -f "$f" ]] && source "$f"; done\n'
            f'for f in "$HOME/.zsh/functions"/*.zsh; do [[ -f "$f" ]] && source "$f"; done\n'
            f'[[ -f "$HOME/.zsh/exports.zsh" ]] && source "$HOME/.zsh/exports.zsh"\n'
            f'[[ -f "$HOME/.zsh/lazyload.zsh" ]] && source "$HOME/.zsh/lazyload.zsh"\n'
            f"{ZSH_SOURCING_FOOTER}\n"
        )
        content = zshrc.read_text() if zshrc.exists() else ""
        new_content = content + block
        with zshrc.open("w") as f:
            f.write(new_content)
        info(f"Added sourcing block to {zshrc}")


APP_CONFIG_MAP = {
    "zed":     (".config/zed",         TEMPLATES_DIR / "zed"),
    "ghostty": (".config/ghostty",     TEMPLATES_DIR / "ghostty"),
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


def print_summary(vars, backup=None, args=None):
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
    for key in ("PROJECTS_DIR", "METABASE_URL"):
        val = vars.get(key, "")
        if val:
            print(f"    {key}={val}")
    if backup:
        print(f"\n  Previous config backed up to:")
        print(f"    {backup}")
    print(f"\n  Docs: https://github.com/vianhanif/opencode-environment-bootstrap")


# ── Snapshot ──

SNAPSHOT_DIRS = [
    Path.home() / ".zsh",
    Path.home() / ".config" / "zed",
]

SNAPSHOT_EXCLUDE_PATTERNS = [
    "prompts/",
    "__pycache__",
    "*.pyc",
]


def _snapshot_should_include(path):
    rel = str(path.relative_to(Path.home())) if path.is_relative_to(Path.home()) else path.name
    for pat in SNAPSHOT_EXCLUDE_PATTERNS:
        if pat.endswith("/"):
            if rel.startswith(pat) or f"/{pat}" in rel:
                return False
        elif path.match(pat):
            return False
    return True


def collect_snapshot_files(vars):
    """Find all managed local files (not runtime state) for snapshot."""
    files = []
    for local_dir in SNAPSHOT_DIRS:
        if not local_dir.is_dir():
            continue
        for f in sorted(local_dir.rglob("*")):
            if not f.is_file():
                continue
            if _snapshot_should_include(f):
                files.append(f)
    return files


def create_snapshot(path, vars, dry_run=False):
    """Create a ZIP snapshot of managed config files."""
    files = collect_snapshot_files(vars)
    if not files:
        info("No managed config files found to snapshot")
        return

    step(f"Snapshot → {path}")
    if dry_run:
        for f in files:
            rel = f.relative_to(Path.home())
            print(f"  [dry-run] {rel}")
        return

    n = len(files)
    total = sum(f.stat().st_size for f in files)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            arcname = str(f.relative_to(Path.home()))
            zf.write(f, arcname)

    info(f"Snapshot saved: {path} ({n} files, {_fmt_size(total)})")


def restore_snapshot(path, dry_run=False):
    """Restore snapshot ZIP contents to home directory."""
    step("Restoring snapshot")
    snap = Path(path)
    if not snap.exists():
        warn(f"Snapshot not found: {path}")
        return

    if dry_run:
        with zipfile.ZipFile(snap) as zf:
            for name in zf.namelist():
                print(f"  [dry-run] ~/{name}")
        return

    count = 0
    with zipfile.ZipFile(snap) as zf:
        for name in zf.namelist():
            if name.endswith("/") or name.startswith("__MACOSX"):
                continue
            basename = name.rstrip("/").split("/")[-1]
            if basename.startswith("."):
                continue
            dst = Path.home() / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(zf.read(name))
            info(f"  {dst}")
            count += 1

    info(f"Snapshot restored: {count} files")


def _fmt_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# ── Clean ──

CLEAN_PATHS = [
    Path.home() / ".config" / "opencode",
    Path.home() / ".zsh",
    Path.home() / ".config" / "zed" / "settings.json",
    Path.home() / ".config" / "zed" / "keymap.json",
    Path.home() / ".config" / "zed" / "rules",
    Path.home() / ".config" / "ghostty" / "config",
    Path.home() / "Library" / "Application Support" / "Bruno",
    Path("/usr/local/bin/git-review-cli"),
    Path("/usr/local/lib/node_modules/git-review-cli"),
    Path.home() / ".local" / "bin" / "git-review-cli",
    Path.home() / ".local" / "bin" / "kubectl-multi-logs",
    Path.home() / ".local" / "bin" / "opencode-session",
    Path.home() / ".local" / "bin" / "rtk",
    Path.home() / ".config" / "rtk",
]


def _remove_sourcing_block(zshrc):
    """Remove the opencode-bootstrap sourcing block from .zshrc."""
    if not zshrc.exists():
        return False
    text = zshrc.read_text()
    if ZSH_SOURCING_HEADER not in text:
        return False
    start = text.index(ZSH_SOURCING_HEADER)
    end = text.index(ZSH_SOURCING_FOOTER) + len(ZSH_SOURCING_FOOTER) + 1
    new_text = text[:start].rstrip() + "\n" + text[end:]
    zshrc.write_text(new_text)
    return True


def clean_machine(vars=None, dry_run=False):
    """Remove managed configs, dotfiles, and extra tools — leaves apps installed."""
    step("Cleaning machine to fresh state")

    # Scan what can be cleaned
    zshrc_block = False
    zshrc = Path.home() / ".zshrc"
    if zshrc.exists() and ZSH_SOURCING_HEADER in zshrc.read_text():
        zshrc_block = True

    projects_dir = Path(vars.get("PROJECTS_DIR", "~/projects")).expanduser() if vars else Path("~/projects").expanduser()
    collections_dir = projects_dir / "bruno" / "collections"
    session_dir = projects_dir / "codes" / "opencode-session-viewer"

    to_remove = []
    for p in CLEAN_PATHS:
        if p.exists():
            to_remove.append(p)
    if zshrc_block:
        to_remove.append(zshrc)
    if collections_dir.exists():
        to_remove.append(collections_dir)
    if session_dir.exists():
        to_remove.append(session_dir)

    if not to_remove:
        info("Nothing to clean")
        return True

    # Print what will be removed
    print()
    longest = max(len(str(p)) for p in to_remove)
    print(f"  {'Config / extras'.ljust(longest)}  Type")
    print(f"  {'─' * longest}  ────")
    for p in to_remove:
        kind = "config dir" if p.is_dir() and not p.is_symlink() else "symlink" if p.is_symlink() else "file" if p.is_file() else "dir"
        print(f"  {str(p).ljust(longest)}  {kind}")
    print()

    if dry_run:
        print(f"  {len(to_remove)} items would be removed")
        return True

    answer = _prompt_input("  Proceed? [y/N] ").lower()
    if answer != "y":
        info("Aborted")
        return False

    # Do the cleaning
    removed = 0
    for p in to_remove:
        if p == zshrc:
            if _remove_sourcing_block(zshrc):
                info(f"Removed sourcing block from {zshrc}")
                removed += 1
            continue
        if p in (collections_dir, session_dir):
            shutil.rmtree(p)
            info(f"Removed: {p}")
            removed += 1
            continue
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
        else:
            p.unlink()
        info(f"Removed: {p}")
        removed += 1

    info(f"Cleaned {removed} paths")
    return True


# ── Verification ──


def _verify_file(path, label):
    """Check a single file exists and return True if OK."""
    if path.exists():
        info(f"  ✓ {label}: {path}")
        return True
    warn(f"  ✗ {label}: {path} not found")
    return False


def _verify_binary(name):
    """Check a binary is in PATH."""
    ok = shutil.which(name) is not None
    if ok:
        info(f"  ✓ Binary {name}")
    else:
        warn(f"  ✗ Binary {name} — not in PATH")
    return ok


def _verify_zsh_sourcing():
    """Check .zshrc has the bootstrap sourcing block."""
    zshrc = Path.home() / ".zshrc"
    if not zshrc.exists():
        warn(f"  ✗ .zshrc not found")
        return False
    text = zshrc.read_text()
    if ZSH_SOURCING_HEADER in text:
        info(f"  ✓ Shell sourcing block in .zshrc")
        return True
    warn(f"  ✗ Shell sourcing block missing from .zshrc")
    return False


def verify_deployment(vars, dry_run=False):
    """Verify that key files were deployed correctly."""
    step("Verification")

    info(f"Bootstrap version: {BOOTSTRAP_VERSION}")

    # File existence
    info("Files:")
    checks = [
        (Path.home() / ".config" / "opencode" / "opencode.json", "OpenCode config"),
        (Path.home() / ".config" / "opencode" / "AGENTS.md", "OpenCode AGENTS.md"),
        (Path.home() / ".config" / "opencode" / "skills" / "planner" / "SKILL.md", "Planner skill"),
        (Path.home() / ".zsh" / "aliases" / "git.zsh", "Shell aliases"),
        (Path.home() / ".zsh" / "lazyload.zsh", "Lazyload"),
    ]
    files_ok = all(_verify_file(p, l) for p, l in checks)

    # Binaries
    info("\nBinaries:")
    binaries = [
        "opencode",
        "rtk",
        "glab",
        "git-review-cli",
        "opencode-session",
        "multilogs",
        "kubectl",
    ]
    bins_ok = all(_verify_binary(b) for b in binaries)

    # Shell
    info("\nShell config:")
    shell_ok = _verify_zsh_sourcing()

    all_ok = all([files_ok, bins_ok, shell_ok])
    print()
    if all_ok:
        info("All checks passed")
    else:
        warn("Some checks failed — see above")


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
    parser.add_argument("--snapshot", metavar="FILE", help="Create ZIP snapshot of custom files and exit")
    parser.add_argument("--restore-snapshot", metavar="FILE", help="Restore snapshot after deployment")
    parser.add_argument("--clean", action="store_true", help="Remove managed configs before install")
    parser.add_argument("--verify", action="store_true", help="Run comprehensive installation verification")
    parser.add_argument("--version", action="store_true", help="Print bootstrap version and exit")
    args = parser.parse_args()

    if args.version:
        local_ver = None
        local_file = Path.home() / ".config" / "opencode" / ".bootstrap-version"
        if local_file.exists():
            local_ver = local_file.read_text().strip()

        remote_ver = None
        try:
            import urllib.request
            req = urllib.request.Request(
                "https://raw.githubusercontent.com/vianhanif/opencode-environment-bootstrap/main/VERSION",
                headers={"User-Agent": "opencode-bootstrap"},
            )
            resp = urllib.request.urlopen(req, timeout=5)
            remote_ver = resp.read().decode().strip()
        except Exception:
            pass

        if local_ver:
            print(f"  Installed: {local_ver}")
        else:
            print(f"  Installed: (none)")

        if remote_ver:
            print(f"  Latest:    {remote_ver}")
            if local_ver == remote_ver:
                print(f"  ✓ Up to date")
            elif local_ver:
                print(f"  ⚠ Update available: {local_ver} → {remote_ver}")
            else:
                print(f"  → Run installer to deploy")
        else:
            print(f"  Latest:    (could not check)")

        return

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

    # Standalone verify mode: run checks and exit (verify is always read-only)
    if args.verify and not args.clean and not args.snapshot and not args.restore_snapshot:
        verify_deployment(vars, dry_run=False)
        return

    # Snapshot mode: create and exit
    if args.snapshot:
        create_snapshot(args.snapshot, vars, args.dry_run)
        if not args.clean and not args.restore_snapshot:
            return

    # Clean: wipe managed configs before install
    if args.clean:
        if not clean_machine(vars, args.dry_run):
            return

    # Phase 1: Install apps (optional)
    if not args.skip_apps:
        ensure_apps(vars, args.dry_run)

    # MCP runtime checks (npx, uvx, serena) — runs after apps so brew is ready
    ensure_mcp_runtimes(vars, args.dry_run)

    # Phase 2: Install opencode CLI
    backup = None
    if not args.skip_opencode:
        ensure_opencode(vars, args.dry_run)
        backup = deploy_opencode_config(vars, args.dry_run)

    # Phase 3: Shell config
    if not args.skip_shell:
        deploy_shell_config(vars, args.dry_run)

    # Phase 4: Dev tools
    if not args.skip_tools:
        ensure_rtk(vars, args.dry_run)
        ensure_glab(vars, args.dry_run)
        ensure_git_review_cli(vars, args.dry_run)
        ensure_opencode_session(vars, args.dry_run)
        ensure_kubectl_multi_logs(vars, args.dry_run)
        ensure_bruno_collections(vars, args.dry_run)

    # Phase 5: RTK OpenCode integration (needs rtk binary + opencode config deployed)
    if not args.skip_tools and not args.skip_opencode:
        _init_rtk_opencode(vars, args.dry_run)

    # Phase 6: App configs (was Phase 5)
    if not args.skip_app_configs:
        deploy_app_configs(vars, args.dry_run)

    # Phase 7: Restore snapshot (after all deployments)
    if args.restore_snapshot:
        restore_snapshot(args.restore_snapshot, args.dry_run)

    # Phase 8: Verify
    verify_deployment(vars, args.dry_run)

    # Summary
    if not args.dry_run:
        print_summary(vars, backup, args)


if __name__ == "__main__":
    main()
