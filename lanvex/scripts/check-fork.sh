#!/usr/bin/env bash
# Lists every NetBox file this fork changes and fails if one is missing from FORK.md, or if a changed
# template or Python file lacks its "Modified for Lanvex Core" notice (Apache License 2.0, section 4b).
# Compares the working tree with the NetBox release in lanvex/UPSTREAM, so it also checks uncommitted work.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
base=$(cat lanvex/UPSTREAM)
status=0

mapfile -t changed < <(git diff --name-only --diff-filter=MDRT "$base" -- . ':!lanvex' ':!netbox/lanvex_core')
mapfile -t added < <(git diff --name-only --diff-filter=A "$base" -- . ':!lanvex' ':!netbox/lanvex_core'; \
                     git ls-files --others --exclude-standard -- . ':!lanvex' ':!netbox/lanvex_core')

echo "Lanvex Core on NetBox $base"
echo "NetBox files changed: ${#changed[@]}"
for f in "${changed[@]}"; do
  if ! grep -qF "\`$f\`" FORK.md; then
    echo "  MISSING FROM FORK.md: $f"; status=1
  fi
  case "$f" in
    *.html|*.py)
      if [ -f "$f" ] && ! grep -q "Modified for Lanvex Core" "$f"; then
        echo "  NO MODIFICATION NOTICE: $f"; status=1
      fi ;;
  esac
  echo "  $f"
done
echo "Files added outside lanvex/ and netbox/lanvex_core/: ${#added[@]}"
for f in "${added[@]}"; do
  if ! grep -qF "\`$f\`" FORK.md; then
    echo "  MISSING FROM FORK.md: $f"; status=1
  fi
  echo "  $f"
done
[ $status -eq 0 ] && echo "FORK.md lists every change." || echo "Update FORK.md (and add the notice) before committing."
exit $status
