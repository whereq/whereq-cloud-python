#!/usr/bin/env bash
#
# release.sh — publish whereq.cloud to PyPI.
#
# This wraps the manual runbook in RELEASING.md into a single command:
#
#     ./release.sh 0.6.1 "the geography endpoints"
#     ./release.sh patch
#     ./release.sh minor --dry-run
#
# It bumps the version in pyproject.toml AND src/whereq_cloud/client.py,
# runs the tests, commits, pushes main, pushes the tag (the tag is what
# actually triggers the Release workflow), watches that run, and verifies
# the version on PyPI.
#
# Nothing is pushed until every check below has passed.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

PACKAGE="whereq.cloud"
PYPROJECT="pyproject.toml"
CLIENT_PY="src/whereq_cloud/client.py"
BRANCH="main"
POLL_ATTEMPTS=30

DRY_RUN=0
SUMMARY=""
VERSION=""

die()  { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }
info() { printf '\033[36m==>\033[0m %s\n' "$*"; }
ok()   { printf '\033[32m  ok\033[0m %s\n' "$*"; }

usage() {
  cat <<'USAGE'
usage: ./release.sh [version|bump] [summary] [--dry-run]

  version    explicit version, e.g. 0.6.1 (no "v" prefix)
  bump       patch | minor | major — computed from the current version
  summary    optional one-liner for the commit message
  --dry-run  run every check and the tests, print the plan, push nothing

examples:
  ./release.sh 0.6.1 "the geography endpoints"
  ./release.sh patch
  ./release.sh minor --dry-run
USAGE
}

# ---------------------------------------------------------------- arguments --

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run|-n) DRY_RUN=1; shift ;;
    --help|-h)   usage; exit 0 ;;
    --)          shift; break ;;
    -*)          die "unknown option: $1 (try --help)" ;;
    *)
      if [ -z "$VERSION" ]; then
        VERSION="$1"
      elif [ -z "$SUMMARY" ]; then
        SUMMARY="$1"
      else
        die "too many arguments"
      fi
      shift ;;
  esac
done

if [ -z "$VERSION" ]; then
  usage
  die "a version (or patch|minor|major) is required"
fi

# ------------------------------------------------------------------ helpers --

have() { command -v "$1" >/dev/null 2>&1; }

current_version() {
  python3 - "$PYPROJECT" <<'PY'
import re, sys, pathlib
text = pathlib.Path(sys.argv[1]).read_text()
m = re.search(r'(?m)^version = "([^"]+)"', text)
if not m:
    sys.exit("no version line found in pyproject.toml")
print(m.group(1))
PY
}

compute_bump() {
  python3 - "$1" "$2" <<'PY'
import re, sys
kind, cur = sys.argv[1], sys.argv[2]
m = re.match(r'^(\d+)\.(\d+)\.(\d+)$', cur)
if not m:
    sys.exit(f"cannot bump non-semver version {cur!r}")
major, minor, patch = (int(x) for x in m.groups())
if kind == "major":
    print(f"{major + 1}.0.0")
elif kind == "minor":
    print(f"{major}.{minor + 1}.0")
elif kind == "patch":
    print(f"{major}.{minor}.{patch + 1}")
else:
    sys.exit(f"unknown bump {kind!r} (use patch, minor or major)")
PY
}

# Does the tag exist locally or on the remote?
tag_exists() {
  git rev-parse -q --verify "refs/tags/$1" >/dev/null 2>&1 && return 0
  git ls-remote --exit-code --tags origin "refs/tags/$1" >/dev/null 2>&1 && return 0
  return 1
}

# Is the version already on PyPI? 0 = yes, 1 = no, 2 = could not tell.
pypi_has_version() {
  curl -sS -m 30 "https://pypi.org/pypi/${PACKAGE}/json" \
    | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(2)
sys.exit(0 if sys.argv[1] in data.get("releases", {}) else 1)
' "$1"
}

# Write the version into both files that carry it.
write_version() {
  python3 - "$VERSION" "$PYPROJECT" "$CLIENT_PY" <<'PY'
import re, sys, pathlib
version, pyproject, client_py = sys.argv[1], sys.argv[2], sys.argv[3]

p = pathlib.Path(pyproject)
text = p.read_text()
new, n = re.subn(r'(?m)^version = "[^"]+"', f'version = "{version}"', text, count=1)
if n != 1:
    sys.exit("could not find the version line in " + pyproject)
p.write_text(new)

c = pathlib.Path(client_py)
text = c.read_text()
new, n = re.subn(r'(?m)^__version__ = "[^"]+"', f'__version__ = "{version}"', text, count=1)
if n != 1:
    sys.exit("could not find __version__ in " + client_py)
c.write_text(new)
PY
}

# Run the tests the way CI does, without touching the user's environment:
# in the active virtualenv if there is one, otherwise in a throwaway venv.
run_tests() {
  local py tmp=""
  if [ -n "${VIRTUAL_ENV:-}" ]; then
    py="python3"
  else
    tmp="$(mktemp -d)"
    py="$tmp/venv/bin/python"
    python3 -m venv "$tmp/venv"
  fi
  "$py" -m pip install --quiet --upgrade pip
  "$py" -m pip install --quiet -e . pytest
  "$py" -m pytest -q
  [ -n "$tmp" ] && rm -rf "$tmp"
  return 0
}

