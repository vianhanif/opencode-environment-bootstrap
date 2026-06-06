# =========================================================
# LAZY LOADERS - Performance Optimization
# Tools are only initialized when first called
# =========================================================

# Generic lazy loader helper
lazy_load() {
  local cmd="$1"
  local init_cmd="$2"

  eval "
    function ${cmd}() {
      unset -f ${cmd}
      eval \"\$(${init_cmd})\"
      ${cmd} \"\$@\"
    }
  "
}

# AWS CLI - lazy loaded with completions
aws() {
  unset -f aws
  if command -v aws_completer >/dev/null 2>&1; then
    complete -C aws_completer aws
  fi
  command aws "$@"
}
