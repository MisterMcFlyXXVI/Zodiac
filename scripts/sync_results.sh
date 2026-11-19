#!/usr/bin/env bash
# Copy the live results (written by `ZBOT_RESULTS_DIR=live-results python -m zbot run`)
# into results/ and commit + push them in one step, so the tracked tree is never left
# half-written. Usage: scripts/sync_results.sh [branch]
set -u
cd "$(dirname "$0")/.."
branch="${1:-$(git rev-parse --abbrev-ref HEAD)}"
mkdir -p results
cp live-results/ledger.jsonl live-results/REPORT.md live-results/ALERTS.md results/ 2>/dev/null || exit 0
[ -z "$(git status --porcelain results)" ] && exit 0
git add results
git commit -q -m "zbot: results update ($(wc -l < results/ledger.jsonl) runs)" \
  -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_015y6depZ1JBrv2tKBjVv61r"
for i in 1 2 3 4; do git push -q origin "$branch" && exit 0; sleep $((2**i)); done
