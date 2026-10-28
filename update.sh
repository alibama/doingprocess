#!/usr/bin/env bash
# update.sh — rebuild the diagrams, commit everything, push. GitHub Pages redeploys on push.
#
#   ./update.sh                       commit with a timestamped message and push
#   ./update.sh "Fix the DMV step"    commit with your message and push
#   ./update.sh --preview             serve site/ at http://localhost:8000 (no commit)
#   ./update.sh --build               rebuild diagrams only (no commit)
#   ./update.sh --no-push "message"   commit but do not push
#
# Works in Git Bash on Windows, macOS and Linux. Needs git and any Python 3.9+.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

say()  { printf '\033[1;32m▸ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m! %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# --- find a real Python 3 (the Windows Store stub and Inkscape's python both exist on some PCs)
find_python() {
  local c
  for c in python3 python py "$LOCALAPPDATA/Programs/Python/Python312/python.exe" \
           "$LOCALAPPDATA/Programs/Python/Python313/python.exe"; do
    if [ -n "$c" ] && command -v "$c" >/dev/null 2>&1; then
      if "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
        echo "$c"; return 0
      fi
    fi
  done
  return 1
}

build() {
  if PY=$(find_python); then
    say "Rebuilding diagrams with $PY"
    "$PY" tools/build_diagrams.py
  else
    warn "No Python 3.9+ found; skipping the diagram rebuild (committing the SVGs as they are)."
  fi
}

case "${1:-}" in
  --preview)
    build
    PY=$(find_python) || die "Python is needed to serve the preview."
    say "Serving site/ at http://localhost:8000  (Ctrl-C to stop)"
    cd site && exec "$PY" -m http.server 8000 ;;
  --build)
    build; exit 0 ;;
esac

PUSH=1
if [ "${1:-}" = "--no-push" ]; then PUSH=0; shift; fi
MSG="${1:-Site update $(date '+%Y-%m-%d %H:%M')}"

build

git add -A
if git diff --cached --quiet; then
  say "Nothing changed; nothing to commit."
else
  git commit -q -m "$MSG" && say "Committed: $MSG"
fi

if [ "$PUSH" = 1 ]; then
  BRANCH=$(git rev-parse --abbrev-ref HEAD)
  say "Pushing $BRANCH to origin"
  git push origin "$BRANCH"
  say "Done. GitHub Pages will redeploy in a minute or two:"
  echo "    https://github.com/alibama/doingprocess/actions"
fi

# Optional: mirror to a classic web host as well. Set the target once, e.g.
#   export DOINGPROCESS_RSYNC_TARGET=user@host:/var/www/doingprocess.org/
if [ -n "${DOINGPROCESS_RSYNC_TARGET:-}" ] && command -v rsync >/dev/null 2>&1; then
  say "Mirroring site/ to $DOINGPROCESS_RSYNC_TARGET"
  rsync -az --delete site/ "$DOINGPROCESS_RSYNC_TARGET"
fi
