#!/usr/bin/env bash
set -euo pipefail

# ── GitHub CLI SSO Auth ──────────────────────────────────────────────
#
# Authentication methods (in order of preference):
#   1. GITHUB_TOKEN env var (PAT/SSO token)
#   2. SSH key mounted at ~/.ssh/id_ed25519
#
# To get a token that works with SSO:
#   1. gh auth login
#      (this triggers the browser-based SSO flow)
#   2. Copy the token and pass it as GITHUB_TOKEN env var
#   3. Or use a GitHub App token (ghs_xxxx) that has repo scope
#
# Usage:
#   docker run -e GITHUB_TOKEN=ghp_xxxx your-image
#   docker run -e GITHUB_TOKEN=ghs_xxxx your-image
#   docker run -v ~/.ssh/id_ed25519:/root/.ssh/id_ed25519:ro your-image

# ── Git config defaults ──────────────────────────────────────────────
git config --global user.email "${GIT_USER_EMAIL:-agent@pi.dev}"
git config --global user.name "${GIT_USER_NAME:-Agent}"

# ── Method 1: gh auth login (GITHUB_TOKEN) ──────────────────────────
if [ -n "${GITHUB_TOKEN:-}" ]; then
  # Create directory for gh credential store if it doesn't exist
  mkdir -p ~/.local/share/gh
  mkdir -p ~/.config/gh

  # Auth with gh, which handles SSO automatically
  echo "$GITHUB_TOKEN" | gh auth login --with-token --hostname github.com 2>/dev/null || {
    echo "⚠️  Failed to authenticate with GitHub token."
    echo "   Make sure the token has 'repo' scope and has accepted SSO."
    exit 1
  }

  # Configure git to use gh credentials
  git config --global credential.https://github.com.host github.com
  git config --global credential.helper store

  # Verify
  if gh auth status --hostname github.com 2>/dev/null | grep -q "Logged in"; then
    echo "✅ gh authenticated (SSO token accepted)"
  fi
fi

# ── Method 2: SSH key (fallback) ────────────────────────────────────
if [ -f ~/.ssh/id_ed25519 ] && [ -n "${SSH_AUTH_SOCK:-}" ]; then
  echo "✅ SSH key found, using SSH for git operations"
  git config --global url."ssh://git@github.com/".insteadof "https://github.com/"
fi

# ── Start the main command ──────────────────────────────────────────
exec "$@"
