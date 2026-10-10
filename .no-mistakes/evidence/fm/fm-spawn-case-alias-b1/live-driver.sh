#!/usr/bin/env bash
# usage: live.sh <firstmate-root> <label>
set -u
ROOT=$1; LABEL=$2
command -v jq >/dev/null || { echo no jq; exit 2; }
. "$ROOT/tests/herdr-test-safety.sh"
herdr_forget_inherited_pane
TMP_ROOT=$(mktemp -d "$(cd "${TMPDIR:-/tmp}" && pwd -P)/fm-live-case.XXXXXX")
SESSION="fm-lab-case-alias-$LABEL-$$"
export HERDR_SESSION="$SESSION" TREEHOUSE_ROOT="$TMP_ROOT/pool"
WT=
cleanup_all() {
  [ -n "$WT" ] && treehouse return --force "$WT" >/dev/null 2>&1
  herdr_safe_stop_and_delete "$SESSION"
  rm -rf "$TMP_ROOT"
}
trap cleanup_all EXIT
if [ -n "${SLOW_TREEHOUSE:-}" ]; then
  mkdir -p "$TMP_ROOT/shim"; REAL_TH=$(command -v treehouse)
  printf '#!/bin/sh\necho "shim: slow pool get ($*)" >> "%s/shim.log"\nsleep %s\nexec "%s" "$@"\n' "$TMP_ROOT" "$SLOW_TREEHOUSE" "$REAL_TH" > "$TMP_ROOT/shim/treehouse"
  chmod +x "$TMP_ROOT/shim/treehouse"; export PATH="$TMP_ROOT/shim:$PATH"
fi
fm_herdr_lab_prepare "$SESSION" || { echo "lab prepare failed"; exit 2; }
HOME_DIR="$TMP_ROOT/Home"
mkdir -p "$HOME_DIR/state" "$HOME_DIR/data/cs1" "$HOME_DIR/config" "$HOME_DIR/projects"
printf 'off\n' > "$HOME_DIR/config/herdr-presentation-spaces"
printf 'trivial brief\n' > "$HOME_DIR/data/cs1/brief.md"
PROJ="$HOME_DIR/projects/Dotfiles"
mkdir -p "$PROJ"; git -C "$PROJ" init -q -b main
printf '# scratch\n' > "$PROJ/README.md"; git -C "$PROJ" add README.md
git -C "$PROJ" -c user.name=t -c user.email=t@e.invalid commit -qm initial
git clone -q --bare "$PROJ" "$TMP_ROOT/origin.git"; git -C "$PROJ" remote add origin "file://$TMP_ROOT/origin.git"
git -C "$PROJ" fetch -q origin
if [ -n "${SLOW_CHECKOUT:-}" ]; then
  printf '#!/bin/sh\necho "post-checkout slow hook in $(pwd -P)" >> "%s/hook.log"\nsleep %s\n' "$TMP_ROOT" "$SLOW_CHECKOUT" > "$PROJ/.git/hooks/post-checkout"
  chmod +x "$PROJ/.git/hooks/post-checkout"
fi
ALIAS_HOME="$TMP_ROOT/home"; ALIAS_PROJ="$ALIAS_HOME/projects/dotfiles"
[ "$ALIAS_PROJ" -ef "$PROJ" ] || { echo "not case-insensitive fs"; exit 2; }
echo "canonical project: $PROJ"
echo "caller spelling:   $ALIAS_PROJ (same dir: yes)"
echo "+ (cd $ALIAS_HOME && FM_HOME=\$PWD bin/fm-spawn.sh cs1 \$PWD/projects/dotfiles \"sh -c 'echo CWD=\$(pwd -P)'\" --mode no-mistakes --yolo off --backend herdr)"
cd "$ALIAS_HOME"
FM_SPAWN_NO_GUARD=1 FM_HOME="$PWD" FM_ROOT_OVERRIDE="$ROOT" \
  "$ROOT/bin/fm-spawn.sh" cs1 "$PWD/projects/dotfiles" "sh -c 'echo CWD=\$(pwd -P); echo TOP=\$(git rev-parse --show-toplevel)'" --mode no-mistakes --yolo off --backend herdr > "$TMP_ROOT/out" 2> "$TMP_ROOT/err"
