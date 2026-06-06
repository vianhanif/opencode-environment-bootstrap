# =========================================================
# GIT ALIASES
# =========================================================

# Delete local branches that match common ephemeral prefixes/patterns
# WARNING: permanently deletes local branches
alias clear-branch="git branch | grep 'B2C\|CLCI\|PROD\|hotfix\|update-\|fix-\|INT-\|PAS-\|cherry\|add-\|deploy' | xargs git branch -D"

# Pretty git log
alias glg="git log --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit"
alias git-lg=glg
