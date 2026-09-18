#!/usr/bin/env bash
set -euo pipefail
ROOT=$PWD
D="$ROOT/.test-phase-tmp/watch-fresh"
mkdir -p "$D"/{home/state,home/config,home/data,wt,route}
export FM_HOME="$D/home" FM_STATE_OVERRIDE="$D/home/state" FM_CREW_STATE_NO_FORGE=1
export FM_GATE_REFUSE_BYPASS=1
REAL_TMUX=$(command -v tmux)
cat > "$D/route/tmux" <<EOF
#!/bin/bash
cd '$D'
exec '$REAL_TMUX' -S test.sock "\$@"
EOF
chmod +x "$D/route/tmux"
export PATH="$D/route:$PATH"
unset TMUX TMUX_PANE
trap 'tmux kill-server 2>/dev/null || true' EXIT
tmux -f /dev/null new-session -d -s lab -n control 'sleep 300'
tmux new-window -d -t lab: -n fm-worker 'sleep 300'
tmux new-window -d -t lab: -n fm-worker2 'sleep 300'
printf 'window=lab:fm-worker\nbackend=tmux\nkind=scout\nharness=claude\nworktree=%s\n' "$D/wt" > "$FM_HOME/state/worker.meta"
gen=$(bin/fm-busy-event.sh arm "$FM_HOME/state" worker)
bin/fm-busy-event.sh apply "$FM_HOME/state" worker busy --gen "$gen" --source claude-hook --event user-prompt-submit
out=$(bin/fm-crew-state.sh worker); printf 'LIVE BUSY: %s\n' "$out"; [[ "$out" = *'state: working'* ]]
. bin/fm-backend.sh
fm_backend_source tmux
fm_backend_tmux_kill lab:fm-worker
out=$(bin/fm-crew-state.sh worker); printf 'CLOSED WITH PREFIX NEIGHBOR: %s\n' "$out"; [[ "$out" = *'state: unknown'* ]]
fm_backend_tmux_kill lab:fm-worker
printf 'REPEATED CLOSE SURVIVORS:\n'; tmux list-windows -t lab -F '#{window_name}'
[ "$(tmux list-windows -t lab -F '#{window_name}' | wc -l | tr -d ' ')" = 2 ]
if fm_backend_tmux_kill ''; then exit 1; fi
printf 'EMPTY CLOSE: refused\n'
tmux new-window -d -t lab: -n fm-worker 'sleep 300'
bin/fm-busy-event.sh apply "$FM_HOME/state" worker idle --gen "$gen" --source claude-hook --event stop
printf 'paused: waiting for validation round\n' > "$FM_HOME/state/worker.status"
for ((i=0;i<220;i++)); do printf '  continuation %s\n' "$i" >> "$FM_HOME/state/worker.status"; done
out=$(bin/fm-crew-state.sh worker); printf 'LONG CONTINUATION: %s\n' "$out"; [[ "$out" = *'state: paused'* ]]
printf 'needs-decision [key=choice]: choose outcome\nworking: resumed unrelated work\n' >> "$FM_HOME/state/worker.status"
out=$(bin/fm-crew-state.sh worker); printf 'OPEN DECISION: %s\n' "$out"; [[ "$out" = *'state: parked'* ]]
printf 'resolved [key=choice]: chosen\npaused: waiting for validation round\n' >> "$FM_HOME/state/worker.status"
out=$(bin/fm-crew-state.sh worker); printf 'RESOLVED DECISION: %s\n' "$out"; [[ "$out" = *'state: paused'* ]]

bin/fm-busy-event.sh apply "$FM_HOME/state" worker busy --gen "$gen" --source claude-hook --event user-prompt-submit
export FM_POLL=1 FM_SIGNAL_GRACE=1 FM_CHECK_INTERVAL=999999 FM_HEARTBEAT=999999 FM_STALE_ESCALATE_SECS=2 FM_BUSY_TURN_MAX_SECS=1 FM_PAUSE_RESURFACE_SECS=5
bin/fm-watch.sh > "$D/watch.out" 2>&1 &
watch_pid=$!
trap 'kill "$watch_pid" 2>/dev/null || true; wait "$watch_pid" 2>/dev/null || true; tmux kill-server 2>/dev/null || true' EXIT
for ((i=0;i<25;i++)); do
  if ! kill -0 "$watch_pid" 2>/dev/null; then break; fi
  sleep 1
done
cat "$D/watch.out"
if [ -f "$FM_HOME/state/.wake-queue" ]; then cat "$FM_HOME/state/.wake-queue"; fi
if ! grep -Eq 'declared (wait|pause)' "$D/watch.out"; then printf 'No declared-wait result observed\n'; exit 1; fi
if grep -q 'possible wedge' "$D/watch.out"; then exit 1; fi
