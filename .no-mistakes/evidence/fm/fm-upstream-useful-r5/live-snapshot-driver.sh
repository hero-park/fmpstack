#!/usr/bin/env bash
set -euo pipefail
ROOT=$PWD
D="$ROOT/.test-phase-tmp/snapshot"
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

printf 'needs-decision [key=choice]: old choice\n' > "$FM_HOME/state/worker.status"
bin/fm-busy-event.sh apply "$FM_HOME/state" worker busy --gen "$gen" --source claude-hook --event user-prompt-submit
printf 'window=lab:fm-worker2\nbackend=tmux\nkind=secondmate\nharness=claude\nworktree=%s\n' "$D/wt" > "$FM_HOME/state/mate.meta"
printf 'needs-decision [key=choice]: persistent choice\n' > "$FM_HOME/state/mate.status"
gen2=$(bin/fm-busy-event.sh arm "$FM_HOME/state" mate)
bin/fm-busy-event.sh apply "$FM_HOME/state" mate busy --gen "$gen2" --source claude-hook --event user-prompt-submit
bin/fm-fleet-snapshot.sh --json > /Users/andrewpark/.no-mistakes/evidence/01M2TX81RG2RPK68ZXRQVR1TAM/live-snapshot.json
jq '.tasks[] | {id,current_state,hints}' /Users/andrewpark/.no-mistakes/evidence/01M2TX81RG2RPK68ZXRQVR1TAM/live-snapshot.json
jq -e '[.tasks[] | select(.id=="worker") | .hints.open_decisions | length] == [0]' /Users/andrewpark/.no-mistakes/evidence/01M2TX81RG2RPK68ZXRQVR1TAM/live-snapshot.json
jq -e '[.tasks[] | select(.id=="mate") | .hints.open_decisions | length] == [1]' /Users/andrewpark/.no-mistakes/evidence/01M2TX81RG2RPK68ZXRQVR1TAM/live-snapshot.json
