#!/usr/bin/env bash
# Merges a NetBox release into Lanvex Core.
#
#   lanvex/scripts/merge-upstream.sh v4.7.6
#
# Fetches NetBox's tags, merges the release without committing, records it in lanvex/UPSTREAM and
# checks FORK.md. On conflicts it stops and lists them; resolve them, then run it again with --continue.
# It never pushes and never builds; run lanvex/scripts/test.sh afterwards.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

usage() { echo "usage: $0 <NetBox release tag, e.g. v4.7.6> [--allow-prerelease] | --continue" >&2; exit 2; }
[ $# -ge 1 ] || usage

finish() {
  local tag; tag=$(cat .git/LANVEX_MERGE_TAG)
  echo "$tag" > lanvex/UPSTREAM
  git add lanvex/UPSTREAM
  lanvex/scripts/check-fork.sh
  git commit --no-edit -q
  rm -f .git/LANVEX_MERGE_TAG
  echo
  echo "Merged NetBox $tag. Next: lanvex/scripts/test.sh, then build and test the image."
  echo "If NetBox added migrations, the next start of Lanvex Core applies them."
}

if [ "$1" = "--continue" ]; then
  [ -f .git/LANVEX_MERGE_TAG ] || { echo "No merge in progress." >&2; exit 1; }
  if git diff --name-only --diff-filter=U | grep -q .; then
    echo "Still unresolved:" >&2; git diff --name-only --diff-filter=U >&2; exit 1
  fi
  finish; exit 0
fi

tag=$1
current=$(cat lanvex/UPSTREAM)
[[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-.+)?$ ]] || usage
if [[ "$tag" == *-* && "${2:-}" != "--allow-prerelease" ]]; then
  echo "$tag is a pre-release. Pass --allow-prerelease to merge it anyway." >&2; exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
  echo "The working tree has uncommitted changes. Commit or stash them first." >&2; exit 1
fi
git fetch --quiet upstream --tags
git rev-parse -q --verify "refs/tags/$tag" >/dev/null || { echo "NetBox has no release $tag." >&2; exit 1; }
if ! git merge-base --is-ancestor "$current" "$tag"; then
  echo "$tag does not contain $current (the current base). Refusing to go backwards." >&2; exit 1
fi

echo "$tag" > .git/LANVEX_MERGE_TAG
echo "Merging NetBox $tag into Lanvex Core (currently on $current):"
git log --oneline "$current..$tag" | wc -l | xargs echo "  NetBox commits:"
git diff --name-only --diff-filter=A "$current" "$tag" -- '*/migrations/*' | wc -l | xargs echo "  new migrations:"
if ! git merge --no-ff --no-commit -m "Merge NetBox $tag into Lanvex Core" "$tag"; then
  echo
  echo "Conflicts to resolve (FORK.md says why each of our changes exists):"
  git diff --name-only --diff-filter=U | sed 's/^/  /'
  echo "Resolve them, git add the files, then: $0 --continue"
  exit 1
fi
finish
