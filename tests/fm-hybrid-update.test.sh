#!/usr/bin/env bash
# Tests for bin/fm-hybrid-update.sh: refresh both source refs without changing
# the checked-out hybrid branch, and report the source work still to adapt.
set -u

# shellcheck source=tests/lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

UPDATE="$ROOT/bin/fm-hybrid-update.sh"
fm_git_identity fmtest fmtest@example.com
TMP_ROOT=$(fm_test_tmproot fm-hybrid-update-tests)

new_source() {
  local seed=$1 bare=$2 file=$3 content=$4
  mkdir -p "$(dirname "$file")" "$seed" "$bare"
  git -C "$seed" init -q -b main
  printf '%s\n' "$content" > "$file"
  git -C "$seed" add -A
  git -C "$seed" commit -qm initial
  git init -q --bare "$bare"
  git -C "$seed" remote add origin "file://$bare"
  git -C "$seed" push -q origin main
  git -C "$bare" symbolic-ref HEAD refs/heads/main
}

new_world() {
  local w="$TMP_ROOT/$1"
  mkdir -p "$w"
  new_source "$w/firstmate-seed" "$w/firstmate.git" \
    "$w/firstmate-seed/README.md" firstmate
  new_source "$w/pstack-seed" "$w/pstack.git" \
    "$w/pstack-seed/pstack/skills/poteto-mode/SKILL.md" pstack
  git clone -q "$w/firstmate.git" "$w/hybrid"
  git -C "$w/hybrid" remote set-head origin main >/dev/null 2>&1 || true
  printf '%s\n' "$w"
}

run_update() {
  local w=$1 firstmate_url pstack_url
  firstmate_url="file://$w/firstmate.git"
  pstack_url="file://$w/pstack.git"
  FM_ROOT_OVERRIDE="$w/hybrid" \
    FM_HYBRID_FIRSTMATE_URL="$firstmate_url" \
    FM_HYBRID_PSTACK_URL="$pstack_url" \
    "$UPDATE" 2>&1
}

