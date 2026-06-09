#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/vianhanif/opencode-environment-bootstrap"
NAME="opencode-bootstrap"

# Handle --version without downloading
for arg in "$@"; do
  if [[ "$arg" == "--version" ]]; then
    local_file="$HOME/.config/opencode/.bootstrap-version"
    if [[ -f "$local_file" ]]; then
      local_ver=$(cat "$local_file")
      echo "  Installed: $local_ver"
    else
      echo "  Installed: (none)"
    fi
    remote=$(curl -fsSL "$REPO/raw/main/VERSION" 2>/dev/null || echo "")
    if [[ -n "$remote" ]]; then
      echo "  Latest:    $remote"
      if [[ "${local_ver:-}" == "$remote" ]]; then
        echo "  ✓ Up to date"
      elif [[ -n "${local_ver:-}" ]]; then
        echo "  ⚠ Update available: $local_ver → $remote"
      else
        echo "  → Run installer to deploy"
      fi
    else
      echo "  Latest:    (could not check)"
    fi
    exit 0
  fi
done

if ! command -v python3 &>/dev/null; then
  echo "Error: Python 3 is required. Install it first:"
  echo "  brew install python3"
  exit 1
fi

if command -v git &>/dev/null; then
  TEMP_DIR=$(mktemp -d)
  echo "Downloading $NAME..."
  git clone --depth 1 "$REPO" "$TEMP_DIR" 2>/dev/null || {
    rm -rf "$TEMP_DIR"
    echo "git clone failed. Trying tarball..."
    TEMP_DIR=$(mktemp -d)
    curl -fsSL "$REPO/archive/main.tar.gz" | tar xz -C "$TEMP_DIR" --strip=1 2>/dev/null || {
      echo "Error: Cannot download $NAME. Check your internet or install from:"
      echo "  $REPO"
      rm -rf "$TEMP_DIR"
      exit 1
    }
  }
else
  TEMP_DIR=$(mktemp -d)
  echo "Downloading $NAME..."
  curl -fsSL "$REPO/archive/main.tar.gz" | tar xz -C "$TEMP_DIR" --strip=1 2>/dev/null || {
    echo "Error: Cannot download $NAME. Check your internet or install from:"
    echo "  $REPO"
    rm -rf "$TEMP_DIR"
    exit 1
  }
fi

cd "$TEMP_DIR"
python3 installer.py "$@"
EXIT_CODE=$?

rm -rf "$TEMP_DIR"
exit $EXIT_CODE
