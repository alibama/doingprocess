#!/usr/bin/env bash
# update.sh — keep the site up to date. One command to remember.
#
#   bash update.sh                 pull the latest from GitHub. This is what the server runs:
#                                  Apache serves /var/www/doingprocess/site directly, so a
#                                  pull is the whole deploy.
#   bash update.sh --push "msg"    from your own machine: rebuild the diagrams, commit
#                                  everything, push. (The server then pulls it.)
#   bash update.sh --build         rebuild the diagrams only (models/src → site/assets/diagrams)
#   bash update.sh --preview       serve site/ at http://localhost:8000
#
# Works in Git Bash on Windows, macOS and Linux. Pulling needs only git; the other modes
# need any Python 3.9+. Anything more the site ever needs on deploy goes in the pull step.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

say()  { printf '\033[1;32m> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m! %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31mx %s\033[0m\n' "$*" >&2; exit 1; }

# --- find a real Python 3 (the Windows Store stub and Inkscape's python both exist on some PCs)
find_python() {
  local c
  for c in python3 python py "${LOCALAPPDATA:-}/Programs/Python/Python312/python.exe" \
           "${LOCALAPPDATA:-}/Programs/Python/Python313/python.exe"; do
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
    warn "No Python 3.9+ found; skipping the diagram rebuild (the SVGs already in site/ stay as they are)."
  fi
}

pull() {
  local branch before after
  branch=$(git rev-parse --abbrev-ref HEAD)
  before=$(git rev-parse --short HEAD)
  if ! git pull --ff-only origin "$branch"; then
    die "Pull failed. If git mentions local changes, this checkout was edited in place; run  git status  and either commit them or  git checkout -- .  to discard, then try again."
  fi
  after=$(git rev-parse --short HEAD)
  if [ "$before" = "$after" ]; then
    say "Already up to date ($after)."
  else
    say "Updated $before -> $after:"
    git --no-pager log --oneline "$before..$after" | sed 's/^/    /'
  fi
  # Deploy steps that the site may need later go here (e.g. a rebuild, a cache clear).
}

case "${1:-}" in
  ""|--pull)
    pull ;;
  --build)
    build ;;
  --preview)
    build
    PY=$(find_python) || die "Python is needed to serve the preview."
    say "Serving site/ at http://localhost:8000  (Ctrl-C to stop)"
    cd site && exec "$PY" -m http.server 8000 ;;
  --push)
    shift
    MSG="${1:-Site update $(date '+%Y-%m-%d %H:%M')}"
    build
    git add -A
    if git diff --cached --quiet; then
      say "Nothing changed; nothing to commit."
    else
      git commit -q -m "$MSG" && say "Committed: $MSG"
    fi
    BRANCH=$(git rev-parse --abbrev-ref HEAD)
    say "Pushing $BRANCH to origin"
    git push origin "$BRANCH"
    say "Done. On the server:  cd /var/www/doingprocess && bash update.sh" ;;
  -h|--help)
    sed -n '2,13p' "$0" ;;
  *)
    die "Unknown option: $1  (try --help)" ;;
esac
