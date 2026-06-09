# =========================================================
# EXPORTS — Environment variables
# =========================================================
# Managed by opencode-bootstrap. Edit this file to add your
# API keys, secrets, and environment-specific variables.

# API Keys (set these via env vars or edit directly)
# export CONTEXT7_API_KEY="${CONTEXT7_API_KEY:-}"
# export FIRECRAWL_API_KEY="${FIRECRAWL_API_KEY:-}"

# OpenCode agent models (uncomment to override defaults)
# export MODEL_PLANNER="${MODEL_PLANNER:-opencode-go/deepseek-v4-pro}"
# export MODEL_CODER="${MODEL_CODER:-opencode-go/deepseek-v4-flash}"
# export MODEL_REVIEWER="${MODEL_REVIEWER:-opencode-go/deepseek-v4-pro}"
# export MODEL_TESTER="${MODEL_TESTER:-opencode-go/deepseek-v4-flash}"
# export MODEL_ANALYZER="${MODEL_ANALYZER:-opencode-go/deepseek-v4-pro}"
# export MODEL_BRAIN="${MODEL_BRAIN:-opencode-go/deepseek-v4-pro}"

# Go module private repos (set your org)
# export GOPRIVATE=gitlab.com/your-org

# Docker host (adjust for your Docker/Colima setup)
# export DOCKER_HOST=unix://$HOME/.colima/docker.sock

# Go binaries
export PATH="$PATH:$(go env GOPATH 2>/dev/null)/bin"

# OpenCode
export PATH="$HOME/.opencode/bin:$PATH"

# Local binaries
export PATH="$HOME/.local/bin:$PATH"