test_refreshes_sources_and_preserves_hybrid() {
  local w out before firstmate_head pstack_head firstmate_date pstack_date start end checked
  w=$(new_world refresh)
  out=$(run_update "$w") || fail "initial source refresh failed"
  assert_contains "$out" 'upstream remote: configured' 'Firstmate remote was configured'
  assert_contains "$out" 'pstack remote: configured' 'pstack remote was configured'
  assert_contains "$out" 'Firstmate source: initialized' 'Firstmate source was initialized'
  assert_contains "$out" 'pstack source: initialized' 'pstack source was initialized'
  assert_contains "$out" 'hybrid Firstmate pending: 0 commit(s)' 'hybrid starts current'

  before=$(git -C "$w/hybrid" rev-parse HEAD)
  printf 'firstmate update\n' >> "$w/firstmate-seed/README.md"
  git -C "$w/firstmate-seed" add README.md
  git -C "$w/firstmate-seed" commit -qm firstmate-update
  git -C "$w/firstmate-seed" push -q origin main
  printf 'pstack update\n' >> "$w/pstack-seed/pstack/skills/poteto-mode/SKILL.md"
  git -C "$w/pstack-seed" add pstack/skills/poteto-mode/SKILL.md
  git -C "$w/pstack-seed" commit -qm pstack-update
  git -C "$w/pstack-seed" push -q origin main

  start=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  out=$(run_update "$w") || fail "source update failed"
  end=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  firstmate_head=$(git -C "$w/firstmate-seed" rev-parse HEAD)
  pstack_head=$(git -C "$w/pstack-seed" rev-parse HEAD)
  firstmate_date=$(git -C "$w/firstmate-seed" show -s --format=%cI HEAD)
  pstack_date=$(git -C "$w/pstack-seed" show -s --format=%cI HEAD)
  assert_contains "$out" "Firstmate snapshot: $firstmate_head $firstmate_date" 'full Firstmate revision and date are reproducible'
  assert_contains "$out" "pstack snapshot: $pstack_head $pstack_date" 'full plugins revision and date are reproducible'
  assert_contains "$out" "Firstmate origin: file://$w/firstmate.git refs/heads/main" 'Firstmate source identity is explicit'
  assert_contains "$out" "pstack origin: file://$w/pstack.git refs/heads/main" 'pstack source identity is explicit'
  assert_contains "$out" "pstack tree: $(git -C "$w/pstack-seed" rev-parse HEAD:pstack)" 'pstack subtree is distinguished from the plugins repository'
  for checked in $(printf '%s\n' "$out" | awk '$2 == "checked-at:" { print $3 }'); do
    [[ "$checked" < "$start" || "$checked" > "$end" ]] && fail 'snapshot timestamp is outside the actual observation window'
  done
  [ "$(printf '%s\n' "$out" | grep -c ' checked-at: ')" -eq 2 ] || fail 'each fetched source needs a timestamp'
  assert_contains "$out" 'Firstmate source: updated' 'Firstmate source update was reported'
  assert_contains "$out" 'pstack source: updated' 'pstack source update was reported'
  assert_contains "$out" 'pstack relevant updates: 1' 'pstack path update was identified'
  assert_contains "$out" 'pstack-update' 'pstack update subject was reported'
  assert_contains "$out" 'hybrid Firstmate pending: 1 commit(s)' 'unapplied Firstmate work was reported'
  assert_contains "$out" 'next: review listed source changes' 'adaptation remains explicit'
  [ "$(git -C "$w/hybrid" rev-parse HEAD)" = "$before" ] \
    || fail 'source refresh changed the hybrid branch'
  [ -z "$(git -C "$w/hybrid" status --porcelain)" ] \
    || fail 'source refresh changed hybrid working files'
  # A repeat still emits the full receipt, but never overwrites local work.
  printf 'local work\n' >> "$w/hybrid/README.md"
  printf 'untracked work\n' > "$w/hybrid/local.txt"
  out=$(run_update "$w") || fail 'repeat source inspection failed'
  assert_contains "$out" "Firstmate snapshot: $firstmate_head $firstmate_date" 'unchanged source still produces a receipt'
  [ "$(git -C "$w/hybrid" rev-parse HEAD)" = "$before" ] || fail 'repeat refresh moved HEAD'
  [ "$(git -C "$w/hybrid" branch --show-current)" = main ] || fail 'refresh switched branches'
  [ "$(git -C "$w/hybrid" diff --numstat README.md)" = $'1\t0\tREADME.md' ] || fail 'refresh changed local edits'
  [ "$(<"$w/hybrid/local.txt")" = 'untracked work' ] || fail 'refresh changed untracked work'
  pass 'fm-hybrid-update.sh: refreshes both sources and preserves the hybrid'
}

test_refuses_wrong_existing_remote() {
  local w other out rc
  w=$(new_world mismatch)
  run_update "$w" >/dev/null || fail 'initial source setup failed'
  other="$w/other.git"
  git init -q --bare "$other"
  set +e
  out=$(FM_ROOT_OVERRIDE="$w/hybrid" \
    FM_HYBRID_FIRSTMATE_URL="file://$w/firstmate.git" \
    FM_HYBRID_PSTACK_URL="file://$other" \
    "$UPDATE" 2>&1)
  rc=$?
  set -e
  [ "$rc" -eq 1 ] || fail 'wrong pstack remote was accepted'
  assert_contains "$out" 'pstack remote points to' 'wrong pstack remote was refused'
  pass 'fm-hybrid-update.sh: refuses to replace a configured source'
}

test_reports_completed_source_before_later_fetch_failure() {
  local w out rc
  w=$(new_world partial)
  run_update "$w" >/dev/null || fail 'initial source setup failed'
  printf 'firstmate update\n' >> "$w/firstmate-seed/README.md"
  git -C "$w/firstmate-seed" add README.md
  git -C "$w/firstmate-seed" commit -qm firstmate-update
  git -C "$w/firstmate-seed" push -q origin main
  mv "$w/pstack.git" "$w/pstack.git.unavailable"

  set +e
  out=$(run_update "$w")
  rc=$?
  set -e
  [ "$rc" -eq 1 ] || fail 'later source fetch failure was not reported'
  case "$out" in
    *'Firstmate source: updated'*'error: could not fetch pstack/main'*) ;;
    *) fail 'completed Firstmate update was not reported before pstack failure' ;;
  esac
  pass 'fm-hybrid-update.sh: reports completed source before later fetch failure'
}

test_refreshes_sources_and_preserves_hybrid
test_refuses_wrong_existing_remote
test_reports_completed_source_before_later_fetch_failure

echo '# all fm-hybrid-update tests passed'
