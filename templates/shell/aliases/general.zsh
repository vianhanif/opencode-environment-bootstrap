# =========================================================
# GENERAL ALIASES
# =========================================================

# Keep the Mac awake (display)
alias keep-awake="caffeinate -d"

# Print human-readable size of files/dirs in current folder
alias check-size="du -sh *"

# Local services (Homebrew)
alias svc="brew services list"

# Kubernetes helpers
alias pod-app-list="kubectl get pods -o jsonpath='{.items[*].metadata.labels.app}' | tr ' ' '\n' | sort | uniq"
