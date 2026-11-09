#!/usr/bin/env bash
set -euo pipefail

# ── GitHub CLI SSO Auth ──────────────────────────────────────────────
# Usage: docker run -e GITHUB_TOKEN=ghp_xxxx ...
#
# The token must be a PAT with "repo" scope that has accepted the
# organization's SSO. See:
#   https://github.com/cli/cli/blob/trunk/docs/cli gh auth login
#
# To get a token that works with SSO:
#   1. gh auth login --login-cli
#      (this triggers the browser-based SSO flow)
#   2. Copy the token and pass it as GITHUB_TOKEN env var
#   3. Or use a GitHub App token

if [ -n "${GITHUB_TOKEN:-}" ]; then
  # Auth with gh, which handles SSO automatically
  echo "$GITHUB_TOKEN" | gh auth login --with-token --hostname github.com 2>/dev/null || true

  # Configure git to use gh credentials
  git config --global credential.https://github.com.host github.com
  git config --global credential.helper store
  git config --global user.email "$(git config --global --get user.email || echo 'agent@pi.dev')"
  git config --global user.name "$(git config --global --get user.name || echo 'Agent')"

  # Verify
  gh auth status --hostname github.com 2>/dev/null || true
  echo "✅ gh authenticated (SSO token accepted)"
else
  echo "⚠️  GITHUB_TOKEN not set. Git push will fail unless SSH key is mounted."
fi

exec "$@"
