#!/usr/bin/env bash
# Refresh the Kun Chen Firstmate and Cursor pstack sources used by fmpstack.
#
# The command creates the `upstream` and `pstack` remotes when absent, refuses
# to overwrite either remote when it points somewhere else, and fetches each
# source's main branch.
#
# It reports Firstmate commits not yet contained by the current hybrid head and
# pstack commits that changed the pstack source tree since the previous fetch.
# It never merges, copies, resets, rebases, stashes, commits, or changes tracked
# files, so source adaptation remains an explicit reviewed change.
#
# The public source URLs can be replaced with FM_HYBRID_FIRSTMATE_URL and
# FM_HYBRID_PSTACK_URL for a mirror or a deterministic local test repository.
#
# Usage: fm-hybrid-update.sh [--help]
set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${FM_ROOT_OVERRIDE:-$(cd "$SCRIPT_DIR/.." && pwd)}"
FIRSTMATE_REMOTE=upstream
FIRSTMATE_BRANCH=main
FIRSTMATE_URL="${FM_HYBRID_FIRSTMATE_URL:-https://github.com/kunchenguid/firstmate}"
PSTACK_REMOTE=pstack
PSTACK_BRANCH=main
PSTACK_URL="${FM_HYBRID_PSTACK_URL:-https://github.com/cursor/plugins.git}"

usage() {
  printf '%s\n' \
    'usage: fm-hybrid-update.sh [--help]' \
    '' \
    'Refresh the Firstmate and pstack source refs and report adaptation work.' \
    'The command never changes the checked-out hybrid files or branch.' \
    '' \
    'Environment:' \
    '  FM_ROOT_OVERRIDE             fmpstack repository root' \
    '  FM_HYBRID_FIRSTMATE_URL      Firstmate source or mirror URL' \
    '  FM_HYBRID_PSTACK_URL         pstack source or mirror URL'
}

if [ "${1:-}" = --help ] || [ "${1:-}" = -h ]; then
  usage
  exit 0
fi
[ "$#" -eq 0 ] || { usage >&2; exit 2; }

git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  printf 'error: not a git repository: %s\n' "$ROOT" >&2
  exit 1
}

canonical_url() {
  local url=$1
  url=${url%/}
  url=${url%.git}
  printf '%s\n' "$url"
}

ensure_remote() {
  local name=$1 expected=$2 current
  if current=$(git -C "$ROOT" remote get-url "$name" 2>/dev/null); then
    if [ "$(canonical_url "$current")" != "$(canonical_url "$expected")" ]; then
      printf 'error: %s remote points to %s, expected %s\n' "$name" "$current" "$expected" >&2
      return 1
    fi
  else
    git -C "$ROOT" remote add "$name" "$expected"
    printf '%s remote: configured\n' "$name"
  fi
}

ref_sha() {
  local remote=$1 branch=$2
  git -C "$ROOT" rev-parse --verify --quiet "refs/remotes/$remote/$branch^{commit}" || true
}

print_source_changes() {
  local label=$1 old=$2 new=$3 path=$4 count
  if [ -z "$old" ]; then
    printf '%s source: initialized at %s\n' "$label" "${new:0:12}"
    return 0
  fi
  if [ "$old" = "$new" ]; then
    printf '%s source: current at %s\n' "$label" "${new:0:12}"
    return 0
  fi
  printf '%s source: updated %s..%s\n' "$label" "${old:0:12}" "${new:0:12}"
  count=$(git -C "$ROOT" rev-list --count "$old..$new" -- "$path")
  if [ "$count" -eq 0 ]; then
    printf '%s relevant updates: none\n' "$label"
    return 0
  fi
  printf '%s relevant updates: %s\n' "$label" "$count"
  git -C "$ROOT" log --format='  %h %s' "$old..$new" -- "$path" | head -20
  if [ "$count" -gt 20 ]; then
    printf '  ... %s more\n' "$((count - 20))"
  fi
}

ensure_remote "$FIRSTMATE_REMOTE" "$FIRSTMATE_URL"
ensure_remote "$PSTACK_REMOTE" "$PSTACK_URL"

old_firstmate=$(ref_sha "$FIRSTMATE_REMOTE" "$FIRSTMATE_BRANCH")
old_pstack=$(ref_sha "$PSTACK_REMOTE" "$PSTACK_BRANCH")

git -C "$ROOT" fetch --prune --quiet "$FIRSTMATE_REMOTE" "$FIRSTMATE_BRANCH" || {
  printf 'error: could not fetch %s/%s\n' "$FIRSTMATE_REMOTE" "$FIRSTMATE_BRANCH" >&2
  exit 1
}
git -C "$ROOT" fetch --prune --quiet "$PSTACK_REMOTE" "$PSTACK_BRANCH" || {
  printf 'error: could not fetch %s/%s\n' "$PSTACK_REMOTE" "$PSTACK_BRANCH" >&2
  exit 1
}

new_firstmate=$(ref_sha "$FIRSTMATE_REMOTE" "$FIRSTMATE_BRANCH")
new_pstack=$(ref_sha "$PSTACK_REMOTE" "$PSTACK_BRANCH")
[ -n "$new_firstmate" ] || { printf 'error: missing %s/%s after fetch\n' "$FIRSTMATE_REMOTE" "$FIRSTMATE_BRANCH" >&2; exit 1; }
[ -n "$new_pstack" ] || { printf 'error: missing %s/%s after fetch\n' "$PSTACK_REMOTE" "$PSTACK_BRANCH" >&2; exit 1; }

print_source_changes Firstmate "$old_firstmate" "$new_firstmate" .
print_source_changes pstack "$old_pstack" "$new_pstack" pstack

base=$(git -C "$ROOT" merge-base HEAD "$FIRSTMATE_REMOTE/$FIRSTMATE_BRANCH" 2>/dev/null || true)
if [ -z "$base" ]; then
  printf 'hybrid Firstmate status: unrelated histories\n'
else
  pending=$(git -C "$ROOT" rev-list --count "$base..$FIRSTMATE_REMOTE/$FIRSTMATE_BRANCH")
  printf 'hybrid Firstmate pending: %s commit(s)\n' "$pending"
  if [ "$pending" -gt 0 ]; then
    git -C "$ROOT" log --format='  %h %s' "$base..$FIRSTMATE_REMOTE/$FIRSTMATE_BRANCH" | head -20
    if [ "$pending" -gt 20 ]; then
      printf '  ... %s more\n' "$((pending - 20))"
    fi
  fi
fi

printf '%s\n' 'next: review listed source changes and adapt the hybrid through its normal PR path.'
