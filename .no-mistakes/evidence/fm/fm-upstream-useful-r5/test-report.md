# Targeted validation at d10ac69

Live product CLI checks used isolated FM_HOME directories and a private tmux 3.7c socket. No native agent or external forge lifecycle was started.

- Passed: generated ship/scout briefs explicitly include own-validation pauses and the worker-only inner loop; secondmate charter remains separate.
- Passed: status CLI recognizes a pause beneath 225 continuation lines, preserves an open decision across a working event, clears it upon resolution, and prefers a busy lifecycle event over paused prose.
- Passed: real tmux close rejects an empty target, preserves a prefix neighbor, closes exactly the named worker, and accepts a repeated close after confirmed absence.
- Passed: running watcher emits a declared-pause recheck, not a wedge escalation, even with an unparseable expiry phrase.
- Failed: after the worker window is gone, fm-crew-state still reports working from its old busy record while another window keeps the server alive. Removing the prefix neighbor does not cure it; removing the server does. tmux display-message is not an endpoint-presence proof. The same pane_readable call exists at the base commit.

Focused regression files passed: fm-classify-decision-key, fm-crew-state, fm-teardown-endpoint-safety, fm-backend-orca, fm-brief, fm-spawn-dispatch-profile, fm-turnend-guard, fm-fleet-snapshot-view. These include substituted external tools and are not credited as native integration evidence. Spawn initially refused a secondmate fixture under the repository; rerunning with normal incidental toolchain temporary directories passed.

fm-watch-triage.test.sh exceeded the local 180-second bound after passing its busy-pause cases. The directly affected selectors test_declared_wait_at_wedge_threshold_is_deferred, test_busy_declared_pause_is_rechecked_not_wedge_escalated, and test_nonterminal_paused_rechecks_authoritative_state were then executed separately and passed.

Ruby YAML normalized the lint job and confirmed its executable command is bin/fm-lint.sh --jobs 1. No lint, static analysis, full repository suite, pipeline control, remote CI, push, or PR operations were run.

Limits: no live Herdr/Orca/Zellij/cmux close, native Codex/Claude lifecycle, or passed-validation forge query. Hosted sequential-lint execution belongs to the outer CI phase. CLI and generated Markdown are the affected user surfaces; no rendered UI screenshot was applicable. No source changes were made.