rc=$?
echo "exit=$rc"; echo "--- stdout"; cat "$TMP_ROOT/out"; echo "--- stderr"; tail -5 "$TMP_ROOT/err"
META="$HOME_DIR/state/cs1.meta"
if [ -f "$META" ]; then
  echo "--- meta"; grep -E '^(worktree|project)=' "$META"
  WT=$(grep '^worktree=' "$META" | cut -d= -f2-)
  [ "$WT" -ef "$PROJ" ] && echo "VERDICT: worktree IS the primary checkout (BUG)" || echo "VERDICT: worktree is distinct from primary"
  [ -n "$WT" ] && git -C "$WT" rev-parse --git-dir
  PANE=$(grep '^herdr_pane_id=' "$META" | cut -d= -f2-)
  sleep 2
  echo "--- herdr pane cwd"; herdr pane get "$PANE" --session "$SESSION" 2>/dev/null | jq -c '.result.pane | {cwd, foreground_cwd}'
  echo "--- pane capture"; (. "$ROOT/bin/fm-backend.sh"; fm_backend_source herdr; fm_backend_herdr_capture "$SESSION:$PANE" 40) | grep -E 'CWD=|TOP=' | tail -3
else
  WT=$(treehouse status 2>/dev/null | grep -o "$TMP_ROOT/pool[^ ]*" | head -1)
  echo "no meta written"
fi
if [ -n "${POST_ROOT:-}" ] && [ -f "$META" ]; then
  cp "$META" "$TMP_ROOT/meta.before"
  echo "=== fixed fm-spawn --relaunch on this record (caller spelling FM_HOME)"
  FM_SPAWN_NO_GUARD=1 FM_HOME="$PWD" FM_ROOT_OVERRIDE="$POST_ROOT" "$POST_ROOT/bin/fm-spawn.sh" cs1 --relaunch --harness codex 2>&1 | tail -3; echo "relaunch exit=${PIPESTATUS[0]}"
  for f in "" --force; do
    echo "=== fixed fm-teardown.sh cs1 $f"
    FM_HOME="$PWD" FM_ROOT_OVERRIDE="$POST_ROOT" "$POST_ROOT/bin/fm-teardown.sh" cs1 $f 2>&1 | tail -3; echo "teardown exit=${PIPESTATUS[0]}"
  done
  [ -f "$META" ] && echo "record still present: yes" || echo "record still present: NO"
  echo "primary still a normal checkout: $(git -C "$PROJ" rev-parse --git-dir) branch=$(git -C "$PROJ" branch --show-current)"
  WT=$(treehouse status 2>/dev/null | grep -o "$TMP_ROOT/pool[^ ]*Dotfiles" | head -1)
fi
if [ -n "${TEARDOWN_OK:-}" ] && [ -f "$META" ]; then
  echo "=== fixed fm-teardown.sh cs1 --force on a legit pool-worktree record"
  FM_HOME="$PWD" FM_ROOT_OVERRIDE="$ROOT" "$ROOT/bin/fm-teardown.sh" cs1 --force 2>&1 | tail -4; echo "teardown exit=${PIPESTATUS[0]}"
  [ -f "$META" ] && echo "record still present: yes" || echo "record removed: yes"
  echo "treehouse status:"; treehouse status 2>&1 | tail -3
fi
[ -f "$TMP_ROOT/hook.log" ] && { echo "--- hook log"; cat "$TMP_ROOT/hook.log"; }
[ -f "$TMP_ROOT/shim.log" ] && { echo "--- shim log"; cat "$TMP_ROOT/shim.log"; }
echo "--- primary HEAD/branch after: $(git -C "$PROJ" branch --show-current) status: $(git -C "$PROJ" status --porcelain | wc -l | tr -d ' ') dirty files"
