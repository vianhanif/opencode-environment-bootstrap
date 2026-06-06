# =========================================================
# TOOL FUNCTIONS
# =========================================================
# Requires: https://github.com/vianhanif/kubectl-multi-logs

multilogs() {
  local tool
  if command -v kubectl-multi-logs &>/dev/null; then
    tool="kubectl-multi-logs"
  elif [[ -f "$OPCODE_PROJECTS_DIR/codes/kubectl-multi-logs/kubectl-multi-logs" ]]; then
    tool="$OPCODE_PROJECTS_DIR/codes/kubectl-multi-logs/kubectl-multi-logs"
  else
    echo "Error: kubectl-multi-logs not found. Install from:"
    echo "  https://github.com/vianhanif/kubectl-multi-logs"
    return 1
  fi
  "$tool" "$@"
}
