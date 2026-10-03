#!/usr/bin/env python3
"""Read the real, offline Claude renderer through the real fmpstack tmux adapter.
No messages are submitted to a model. No Herdr lifecycle or fleet session is used.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path('/Users/andrewpark/.no-mistakes/worktrees/6df33f9edf6e/01M41VPXFNFNPV4ERYKTT7VP9N')
EVIDENCE = Path('/Users/andrewpark/.no-mistakes/evidence/01M41VPXFNFNPV4ERYKTT7VP9N')
LAB = ROOT / '.test-phase/claude'
LAB.mkdir(parents=True, exist_ok=True)
CONFIG = LAB / 'config'
CONFIG.mkdir(exist_ok=True)
(CONFIG / '.claude.json').write_text(json.dumps({'hasCompletedOnboarding': True, 'theme': 'dark', 'numStartups': 1}))
SOCKET = ROOT / '.test-phase/s'
TMUX = shutil.which('tmux')
CLAUDE = shutil.which('claude')
ENV = {k: v for k, v in os.environ.items() if not any(x in k for x in ['ANTHROPIC', 'CLAUDE', 'HERDR', 'AWS_', 'OPENAI', 'BEDROCK', 'VERTEX'])}
ENV.update(HOME=str(LAB / 'home'), TMPDIR=str(ROOT / '.test-phase/tmp'),
           CLAUDE_CONFIG_DIR=str(CONFIG), ANTHROPIC_API_KEY='disposable-offline-placeholder',
           ANTHROPIC_BASE_URL='http://127.0.0.1:1', DISABLE_AUTOUPDATER='1',
           CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1', CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION='false',
           XDG_CONFIG_HOME=str(LAB / 'xdg-config'), XDG_CACHE_HOME=str(LAB / 'xdg-cache'),
           TERM='xterm-256color', FM_HOME=str(LAB / 'fm-home'), FM_ROOT_OVERRIDE=str(ROOT), FM_GUARD_READ_ONLY='1')
(LAB / 'home').mkdir(exist_ok=True)
(LAB / 'fm-home/state').mkdir(parents=True, exist_ok=True)
SHIM = LAB / 'shim'
SHIM.mkdir(exist_ok=True)
(SHIM / 'tmux').write_text(f'#!/usr/bin/env bash\nexec "{TMUX}" -S "{SOCKET}" "$@"\n')
(SHIM / 'tmux').chmod(0o755)
ENV['PATH'] = str(SHIM) + ':' + ENV['PATH']
LOG = []


def tmux(*args):
    p = subprocess.run([TMUX, '-S', str(SOCKET), *args], env=ENV, cwd=LAB, text=True, capture_output=True)
    assert p.returncode == 0, (args, p.stdout, p.stderr)
    return p.stdout


def capture(name, target='probe:0'):
    plain = tmux('capture-pane', '-p', '-t', target, '-S', '0', '-E', '-')
    ansi = tmux('capture-pane', '-e', '-p', '-t', target, '-S', '0', '-E', '-')
    cursor = tmux('display-message', '-p', '-t', target, '#{cursor_y}').strip()
    (EVIDENCE / f'claude-{name}.txt').write_text(plain)
    (EVIDENCE / f'claude-{name}.ansi').write_text(ansi)
    cmd = '''. "$1/bin/fm-backend.sh"; fm_backend_source tmux; screen=$(fm_tmux_composer_capture "$2"); printf 'tmux='; fm_backend_composer_state tmux "$2"; printf '\ncursorless-styled='; fm_composer_classify_screen 'styled=1\ncursor=0\nidentity=0\nrows=40' "$screen"; printf '\ncursorless-styled-identity='; fm_composer_classify_screen 'styled=1\ncursor=0\nidentity=1\nrows=40' "$screen"; printf '\ncursorless-plain='; fm_composer_classify_screen 'styled=0\ncursor=0\nidentity=0\nrows=40' "$(printf '%s' "$screen" | fm_composer_strip_ansi)"; printf '\nextracted='; if fm_composer_extract_selected_content 'styled=1\ncursor=0\nidentity=0\nrows=40' "$screen"; then printf '\nextraction-status=0\n'; else printf '\nextraction-status=1\n'; fi '''
    p = subprocess.run(['bash', '-c', cmd, '_', str(ROOT), target], cwd=LAB, env=ENV, text=True, capture_output=True)
    assert p.returncode == 0, (p.stdout, p.stderr)
    LOG.append(f'{name}: grid=80x30 cursor_y={cursor}\n{p.stdout}\n{plain}')
    return plain, p.stdout


try:
    version = subprocess.run([CLAUDE, '--version'], env=ENV, cwd=LAB, text=True, capture_output=True).stdout.strip()
    LOG.append('Claude version: ' + version)
    tmux('-f', '/dev/null', 'new-session', '-d', '-s', 'probe', '-x', '80', '-y', '30', '-c', str(LAB),
         CLAUDE, '--bare', '--setting-sources', '', '--strict-mcp-config', '--tools', '',
         '--name', 'Firstmate operational input validation')
    screen = ''
    for _ in range(30):
        time.sleep(0.5)
        screen = tmux('capture-pane', '-p', '-t', 'probe:0')
        if '❯' in screen and ('bypass' in screen or 'for shortcuts' in screen or 'disposable-offline' in screen):
            break
    screen, verdicts = capture('startup')
    # Only dismiss onboarding choices visibly present in this isolated account.
    if 'Yes, I trust this folder' in screen:
        if '❯ No, exit' in screen:
            tmux('send-keys', '-t', 'probe:0', 'Down')
        tmux('send-keys', '-t', 'probe:0', 'Enter')
        time.sleep(2)
        screen, verdicts = capture('trusted')
    if 'Use this API key' in screen or ('API key' in screen and 'Yes' in screen):
        tmux('send-keys', '-t', 'probe:0', 'Down', 'Enter')
        time.sleep(2)
        screen, verdicts = capture('key-choice')
    # Do not send Enter once input text has been typed: this is renderer-only.
    assert 'tmux=empty' in verdicts, 'isolated Claude must reach a real empty composer'
    assert 'cursorless-styled=empty' in verdicts and 'cursorless-plain=empty' in verdicts
    assert '─ Firstmate operational input validation ─' in screen, 'real renderer must show the named top rule'
    tmux('send-keys', '-t', 'probe:0', '-l', 'fix the login bug')
    time.sleep(1)
    screen, verdicts = capture('typed-input')
    assert 'tmux=pending' in verdicts and 'cursorless-styled=pending' in verdicts and 'cursorless-plain=unknown' in verdicts
    assert 'extracted=fix the login bug\n' in verdicts
    tmux('send-keys', '-t', 'probe:0', 'C-u')
    time.sleep(0.5)
    typed = 'fix the login bug and its regression before shipping; preserve every separator width and ambiguity safety boundary'
    tmux('send-keys', '-t', 'probe:0', '-l', typed)
    time.sleep(2)
    screen, verdicts = capture('wrapped-input')
    assert 'tmux=pending' in verdicts and 'cursorless-styled=pending' in verdicts and 'cursorless-styled-identity=pending' in verdicts
    assert 'cursorless-plain=unknown' in verdicts
    assert 'extracted=' + typed in verdicts
    # Replay only these real vendor-rendered bytes through the pre-correction
    # classifier to reproduce R1. This baseline replay is NOT a live scenario.
    before = subprocess.run(['bash', '-c', '. "$1/bin/fm-composer-lib.sh"; fm_composer_classify_screen "styled=1" "$(< "$2")"', '_',
        str(ROOT / '.test-phase/pre-review'), str(EVIDENCE / 'claude-wrapped-input.ansi')],
        cwd=LAB, env=ENV, text=True, capture_output=True)
    assert before.returncode == 0 and before.stdout == 'unknown', before.stdout
    LOG.append('Same real captured wrapped input: pre-review d2534bc classifier=unknown; target a1e04c0 classifier=pending; complete extraction=' + typed)
    LOG.append('Typed literal, never submitted: ' + typed)
    tmux('new-window', '-d', '-t', 'probe', '-n', 'unicode', '-c', str(LAB),
         CLAUDE, '--bare', '--setting-sources', '', '--strict-mcp-config', '--tools', '', '--name', 'Firstmate naïve title')
    for _ in range(30):
        time.sleep(0.5)
        screen = tmux('capture-pane', '-p', '-t', 'probe:unicode')
        if 'Firstmate naïve title' in screen and '❯' in screen:
            break
    screen, verdicts = capture('nonascii-title', 'probe:unicode')
    assert 'Firstmate naïve title' in screen
    assert 'tmux=empty' in verdicts
    assert 'cursorless-styled=unknown' in verdicts and 'cursorless-styled-identity=unknown' in verdicts and 'cursorless-plain=unknown' in verdicts
    assert 'extraction-status=1' in verdicts
    LOG.append('Adversarial real non-ASCII title: cursorless reads unknown and extraction refuses; the independently anchored tmux cursor still proves idle. No Enter was sent.')
    LOG.append('No live Herdr titled-rule or submit-confirmation evidence was refreshed. Model endpoint is unreachable localhost and no operator credentials were used.')
    print('\n'.join(LOG))
finally:
    subprocess.run([TMUX, '-S', str(SOCKET), 'kill-server'], cwd=LAB, env=ENV, capture_output=True)
    (EVIDENCE / 'claude-terminal-probe.log').write_text('\n'.join(LOG))