# --------------------------------------------------------------- preflight --

for dep in git python3 curl gh; do
  have "$dep" || die "$dep is required but was not found on PATH"
done

git rev-parse --git-dir >/dev/null 2>&1 || die "not a git repository"

CURRENT="$(current_version)"
info "current version: $CURRENT"

case "$VERSION" in
  patch|minor|major) VERSION="$(compute_bump "$VERSION" "$CURRENT")" ;;
esac

if ! printf '%s' "$VERSION" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$'; then
  die "invalid version '$VERSION' (expected MAJOR.MINOR.PATCH)"
fi

if [ "$(git rev-parse --abbrev-ref HEAD)" != "$BRANCH" ]; then
  die "must be on the '$BRANCH' branch (currently on $(git rev-parse --abbrev-ref HEAD))"
fi

if [ -n "$(git status --porcelain)" ]; then
  die "the working tree is not clean — commit or stash first"
fi

info "checking the remote is in sync"
git fetch --quiet origin
if [ "$(git rev-parse HEAD)" != "$(git rev-parse "origin/$BRANCH")" ]; then
  AHEAD="$(git rev-list --count "origin/$BRANCH..HEAD")"
  BEHIND="$(git rev-list --count "HEAD..origin/$BRANCH")"
  if [ "$BEHIND" -gt 0 ]; then
    die "origin/$BRANCH has $BEHIND commit(s) you don't have — pull first"
  fi
  die "you have $AHEAD unpushed commit(s) — push them first"
fi

if tag_exists "v$VERSION"; then
  die "tag v$VERSION already exists"
fi

info "checking PyPI for $PACKAGE $VERSION"
set +e
pypi_has_version "$VERSION"
PYPY_RC=$?
set -e
case "$PYPY_RC" in
  0) die "$PACKAGE $VERSION is already on PyPI — pick a new version" ;;
  2) die "could not reach PyPI to check the version" ;;
  *) ok "$PACKAGE $VERSION is not on PyPI yet" ;;
esac

gh auth status >/dev/null 2>&1 || die "gh is not authenticated (run: gh auth login)"

# ------------------------------------------------------------------- bump ---

info "bumping $CURRENT -> $VERSION"
write_version

if ! git diff --quiet -- "$PYPROJECT" "$CLIENT_PY"; then
  git --no-pager diff -- "$PYPROJECT" "$CLIENT_PY"
fi

# ------------------------------------------------------------------ tests ---

info "running the tests"
run_tests
ok "tests passed"

# ----------------------------------------------------------------- commit ---

if [ "$DRY_RUN" -eq 1 ]; then
  echo
  info "dry run — nothing was committed or pushed. Planned steps:"
  printf '  1. commit   release: v%s\n' "$VERSION"
  printf '  2. push     origin %s\n' "$BRANCH"
  printf '  3. tag      v%s\n' "$VERSION"
  printf '  4. push     origin v%s   (triggers the Release workflow)\n' "$VERSION"
  printf '  5. watch    the Release run, then verify %s %s on PyPI\n' "$PACKAGE" "$VERSION"
  echo
  git checkout -- "$PYPROJECT" "$CLIENT_PY"
  ok "reverted the version bump; the tree is clean again"
  exit 0
fi

if [ -n "$SUMMARY" ]; then
  COMMIT_MSG="release: v$VERSION — $SUMMARY"
else
  COMMIT_MSG="release: v$VERSION"
fi

info "committing"
git add "$PYPROJECT" "$CLIENT_PY"
git commit -m "$COMMIT_MSG"
ok "$(git rev-parse --short HEAD) $COMMIT_MSG"

info "pushing $BRANCH"
git push origin "$BRANCH"
ok "origin/$BRANCH updated"

# -------------------------------------------------------------------- tag ---

info "tagging v$VERSION"
git tag "v$VERSION"
git push origin "v$VERSION"
ok "tag v$VERSION pushed — the Release workflow is on its way"

# --------------------------------------------------------------- watch/verify --

info "waiting for the Release workflow"
RUN_ID=""
for _ in $(seq 1 "$POLL_ATTEMPTS"); do
  RUN_ID="$(gh run list --workflow release.yml --limit 10 \
    --json databaseId,headBranch \
    --jq '.[] | select(.headBranch == "v'"$VERSION"'") | .databaseId' | head -n 1)"
  [ -n "$RUN_ID" ] && break
  sleep 3
done
[ -n "$RUN_ID" ] || die "the Release workflow for v$VERSION never appeared"

info "watching run $RUN_ID"
gh run watch "$RUN_ID" --exit-status
ok "Release workflow succeeded"

info "verifying $PACKAGE $VERSION on PyPI"
for _ in $(seq 1 20); do
  set +e
  pypi_has_version "$VERSION"
  RC=$?
  set -e
  [ "$RC" -eq 0 ] && break
  [ "$RC" -eq 2 ] && die "could not reach PyPI to verify the release"
  sleep 10
done
set +e
pypi_has_version "$VERSION"
RC=$?
set -e
[ "$RC" -eq 0 ] || die "$PACKAGE $VERSION is still not on PyPI"

ok "$PACKAGE $VERSION is live on PyPI"
info "https://pypi.org/project/${PACKAGE}/${VERSION}/"
