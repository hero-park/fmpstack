#!/usr/bin/env python3
"""Run only intent-owned executable test selectors, not static checks or full suites."""
from pathlib import Path
import os
import subprocess

ROOT = Path('/Users/andrewpark/.no-mistakes/worktrees/6df33f9edf6e/01M41VPXFNFNPV4ERYKTT7VP9N')
EVIDENCE = Path('/Users/andrewpark/.no-mistakes/evidence/01M41VPXFNFNPV4ERYKTT7VP9N')
LAB = ROOT / '.test-phase'
ENV = dict(os.environ, HOME=str(LAB / 'home'), TMPDIR=str(LAB / 'tmp'), FM_TEST_SKIP_ORPHAN_REAP='1')
lib = LAB / 'lib.sh'
if not lib.exists():
    lib.symlink_to(ROOT / 'tests/lib.sh')
checks = [
    ('fm-composer-lib', 'test_bare_shell_glyphs_are_unknown', [
        'test_matrix_claude_titled_top_rule', 'test_matrix_claude_titled_wrap_region']),
    ('fm-brief', 'test_script_parses', [
        'test_ship_modes_generate_clean_briefs',
        'test_engineering_inner_loop_is_worker_only_and_harness_neutral',
        'test_scout_and_secondmate_scaffold', 'test_secondmate_no_projects_charter']),
]
for name, first_call, selectors in checks:
    # Reuse test definitions verbatim; the file's implementation-source checks
    # and unrelated test calls are never invoked. Assertions execute the product.
    definitions = (ROOT / f'tests/{name}.test.sh').read_text().rsplit('\n' + first_call + '\n', 1)[0]
    selected = LAB / f'{name}-selected.sh'
    selected.write_text(definitions + '\n' + '\n'.join(selectors) + '\n')
    for shell, label in [('bash', 'ambient'), ('/bin/bash', 'stock')]:
        p = subprocess.run([shell, str(selected)], cwd=ROOT, env=ENV, text=True, capture_output=True)
        (EVIDENCE / f'{name}-selected-{label}.log').write_text(
            '$ ' + shell + ' ' + str(selected) + '\nSelectors: ' + ', '.join(selectors) + '\n' + p.stdout + p.stderr)
        print(name, label, 'exit=' + str(p.returncode), p.stdout, p.stderr)
        assert p.returncode == 0
