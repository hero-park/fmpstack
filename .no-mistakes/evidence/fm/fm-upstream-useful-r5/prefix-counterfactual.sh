#!/usr/bin/env bash
set -eu
export FM_HOME="$PWD/.test-phase-tmp/live-home"
export LIVE_TMUX_SOCKET=.test-phase-tmp/counter.sock
export LIVE_TMUX_BIN=$(command -v tmux)
tmux() { "$LIVE_TMUX_BIN" -S "$LIVE_TMUX_SOCKET" "$@"; }
export -f tmux
unset TMUX TMUX_PANE
trap 'tmux kill-server 2>/dev/null || true' EXIT
tmux -f /dev/null new-session -d -s testphase -n control 'sleep 600'
tmux new-window -d -t testphase -n fm-worker-neighbor 'sleep 600'
printf 'Actual inventory (worker does not exist):\n'
tmux list-windows -t testphase -F '#{window_name}'
printf 'Non-exact lookup resolves to: '
tmux display-message -p -t testphase:fm-worker '#{window_name}'
printf 'Exact lookup exit: '
if tmux display-message -p -t '=testphase:=fm-worker' '#{window_name}'; then echo 0; else echo "$?"; fi
printf 'Status with prefix neighbor: '
bin/fm-crew-state.sh worker
tmux kill-window -t '=testphase:=fm-worker-neighbor'
printf 'Status after removing only the neighbor: '
bin/fm-crew-state.sh worker
tmux kill-server
printf 'Status after removing the isolated server: '
bin/fm-crew-state.sh worker
printf 'Baseline pane_readable implementation:\n'
git show f5fab028:bin/fm-crew-state.sh | sed -n '/^pane_readable()/,/^}/p'
