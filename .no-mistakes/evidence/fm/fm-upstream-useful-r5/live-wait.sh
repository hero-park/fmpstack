#!/usr/bin/env bash
set -eu
export FM_HOME="$PWD/.test-phase-tmp/wait-home"
export LIVE_TMUX_SOCKET=.test-phase-tmp/wait.sock
export LIVE_TMUX_BIN=$(command -v tmux)
tmux() { "$LIVE_TMUX_BIN" -S "$LIVE_TMUX_SOCKET" "$@"; }
export -f tmux
unset TMUX TMUX_PANE
mkdir -p "$FM_HOME"/{state,config,data,work}
trap 'tmux kill-server 2>/dev/null || true' EXIT
tmux -f /dev/null new-session -d -s waittest -n fm-waiter 'sleep 600'
cat > "$FM_HOME/state/waiter.meta" <<EOF
backend=tmux
window=waittest:fm-waiter
worktree=$FM_HOME/work
kind=scout
harness=claude
EOF
bin/fm-busy-event.sh arm "$FM_HOME/state" waiter --state busy --source fm-recovery --event recovered >/dev/null
printf 'paused: own validation round; expires nonsense tomorrowish\n  continuation\n' > "$FM_HOME/state/waiter.status"
export FM_BUSY_TURN_MAX_SECS=1 FM_STALE_ESCALATE_SECS=1 FM_PAUSE_RESURFACE_SECS=3
export FM_POLL=1 FM_SIGNAL_GRACE=1 FM_CHECK_INTERVAL=999999 FM_HEARTBEAT=999999
python3 - <<'PY'
import subprocess,os,pathlib
p=subprocess.Popen(['bin/fm-watch.sh'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
try: out,_=p.communicate(timeout=20)
except subprocess.TimeoutExpired:
 p.terminate();out,_=p.communicate(timeout=5);print(out);raise SystemExit('No wait recheck within 20 seconds')
print(out)
s=pathlib.Path(os.environ['FM_HOME'])/'state'
for f in sorted(s.glob('.wake-queue*')):
 if f.is_file():print(f.name+': '+f.read_text())
assert 'awaiting external' in out or 'declared wait' in out,out
assert 'escalation 1' not in out,out
assert p.returncode==0,p.returncode
PY
