#!/usr/bin/env bash
# Used by the GitHub workflow: commit results/ and force-push them to the zbot-results
# branch. Called every 10 minutes during a run (so the dashboard shows progress) and once
# at the end. Safe to call when nothing changed.
set -u
cd "$(dirname "$0")/.."
git add results/ 2>/dev/null
git -c user.name=zbot -c user.email=zbot@users.noreply.github.com \
  commit -q -m "zbot results $(date -u +%FT%H:%M)" >/dev/null 2>&1 || true
for i in 1 2 3; do git push -q --force origin HEAD:zbot-results && exit 0; sleep $((5 * i)); done
echo "push to zbot-results failed" >&2
