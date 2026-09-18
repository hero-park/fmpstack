#!/usr/bin/env bash
set -eu
ROOT=$PWD
EVIDENCE=/Users/andrewpark/.no-mistakes/evidence/01M2TX81RG2RPK68ZXRQVR1TAM
export FM_HOME="$ROOT/.test-phase-tmp/live-home"
export FM_GATE_REFUSE_BYPASS=1
mkdir -p "$FM_HOME"/{state,config,data,projects} "$FM_HOME/work"
export LIVE_TMUX_SOCKET=.test-phase-tmp/live.sock
export LIVE_TMUX_BIN=$(command -v tmux)
tmux() { "$LIVE_TMUX_BIN" -S "$LIVE_TMUX_SOCKET" "$@"; }
export -f tmux
unset TMUX TMUX_PANE
trap 'tmux kill-server 2>/dev/null || true' EXIT
tmux -f /dev/null new-session -d -s testphase -n control 'sleep 600'
tmux new-window -d -t testphase -n fm-worker 'sleep 600'
tmux new-window -d -t testphase -n fm-worker-neighbor 'sleep 600'
cat > "$FM_HOME/state/worker.meta" <<EOF
backend=tmux
window=testphase:fm-worker
endpoint_task_id=worker
worktree=$FM_HOME/work
kind=scout
harness=claude
EOF
bin/fm-busy-event.sh arm "$FM_HOME/state" worker --state idle --source fm-recovery --event recovered >/dev/null
printf 'paused: own validation round\n' > "$FM_HOME/state/worker.status"
for i in $(seq 1 225); do printf '  continuation %s\n' "$i" >> "$FM_HOME/state/worker.status"; done
printf '\n### Latest event remains visible beyond 200 continuation lines\n'
out=$(bin/fm-crew-state.sh worker); printf '%s\n' "$out"
[[ "$out" == *'paused'*'own validation round'* ]]
printf 'needs-decision [key=release]: approve release\nworking: more investigation\n  continuation\n' >> "$FM_HOME/state/worker.status"
printf '\n### Open decision survives later working event\n'
out=$(bin/fm-crew-state.sh worker); printf '%s\n' "$out"
[[ "$out" == *'parked'*'approve release'* ]]
printf 'resolved [key=release]: approved\npaused: next validation round\n  continuation\n' >> "$FM_HOME/state/worker.status"
printf '\n### Resolved decision clears and current pause appears\n'
out=$(bin/fm-crew-state.sh worker); printf '%s\n' "$out"
[[ "$out" == *'paused'*'next validation round'* ]]
printf '\n### Active lifecycle evidence outranks the paused log\n'
bin/fm-busy-event.sh apply "$FM_HOME/state" worker busy --current-gen --source claude-hook --event UserPromptSubmit
out=$(bin/fm-crew-state.sh worker); printf '%s\n' "$out"
[[ "$out" == *'working'*'pane'* ]]
printf '\n### Generated worker and supervisor contracts\n'
bin/fm-brief.sh ship sample --mode direct-PR
bin/fm-brief.sh scout sample --scout
FM_SECONDMATE_CHARTER='Supervise sample work.' bin/fm-brief.sh mate --secondmate sample
cp "$FM_HOME/data/ship/brief.md" "$EVIDENCE/ship-brief.md"
cp "$FM_HOME/data/scout/brief.md" "$EVIDENCE/scout-brief.md"
cp "$FM_HOME/data/mate/brief.md" "$EVIDENCE/secondmate-brief.md"
printf '\n### Exact endpoint closure and adversarial prefix preservation\n'
. "$ROOT/bin/fm-backend.sh"
fm_backend_source tmux
if fm_backend_tmux_kill ''; then echo 'ERROR empty target accepted'; exit 1; fi
fm_backend_tmux_kill testphase:fm-work
printf 'After absent prefix target:\n'; tmux list-windows -t testphase -F '#{window_name}'
fm_backend_tmux_kill testphase:fm-worker
printf 'After exact close:\n'; tmux list-windows -t testphase -F '#{window_name}'
tmux list-windows -t testphase -F '#{window_name}' | grep -qx fm-worker-neighbor
if tmux list-windows -t testphase -F '#{window_name}' | grep -qx fm-worker; then exit 1; fi
fm_backend_tmux_kill testphase:fm-worker
printf 'Repeated close of confirmed-absent endpoint returned success\n'
printf '\n### Closed endpoint does not turn old pause into current truth\n'
out=$(bin/fm-crew-state.sh worker); printf '%s\n' "$out"
[[ "$out" == *'unknown'*'backend target gone'* ]]
