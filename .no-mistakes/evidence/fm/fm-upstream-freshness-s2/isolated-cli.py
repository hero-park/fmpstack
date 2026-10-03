#!/usr/bin/env python3
"""Drive the real fleet-sync and brief CLIs with disposable worktree-local data."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('/Users/andrewpark/.no-mistakes/worktrees/6df33f9edf6e/01M41VPXFNFNPV4ERYKTT7VP9N')
EVIDENCE = Path('/Users/andrewpark/.no-mistakes/evidence/01M41VPXFNFNPV4ERYKTT7VP9N')
LAB = ROOT / '.test-phase/cli'
LAB.mkdir(parents=True, exist_ok=True)
ENV = dict(os.environ, HOME=str(ROOT / '.test-phase/home'), TMPDIR=str(ROOT / '.test-phase/tmp'),
           GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
           GIT_AUTHOR_NAME='Disposable test', GIT_AUTHOR_EMAIL='test@example.invalid',
           GIT_COMMITTER_NAME='Disposable test', GIT_COMMITTER_EMAIL='test@example.invalid',
           FM_ROOT_OVERRIDE=str(ROOT), FM_HOME=str(LAB / 'home'), FM_GUARD_READ_ONLY='1')
(LAB / 'home/projects').mkdir(parents=True, exist_ok=True)
LOG = []


def run(*args, env=None, ok=True, record=True):
    result = subprocess.run([str(a) for a in args], cwd=ROOT, env=env or ENV, text=True, capture_output=True)
    if record:
        LOG.append('$ ' + ' '.join(str(a) for a in args) + '\n' + result.stdout + result.stderr + f'[exit {result.returncode}]\n')
    if ok:
        assert result.returncode == 0, (args, result.stdout, result.stderr)
    return result


def git(where, *args):
    return run('git', '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', '-C', where, *args, record=False).stdout.strip()


def advance(work, text):
    (work / 'file.txt').write_text(text + '\n')
    git(work, 'add', 'file.txt')
    git(work, 'commit', '-qm', text)
    git(work, 'push', '-q', 'origin', 'main')
    return git(work, 'rev-parse', 'HEAD')


def sync(target):
    return run('bash', ROOT / 'bin/fm-fleet-sync.sh', target).stdout


try:
    work = LAB / 'publisher'
    remote = LAB / 'origin.git'
    clone = LAB / 'home/projects/CaseClone'
    run('git', 'init', '-q', '-b', 'main', work, record=False)
    (work / 'file.txt').write_text('initial\n')
    git(work, 'add', 'file.txt')
    git(work, 'commit', '-qm', 'initial')
    run('git', 'clone', '--quiet', '--bare', work, remote, record=False)
    git(work, 'remote', 'add', 'origin', str(remote))
    run('git', 'clone', '--quiet', remote, clone, record=False)
    old = git(clone, 'rev-parse', 'HEAD')
    expected = advance(work, 'case update')
    case_path = LAB / 'home/projects/caseclone'
    assert case_path.is_dir() and os.path.samefile(case_path, clone), 'filesystem must support case aliases for this live probe'
    top = git(case_path, 'rev-parse', '--show-toplevel')
    pwd = run('bash', '-c', 'cd "$1" && pwd -P', '_', case_path).stdout.strip()
    LOG.append(f'case alias: git root={top}\nphysical cwd={pwd}\nsame directory={os.path.samefile(top, pwd)}\n')
    output = sync(case_path)
    actual = git(clone, 'rev-parse', 'HEAD')
    assert ': synced ' in output and actual == expected and actual != old
    LOG.append(f'clone before={old}\nclone after={actual}\nlocal origin cutoff={expected}\nfile.txt={(clone / "file.txt").read_text()}')

    alias = LAB / 'home/projects/clone-link'
    alias.symlink_to(clone, target_is_directory=True)
    expected = advance(work, 'symlink update')
    assert ': synced ' in sync('clone-link')
    assert git(clone, 'rev-parse', 'HEAD') == expected
    LOG.append(f'symlink clone after={expected}\n')

    (clone / 'file.txt').write_text('private uncommitted work\n')
    held = git(clone, 'rev-parse', 'HEAD')
    expected = advance(work, 'remote ahead but dirty')
    output = sync('clone-link')
    assert 'STUCK:' in output and 'uncommitted changes' in output
    assert git(clone, 'rev-parse', 'HEAD') == held
    assert (clone / 'file.txt').read_text() == 'private uncommitted work\n'
    LOG.append(f'dirty guard preserved HEAD={held} and file.txt=private uncommitted work; origin={expected}\n')

    enclosing = LAB / 'enclosing'
    run('git', 'clone', '--quiet', remote, enclosing, record=False)
    nested = enclosing / 'projects/stranded'
    nested.mkdir(parents=True)
    git(enclosing, 'config', 'user.name', 'Disposable test')
    git(enclosing, 'config', 'user.email', 'test@example.invalid')
    git(enclosing, 'branch', '--track', 'must-survive', 'origin/main')
    enclosing_before = git(enclosing, 'rev-parse', 'HEAD')
    tracking_before = git(enclosing, 'rev-parse', 'origin/main')
    advance(work, 'must not fetch through a nested directory')
    nested_env = dict(ENV, FM_HOME=str(enclosing))
    whole = run('bash', ROOT / 'bin/fm-fleet-sync.sh', env=nested_env).stdout
    single = run('bash', ROOT / 'bin/fm-fleet-sync.sh', 'stranded', env=nested_env).stdout
    assert 'skipped: not a clone root' in whole and 'skipped: not a clone root' in single
    assert git(enclosing, 'rev-parse', 'HEAD') == enclosing_before
    assert git(enclosing, 'rev-parse', 'origin/main') == tracking_before
    assert git(enclosing, 'rev-parse', 'must-survive') == enclosing_before
    LOG.append(f'enclosing HEAD unchanged={enclosing_before}; origin/main unchanged={tracking_before}; must-survive branch preserved\n')

    briefs = {}
    for mode in ['no-mistakes', 'direct-PR', 'local-only']:
        ident = 'ship-' + mode
        run('bash', ROOT / 'bin/fm-brief.sh', ident, 'disposable-project', '--mode', mode)
        briefs[ident] = LAB / 'home/data' / ident / 'brief.md'
    run('bash', ROOT / 'bin/fm-brief.sh', 'scout', 'disposable-project', '--scout')
    briefs['scout'] = LAB / 'home/data/scout/brief.md'
    run('bash', ROOT / 'bin/fm-brief.sh', 'mate', '--secondmate', '--no-projects',
        env=dict(ENV, FM_SECONDMATE_CHARTER='Supervise only assigned disposable work.'))
    briefs['mate'] = LAB / 'home/data/mate/brief.md'
    guidance = 'For a measured performance or evaluation claim, state what limits the result, rule out skipped, failed, cached, or untuned work, and record the run count and spread before reporting or acting on it.'
    for ident, path in briefs.items():
        text = path.read_text()
        # The generated brief is the intentional worker-agent instruction interface,
        # not implementation-source inspection or a claim about model interpretation.
        if ident != 'mate':
            assert guidance in text
            assert 'Firstmate owns task routing, isolation, supervision, and delivery.' in text
            assert 'Do not add a second review ceremony.' in text
            assert '/poteto-mode' not in text
            section = text.split('# Engineering inner loop\n', 1)[1].split('\n# ', 1)[0]
            LOG.append(f'Generated interface {ident}:\n# Engineering inner loop\n{section}\n')
        else:
            assert guidance not in text and '# Engineering inner loop' not in text
            LOG.append('Generated secondmate charter: no worker-only engineering inner loop or measured-claim rule.\n')
        (EVIDENCE / ('generated-' + ident + '.md')).write_text(text)
    previous = briefs['scout'].read_bytes()
    refused = run('bash', ROOT / 'bin/fm-brief.sh', 'scout', 'disposable-project', '--scout', ok=False)
    assert refused.returncode != 0 and briefs['scout'].read_bytes() == previous
    LOG.append('Existing brief refusal preserved the generated worker instructions byte-for-byte.\n')
    print('Real fleet-sync and brief CLI scenarios passed; product transcripts and generated briefs saved.')
finally:
    (EVIDENCE / 'isolated-cli.log').write_text('\n'.join(LOG))
