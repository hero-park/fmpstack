#!/usr/bin/env python3
"""Drive fmpstack's real terminal capture/guard using controlled damaged screens.
This is not vendor-renderer or Herdr-submit evidence: only terminal data is seeded.
No fmpstack implementation or transport is stubbed.
"""
from pathlib import Path
import os
import shutil
import subprocess
import time

ROOT = Path('/Users/andrewpark/.no-mistakes/worktrees/6df33f9edf6e/01M41VPXFNFNPV4ERYKTT7VP9N')
EVIDENCE = Path('/Users/andrewpark/.no-mistakes/evidence/01M41VPXFNFNPV4ERYKTT7VP9N')
LAB = ROOT / '.test-phase/adversarial'
LAB.mkdir(parents=True, exist_ok=True)
SOCKET = ROOT / '.test-phase/s'
TMUX = shutil.which('tmux')
ENV = dict(os.environ, HOME=str(ROOT / '.test-phase/home'), TMPDIR=str(ROOT / '.test-phase/tmp'),
           TERM='xterm-256color', FM_HOME=str(LAB / 'home'), FM_ROOT_OVERRIDE=str(ROOT), FM_GUARD_READ_ONLY='1')
(LAB / 'home/state').mkdir(parents=True, exist_ok=True)
SHIM = LAB / 'shim'
SHIM.mkdir(exist_ok=True)
(SHIM / 'tmux').write_text(f'#!/usr/bin/env bash\nexec "{TMUX}" -S "{SOCKET}" "$@"\n')
(SHIM / 'tmux').chmod(0o755)
ENV['PATH'] = str(SHIM) + ':' + ENV['PATH']
DRAW = LAB / 'draw.py'
DRAW.write_text("import sys,time\nfrom pathlib import Path\nframe=Path(sys.argv[1]).read_text()\nsys.stdout.write('\\x1b[2J\\x1b[H'+frame.replace('\\n','\\r\\n')+'\\x1b[6;1H')\nsys.stdout.flush()\ntime.sleep(120)\n")
CASES = {
    'mismatched-width': '──────── named ─\n❯ text\ncontinuation\n────────\n  status',
    'stale-scrollback': '──────── named ─\n❯\n\nlater transcript output\n────────────────\nmore output',
    'blank-break': '──────── named ─\n❯ text\n\ncontinuation\n────────────────\n  status',
    'halfblock-break': '──────── named ─\n❯ text\n▀▀▀▀▀▀▀▀\ncontinuation\n────────────────\n  status',
    'shell-break': '──────── named ─\n❯ text\n$ live shell\ncontinuation\n────────────────\n  status',
}
LOG = []


def tmux(*args):
    p = subprocess.run([TMUX, '-S', str(SOCKET), *args], cwd=LAB, env=ENV, text=True, capture_output=True)
    assert p.returncode == 0, (args, p.stdout, p.stderr)
    return p.stdout


try:
    tmux('-f', '/dev/null', 'new-session', '-d', '-s', 'guards', '-x', '80', '-y', '30', '-c', str(LAB), 'sleep', '120')
    for name, screen in CASES.items():
        frame = LAB / (name + '.txt')
        frame.write_text(screen)
        tmux('new-window', '-d', '-t', 'guards', '-n', name, '-c', str(LAB), 'python3', str(DRAW), str(frame))
        target = 'guards:' + name
        time.sleep(0.4)
        peek = subprocess.run(['bash', str(ROOT / 'bin/fm-peek.sh'), target, '30'], cwd=LAB, env=ENV, text=True, capture_output=True)
        assert peek.returncode == 0, peek.stderr
        assert '❯' in peek.stdout, 'live pane must have rendered the controlled terminal data'
        cmd = '''. "$1/bin/fm-backend.sh"; fm_backend_source tmux; screen=$(fm_tmux_composer_capture "$2");
        printf 'tmux='; fm_backend_composer_state tmux "$2"; printf '\n';
        if fm_pane_input_pending "$2"; then printf 'injection-deferred=true\n'; else printf 'injection-deferred=false\n'; fi
        for caps in 'styled=1\ncursor=0\nidentity=1\nrows=20' 'styled=1\ncursor=0\nidentity=0\nrows=20' 'styled=0\ncursor=0\nidentity=0\nrows=20'; do
          printf 'cursorless='; fm_composer_classify_screen "$caps" "$screen"; printf '\n';
          if fm_composer_extract_selected_content "$caps" "$screen"; then printf '\nextraction=accepted\n'; else printf 'extraction=refused\n'; fi
        done'''
        p = subprocess.run(['bash', '-c', cmd, '_', str(ROOT), target], cwd=LAB, env=ENV, text=True, capture_output=True)
        LOG.append(f'Controlled damaged terminal: {name}\n$ bin/fm-peek.sh {target} 30\n{peek.stdout}\nReal captured-screen guard outputs:\n{p.stdout}{p.stderr}')
        assert p.returncode == 0
        assert 'tmux=unknown' in p.stdout and 'injection-deferred=true' in p.stdout
        assert p.stdout.count('cursorless=unknown') == 3 and p.stdout.count('extraction=refused') == 3
        tmux('kill-window', '-t', target)
    print('All controlled stale/width/wrap-boundary screens were refused by the real captured-screen guards.')
finally:
    subprocess.run([TMUX, '-S', str(SOCKET), 'kill-server'], cwd=LAB, env=ENV, capture_output=True)
    (EVIDENCE / 'adversarial-terminal-probe.log').write_text('\n'.join(LOG))
