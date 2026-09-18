#!/bin/bash
set -eu
ROOT=$PWD
EVID=/Users/andrewpark/.no-mistakes/evidence/01M2RXHBD73VF0CA05VYH9ZMC1
LIVE=$ROOT/.test-phase-tmp/live
mkdir -p "$LIVE/home/state" "$LIVE/home/data" "$LIVE/home/config" "$LIVE/wt" "$LIVE/bin"
cd "$LIVE"
/opt/homebrew/bin/tmux -S s -f /dev/null new-session -d -s validation -n fm-scout 'sleep 600'
trap '/opt/homebrew/bin/tmux -S s kill-server 2>/dev/null || true' EXIT
cat > bin/tmux <<EOF
#!/bin/bash
cd '$LIVE'
exec /opt/homebrew/bin/tmux -S s "\$@"
EOF
chmod +x bin/tmux
export PATH="$LIVE/bin:$PATH" FM_HOME="$LIVE/home" FM_ROOT_OVERRIDE="$ROOT" TMPDIR="$ROOT/.test-phase-tmp"
printf 'kind=scout\nbackend=tmux\nwindow=validation:fm-scout\nworktree=%s\nharness=codex\n' "$LIVE/wt" > home/state/scout.meta
printf 'paused: waiting for validation round\n' > home/state/scout.status
for i in $(seq 1 230); do printf '  continuation %s\n' "$i"; done >> home/state/scout.status
printf 'Buried pause after 230 continuation lines:\n'
"$ROOT/bin/fm-crew-state.sh" scout
printf 'needs-decision [key=api]: choose interface\ndone: report delivered\n' >> home/state/scout.status
printf '\nUnanswered decision after done:\n'
"$ROOT/bin/fm-crew-state.sh" scout
printf 'failed: unrelated failure\n' >> home/state/scout.status
printf '\nUnanswered decision after failed:\n'
"$ROOT/bin/fm-crew-state.sh" scout
printf 'resolved [key=api]: answered REST\npaused: next validation round\n' >> home/state/scout.status
printf '\nAfter explicit keyed resolution:\n'
"$ROOT/bin/fm-crew-state.sh" scout
"$ROOT/bin/fm-brief.sh" live-ship example --mode no-mistakes
"$ROOT/bin/fm-brief.sh" live-scout example --scout
cp home/data/live-ship/brief.md "$EVID/generated-ship-brief.md"
cp home/data/live-scout/brief.md "$EVID/generated-scout-brief.md"
printf '\nExact endpoint closure with a prefix neighbor:\n'
tmux new-window -d -t validation: -n fm-scout2 'sleep 600'
. "$ROOT/bin/fm-backend.sh"
fm_backend_source tmux
fm_backend_tmux_kill validation:fm-scout
fm_backend_tmux_kill validation:fm-scout
if fm_backend_tmux_kill ''; then exit 1; fi
tmux list-windows -t validation -F '#{window_name}'
