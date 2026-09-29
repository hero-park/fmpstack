import os, sys, json, pathlib, subprocess, shutil, time, base64, threading, http.server
W = pathlib.Path.cwd()
D = W / '.test-phase'
E = pathlib.Path('/Users/andrewpark/.no-mistakes/evidence/01M3QEYFTCVJ0545Y5RQ59CG6A')
B = D / 'tools'; B.mkdir(exist_ok=True)
for name in ['bash','git','node','jq','treehouse','tmux','pi','npm']:
    target = shutil.which(name)
    if target and not (B/name).exists(): (B/name).symlink_to(target)
real_tmux = shutil.which('tmux')
(B/'tmux').unlink()
(B/'tmux').write_text('#!/bin/bash\nexec '+real_tmux+' -S "'+str(D/'tmux.sock')+'" "$@"\n')
(B/'tmux').chmod(0o755)
(B/'opencode').write_text('#!/bin/bash\nexec npm exec --prefix "'+str(D/'vendor')+'" -- opencode "$@"\n')
(B/'opencode').chmod(0o755)
(D/'shell').write_text('#!/bin/bash\nexec /bin/bash --noprofile --norc -i\n'); (D/'shell').chmod(0o755)
env = {'PATH':str(B)+':/usr/bin:/bin:/usr/sbin:/sbin', 'HOME':str(D/'home'), 'TMPDIR':str(D/'tmp'), 'SHELL':str(D/'shell'), 'TERM':'xterm-256color', 'LANG':'en_US.UTF-8', 'GIT_CONFIG_GLOBAL':'/dev/null', 'GIT_CONFIG_SYSTEM':'/dev/null', 'GIT_AUTHOR_NAME':'Test', 'GIT_AUTHOR_EMAIL':'test@example.invalid', 'GIT_COMMITTER_NAME':'Test', 'GIT_COMMITTER_EMAIL':'test@example.invalid', 'XDG_CONFIG_HOME':str(D/'xdg/config'), 'XDG_DATA_HOME':str(D/'xdg/data'), 'XDG_CACHE_HOME':str(D/'xdg/cache'), 'XDG_STATE_HOME':str(D/'xdg/state'), 'PI_CODING_AGENT_DIR':str(D/'pi-config'), 'PI_OFFLINE':'1', 'PI_TELEMETRY':'0', 'FM_TEST_SKIP_ORPHAN_REAP':'1', 'FM_GATE_REFUSE_BYPASS':'1', 'FM_SPAWN_NO_GUARD':'1', 'TREEHOUSE_ROOT':str(D/'pool'), 'OPENCODE_DISABLE_AUTOUPDATE':'1', 'OPENCODE_DISABLE_MODELS_FETCH':'1', 'OPENCODE_DISABLE_DEFAULT_PLUGINS':'1'}
transcript = []
def run(args, cwd=W, extra=None, data=None, expected=0, timeout=90):
    ee=dict(env); ee.update(extra or {})
    p=subprocess.run([str(x) for x in args], cwd=cwd, env=ee, input=data, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    transcript.append({'command':' '.join(str(x) for x in args), 'cwd':str(cwd), 'exit':p.returncode, 'stdout':p.stdout, 'stderr':p.stderr})
    if expected is not None: assert p.returncode==expected, transcript[-1]
    return p

def init(repo):
    repo.mkdir(parents=True,exist_ok=True)
    run(['git','init','-q','-b','main',repo])
    (repo/'README.md').write_text('Disposable validation project\n')
    run(['git','add','.'], repo); run(['git','commit','-qm','fixture'],repo)

def origin(repo, remote):
    remote.parent.mkdir(parents=True,exist_ok=True)
    run(['git','clone','--quiet','--bare',repo,remote])
    run(['git','remote','add','origin',remote.as_uri()],repo)

scenarios=[]
def done(name, evidence):
    scenarios.append({'name':name,'result':'pass','live':True,'evidence':str(evidence),'reason':'Executed real product entrypoints against disposable local homes/endpoints.'})
    print(name,flush=True)
    (E/'live-progress.json').write_text(json.dumps(scenarios,indent=2))

def save(name, obj):
    path=E/name; path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)); return path

