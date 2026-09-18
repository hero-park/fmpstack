#!/bin/bash
set -eu
ROOT=$PWD
export FM_HOME="$ROOT/.test-phase-tmp/drain-home" FM_STATE_OVERRIDE="$ROOT/.test-phase-tmp/drain-home/state" TMPDIR="$ROOT/.test-phase-tmp"
mkdir -p "$FM_STATE_OVERRIDE" "$FM_HOME/data"
for kind in ship scout; do
 for event in done failed; do
  id="$kind-$event"
  printf 'kind=%s\n' "$kind" > "$FM_STATE_OVERRIDE/$id.meta"
  printf 'needs-decision [key=api]: choose interface\n' > "$FM_STATE_OVERRIDE/$id.status"
 done
done
printf 'Initial open decisions:\n'
"$ROOT/bin/fm-wake-drain.sh"
for kind in ship scout; do
 for event in done failed; do
  printf '%s: unrelated outcome\n' "$event" >> "$FM_STATE_OVERRIDE/$kind-$event.status"
 done
done
printf '\nAfter terminal events (incremental drain):\n'
"$ROOT/bin/fm-wake-drain.sh"
for kind in ship scout; do
 for event in done failed; do
  printf 'resolved [key=api]: answered REST\n' >> "$FM_STATE_OVERRIDE/$kind-$event.status"
 done
done
printf '\nAfter explicit resolutions:\n'
"$ROOT/bin/fm-wake-drain.sh"
