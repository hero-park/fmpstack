#!/usr/bin/env python3
"""Render the recorded real Claude terminal captures, not a proposed/mock UI."""
from pathlib import Path
import html
import re

EVIDENCE = Path('/Users/andrewpark/.no-mistakes/evidence/01M41VPXFNFNPV4ERYKTT7VP9N')
BASE = ['#000000', '#cc5555', '#55cc55', '#cccc55', '#5555cc', '#cc55cc', '#55cccc', '#dddddd',
        '#555555', '#ff5555', '#55ff55', '#ffff55', '#5555ff', '#ff55ff', '#55ffff', '#ffffff']


def color256(n):
    if n < 16:
        return BASE[n]
    if n >= 232:
        v = 8 + (n - 232) * 10
        return f'rgb({v},{v},{v})'
    n -= 16
    steps = [0, 95, 135, 175, 215, 255]
    return f'rgb({steps[n // 36]},{steps[(n // 6) % 6]},{steps[n % 6]})'


def render(data):
    # OSC hyperlink metadata is not displayed in terminal cells.
    data = re.sub(r'\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)', '', data)
    result, state = [], {}
    for piece in re.split(r'(\x1b\[[0-9;]*m)', data):
        if piece.startswith('\x1b['):
            codes = [int(x or '0') for x in piece[2:-1].split(';')]
            i = 0
            while i < len(codes):
                n = codes[i]
                if n == 0:
                    state = {}
                elif n == 1:
                    state['font-weight'] = 'bold'
                elif n == 2:
                    state['opacity'] = '.55'
                elif n == 22:
                    state.pop('opacity', None)
                    state.pop('font-weight', None)
                elif n == 3:
                    state['font-style'] = 'italic'
                elif n == 23:
                    state.pop('font-style', None)
                elif n == 4:
                    state['text-decoration'] = 'underline'
                elif n == 24:
                    state.pop('text-decoration', None)
                elif 30 <= n <= 37 or 90 <= n <= 97:
                    state['color'] = BASE[n - 30 if n < 90 else n - 90 + 8]
                elif n == 39:
                    state.pop('color', None)
                elif n == 38 and i + 2 < len(codes):
                    if codes[i + 1] == 5:
                        state['color'] = color256(codes[i + 2])
                        i += 2
                    elif codes[i + 1] == 2 and i + 4 < len(codes):
                        state['color'] = 'rgb(%s,%s,%s)' % tuple(codes[i + 2:i + 5])
                        i += 4
                i += 1
        elif piece:
            style = ';'.join(k + ':' + v for k, v in state.items())
            result.append('<span style="' + style + '">' + html.escape(piece) + '</span>')
    return ''.join(result)


panels = [
    ('key-choice', 'Named composer · idle', 'tmux and both styled cursorless profiles: empty; plain capture: empty.'),
    ('typed-input', 'Named composer · one-line input', 'Styled: pending. Plain: unknown. Extracted exactly “fix the login bug”.'),
    ('wrapped-input', 'Named composer · wrapped input', 'Styled: pending. Plain: unknown. Complete wrapped payload extracted; matching rule/footer excluded. Same capture on d2534bc: unknown.'),
    ('nonascii-title', 'Adversarial non-ASCII title', 'Cursorless profiles: unknown; extraction refused. Independently anchored tmux cursor: empty.'),
]
blocks = []
for key, title, verdict in panels:
    data = (EVIDENCE / f'claude-{key}.ansi').read_text()
    blocks.append('<section><h2>' + html.escape(title) + '</h2><p>' + html.escape(verdict) + '</p><pre aria-label="Captured real Claude terminal">' + render(data) + '</pre></section>')
page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Real Claude terminal evidence</title>
<style>html{color-scheme:dark;background:#161616;color:#ddd;font:15px system-ui}body{max-width:900px;margin:auto;padding:32px}h1{font-size:28px}h2{font-size:19px}p{line-height:1.55}section{min-width:0;margin:28px 0;border-top:1px solid #444;padding-top:8px}pre{background:#101010;border:1px solid #444;border-radius:8px;padding:16px;overflow-x:auto;font:13px/1.4 Menlo,Consolas,monospace;white-space:pre;max-width:100%;min-width:0}aside{border-left:3px solid #e0ae68;padding:4px 16px;color:#e0c49d}a{color:#9ed8eb}</style>
<h1>Real Claude terminal captures</h1><p>Claude Code 2.1.288, isolated tmux 80×30, target a1e04c0a8fcdbafaf32c930fce4cdce72f67cc31. These are the actual captured terminal cells and ANSI foreground styles rendered as portable HTML, not an OS screenshot or a mocked composer.</p>
<aside>No message was submitted to a model. No operator credentials, native Herdr session, or captain default session were used. The prior Claude 2.1.260 / Herdr 0.9.1 titled-rule and bounded-reply evidence gaps remain unrefreshed.</aside>
''' + ''.join(blocks) + '''<p>Design source: the real dark terminal capture and its ANSI palette; no speculative product UI or remote design dependencies.</p><p><a href="claude-terminal-probe.log">Complete CLI transcript</a> · <a href="isolated-cli.log">Fleet-sync and generated-brief transcript</a></p></html>'''
(EVIDENCE / 'terminal-evidence.html').write_text(page)
print('Wrote terminal-evidence.html from actual captured ANSI terminal output.')