try:
    # True tmux + treehouse spawn handoff; raw command is the documented adapter
    # verification escape hatch and records the actual cwd of the launched worker.
    start=len(transcript)
    home=D/'worker-home'
    for sub in ['data','state','projects','config']: (home/sub).mkdir(parents=True,exist_ok=True)
    (home/'config/backlog-backend').write_text('manual\n')
    proj=home/'projects/app'; init(proj); origin(proj,D/'worker-origin.git')
    run(['tmux','-f','/dev/null','new-session','-d','-s','firstmate','-x','140','-y','40','-c',proj])
    run(['tmux','set-option','-g','default-shell',D/'shell'])
    spawned=[]
    def spawn(id, scout=False, model=None, effort=None, raw=None, expected=0):
        (home/'data'/id).mkdir(parents=True,exist_ok=True)
        (home/'data'/id/'brief.md').write_text('Delivery contract: mode=direct-PR\nDisposable validation; reply once and do not run tools.\n')
        cmd=[W/'bin/fm-spawn.sh',id,proj]
        if scout: cmd+=['--scout']
        else: cmd+=['--mode','direct-PR','--yolo','off']
        if raw: cmd+=[raw]
        else: cmd+=['--harness','opencode']
        if model: cmd+=['--model',model]
        if effort: cmd+=['--effort',effort]
        out=run(cmd,extra={'FM_HOME':str(home)},expected=expected,timeout=90)
        if out.returncode==0: spawned.append(id)
        return out
    for id,scout in [('live-ship',False),('live-scout',True)]:
        capture=E/(id+'-cwd.txt')
        raw="pwd > '"+str(capture)+"'; printf 'WORKER_CWD_CAPTURED\\n'"
        spawn(id,scout=scout,raw=raw)
        for _ in range(100):
            if capture.exists(): break
            time.sleep(.1)
        meta=dict(line.split('=',1) for line in (home/'state'/(id+'.meta')).read_text().splitlines() if '=' in line)
        assert capture.read_text().strip()==meta['worktree']
        pane=run(['tmux','capture-pane','-p','-t',meta['window'],'-S','-200']).stdout
        transcript.append({'task':id,'recorded_metadata':meta,'actual_worker_cwd':capture.read_text(),'pane':pane})
    meta_path=home/'state/live-ship.meta'; meta=dict(line.split('=',1) for line in meta_path.read_text().splitlines() if '=' in line)
    wt=pathlib.Path(meta['worktree']); (wt/'unlanded.txt').write_text('Preserve this replacement work\n')
    replacement=E/'replacement-cwd.txt'
    raw="pwd > '"+str(replacement)+"'; printf 'REPLACEMENT_CWD_CAPTURED\\n'"
    run([W/'bin/fm-spawn.sh','live-ship','--relaunch','--harness',raw],extra={'FM_HOME':str(home)})
    for _ in range(100):
        if replacement.exists(): break
        time.sleep(.1)
    assert replacement.read_text().strip()==str(wt) and (wt/'unlanded.txt').read_text()=='Preserve this replacement work\n'
    run(['tmux','send-keys','-t',meta['window'],'cd -- "'+str(proj)+'"','Enter']); time.sleep(.5)
    p=run([W/'bin/fm-spawn.sh','live-ship','--relaunch','--harness',raw],extra={'FM_HOME':str(home)},expected=1)
    assert 'not its recorded worktree' in p.stderr and (wt/'unlanded.txt').exists()
    evidence=save('worker-cwd-handoff.json',{'commands':transcript[start:],'unlanded_content':(wt/'unlanded.txt').read_text()})
    done('Launch fresh ship/scout and replacement workers in recorded copies, preserve unlanded work, and refuse a drifted relaunch',evidence)

    # Actual vendor config consumer sees the config passed by a genuine tmux
    # spawn. A local wrapper invokes debug config instead of using live billing.
    (B/'opencode').write_text('#!/bin/bash\nnpm exec --prefix "'+str(D/'vendor')+'" -- opencode debug config > "'+str(D/'opencode-effective')+'-$FM_EVIDENCE_TASK.json"\n')
    for id,model,effort,want in [('supported','openai/gpt-5.2-codex','xhigh','xhigh'),('unsupported','openai/gpt-5.1-codex','xhigh',None),('omitted','openai/gpt-5.2-codex',None,None)]:
        # tmux environment must carry the task's output key before its window opens.
        run(['tmux','set-environment','-g','FM_EVIDENCE_TASK',id])
        start=len(transcript)
        spawn('oc-'+id,model=model,effort=effort)
        path=D/('opencode-effective-'+id+'.json')
        for _ in range(200):
            if path.exists() and path.stat().st_size: break
            time.sleep(.1)
        config=json.loads(path.read_text())
        build=config.get('agent',{}).get('build',{})
        if want: assert build['model']==model and build['variant']==want
        else: assert 'variant' not in build
        save('opencode-'+id+'.json',{'commands':transcript[start:],'resolved_vendor_config':config})
    done('Spawn OpenCode with a verified effort pair, an unsupported pair, and omitted effort; real OpenCode resolves only the authorized variant',E/'opencode-supported.json')

finally:
    subprocess.run([real_tmux,'-S',str(D/'tmux.sock'),'kill-server'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    (E/'live-transcript.json').write_text(json.dumps(transcript,indent=2,ensure_ascii=False))
    (E/'live-scenarios.json').write_text(json.dumps(scenarios,indent=2,ensure_ascii=False))
