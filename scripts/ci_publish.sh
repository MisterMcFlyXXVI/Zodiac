#!/usr/bin/env bash
# Used by the GitHub workflow: publish results/ to the zbot-results branch.
# Called every 10 minutes during a run (so the dashboard shows progress) and once at the
# end. Safe to call when nothing changed.
#
# The branch holds ONLY the results (a fresh single commit each time, force-pushed):
#   * no workflow files, so GitHub never refuses the push for touching .github/workflows
#     (the Actions token isn't allowed to change workflows);
#   * a vercel.json that switches Vercel deployments off for this branch, so results
#     pushes don't trigger website builds.
# The ledger itself is cumulative, so no history is lost by replacing the commit.
set -u
cd "$(dirname "$0")/.."

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/web"
cfg='{ "git": { "deploymentEnabled": false } }'
echo "$cfg" > "$tmp/vercel.json"        # projects built from the repo root
echo "$cfg" > "$tmp/web/vercel.json"    # projects with Root Directory = web
cat > "$tmp/README.md" <<'EOF'
Results published by the zbot workflow. Overwritten on every publish; edit nothing here.
EOF

export GIT_INDEX_FILE="$tmp/index"
git read-tree --empty
git add results/
for f in vercel.json web/vercel.json README.md; do
  blob=$(git hash-object -w "$tmp/$f")
  git update-index --add --cacheinfo 100644 "$blob" "$f"
done
tree=$(git write-tree)
unset GIT_INDEX_FILE

commit=$(git -c user.name=zbot -c user.email=zbot@users.noreply.github.com \
  commit-tree "$tree" -m "zbot results $(date -u +%FT%H:%M)")
for i in 1 2 3; do
  git push -q --force origin "$commit:refs/heads/zbot-results" && exit 0
  sleep $((5 * i))
done
echo "push to zbot-results failed" >&2
exit 1
