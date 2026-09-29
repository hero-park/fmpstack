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

code=D/'code-root'; code.mkdir(exist_ok=True)
p=subprocess.Popen(['git','archive','HEAD'],cwd=W,stdout=subprocess.PIPE)
subprocess.run(['tar','-xf','-','-C',str(code)],stdin=p.stdout,check=True); assert p.wait()==0
run(['git','init','-q','-b','main',code]); run(['git','add','.'],code); run(['git','commit','-qm','current tracked product'],code)
origin(code,D/'firstmate.git')
scenarios=[]
def done(name, evidence):
    scenarios.append({'name':name,'result':'pass','live':True,'evidence':str(evidence),'reason':'Executed real product entrypoints against disposable local homes/endpoints.'})
    print(name,flush=True)
    (E/'live-progress.json').write_text(json.dumps(scenarios,indent=2))

def save(name, obj):
    path=E/name; path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)); return path

try:
    # Public project lookup and complete local provisioning, including reseed.
    start=len(transcript)
    parent=D/'registry-parent'; (parent/'data').mkdir(parents=True,exist_ok=True); (parent/'state').mkdir(); (parent/'projects').mkdir()
    rows=['- foo bar [local-only] - excluded longer neighbor','- foo [direct-PR] - selected short name','- foo bar baz plus [local-only] - excluded longer multiword neighbor','- foo bar baz [direct-PR +yolo] - selected multiword name','- regex.name+ [direct-PR] - literal punctuation','- regexXnameee [local-only] - regex neighbor']
    (parent/'data/projects.md').write_text('\n'.join(rows)+'\n')
    for name in ['foo','foo bar baz','regex.name+']:
        repo=parent/'projects'/name; init(repo); origin(repo,D/'origins'/(name+'.git'))
    for name,want in [('foo','direct-PR off'),('foo bar baz','direct-PR on'),('foo bar','local-only off'),('regex.name+','direct-PR off')]:
        p=run([W/'bin/fm-project-mode.sh',name],extra={'FM_HOME':str(parent)}); assert p.stdout.strip()==want
    child=D/'registry-child'; se={'FM_HOME':str(parent),'FM_ROOT_OVERRIDE':str(code),'FM_SECONDMATE_CHARTER':'Disposable registry test.','FM_SECONDMATE_SCOPE':'Disposable registry scope.'}
    run([W/'bin/fm-home-seed.sh','names',child,'foo','foo bar baz','regex.name+'],extra=se)
    assert (child/'data/projects.md').read_text().splitlines()==[rows[1],rows[3],rows[4]]
    with (child/'data/projects.md').open('a') as f: f.write(rows[0]+'\n'+rows[2]+'\n')
    run([W/'bin/fm-home-seed.sh','names',child,'foo','foo bar baz','regex.name+'],extra=se)
    state=(child/'data/projects.md').read_text()
    for row in [rows[0],rows[1],rows[2],rows[3],rows[4]]: assert state.splitlines().count(row)==1
    evidence=save('registry-provisioning.json',{'commands':transcript[start:],'persisted_child_registry':state})
    done('Select and reseed literal short, multiword, and punctuation project names without stealing neighbor delivery modes',evidence)

    # Real receiving-host public protocol, no SSH/account/shared host needed.
    start=len(transcript)
    b64=lambda s: base64.b64encode(s.encode()).decode()
    def manifest(id, records):
        return 'schema=fm-remote-home-provision.v1\nid_b64='+b64(id)+'\ncharter_b64='+b64('Disposable remote receiver validation.\n')+'\nproject_count='+str(len(records))+'\n'+''.join('project='+'|'.join(b64(v) for v in rec)+'\n' for rec in records)
    remote=D/'receiver-home'
    payload=manifest('receiver',[('foo',(D/'origins/foo.git').as_uri(),rows[1],'direct-PR')])
    run([W/'bin/fm-remote-home-provision.sh'],extra={'FM_ROOT_OVERRIDE':str(code),'FM_HOME':str(remote)},data=payload)
    assert (remote/'data/projects.md').read_text().splitlines()==[rows[1]]
    for name,want in [('foo','direct-PR off')]:
        assert run([W/'bin/fm-project-mode.sh',name],extra={'FM_HOME':str(remote)}).stdout.strip()==want
    bad=D/'receiver-bad'
    payload=manifest('receiver-bad',[('foo',(D/'origins/foo.git').as_uri(),rows[0],'direct-PR')])
    p=run([W/'bin/fm-remote-home-provision.sh'],extra={'FM_ROOT_OVERRIDE':str(code),'FM_HOME':str(bad)},data=payload,expected=1)
    assert 'registry line is malformed' in p.stderr and not bad.exists()
    evidence=save('remote-receiver.json',{'commands':transcript[start:],'persisted_registry':(remote/'data/projects.md').read_text(),'mismatched_home_exists':bad.exists()})
    done('Provision the exact short remote project record and reject a prefix-collision manifest with rollback',evidence)

    # Genuine primary checkout: invoke hook under a persistent real Pi ancestry.
    # The HTTP endpoint is disposable data, not a replacement for Firstmate/Pi.
    class Handler(http.server.BaseHTTPRequestHandler):
        requests=[]
        def log_message(self,*args): pass
        def do_POST(self):
            data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            Handler.requests.append({'path':self.path,'body':data})
            message='DISPOSABLE_ENDPOINT_ACK'
            events=[{'id':'validation','object':'chat.completion.chunk','created':int(time.time()),'model':data.get('model','deterministic'),'choices':[{'index':0,'delta':{'role':'assistant','content':message},'finish_reason':None}]},{'id':'validation','object':'chat.completion.chunk','created':int(time.time()),'model':data.get('model','deterministic'),'choices':[{'index':0,'delta':{},'finish_reason':'stop'}]}]
            self.send_response(200); self.send_header('Content-Type','text/event-stream'); self.end_headers()
            for e in events: self.wfile.write(('data: '+json.dumps(e)+'\n\n').encode())
            self.wfile.write(b'data: [DONE]\n\n')
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    cfg=D/'pi-config'; cfg.mkdir(exist_ok=True)
    (cfg/'models.json').write_text(json.dumps({'providers':{'evidence-local':{'baseUrl':f'http://127.0.0.1:{server.server_port}/v1','api':'openai-completions','apiKey':'disposable','models':[{'id':'deterministic','reasoning':False,'input':['text'],'contextWindow':65536,'maxTokens':64}]}}}))
    primary=D/'fresh-primary'; run(['git','clone','--quiet',code,primary])
    assert not (primary/'state').exists() or not list((primary/'state').iterdir())
    if (primary/'state').exists(): shutil.rmtree(primary/'state')
    start=len(transcript)
    ee={'FM_ROOT_OVERRIDE':str(primary),'FM_HOME':str(primary),'FM_BOOTSTRAP_DETECT_ONLY':'1','FM_BOOTSTRAP_NETWORK':'skip'}
    args=['pi','--print','--approve','--no-session','--no-context-files','--no-extensions','--no-skills','--no-prompt-templates','--no-tools','-e',W/'.pi/extensions/fm-primary-turnend-guard.ts','--model','evidence-local/deterministic','--thinking','off','Startup evidence probe']
    p=run(args,cwd=primary,extra=ee,timeout=90)
    assert (primary/'state').is_dir() and 'DISPOSABLE_ENDPOINT_ACK' in p.stdout
    texts=json.dumps(Handler.requests[-1]['body']['messages'],ensure_ascii=False)
    assert 'SESSION START - '+str(primary) in texts and 'NEXT STEP' in texts
    evidence=save('pi-fresh-primary.json',{'commands':transcript[start:],'provider_request':Handler.requests[-1],'state_created':(primary/'state').is_dir(),'completion_file':(primary/'state/.session-start-complete').read_text() if (primary/'state/.session-start-complete').exists() else None})
    done('Open a fresh primary in real Pi and receive the full session-start digest after automatic state creation',evidence)

    start=len(transcript)
    readonly=D/'readonly-primary'; run(['git','clone','--quiet',code,readonly])
    if (readonly/'state').exists(): shutil.rmtree(readonly/'state')
    readonly.chmod(0o500)
    try:
        ee={'FM_HOME':str(readonly),'FM_ROOT_OVERRIDE':str(readonly)}
        plain=run([W/'bin/fm-sessionstart-run.sh','--source','startup'],extra=ee,data='')
        assert 'startup could not create the state directory' in plain.stdout and not plain.stderr
        cursor=run([W/'bin/fm-sessionstart-cursor.sh','--source','startup'],extra=ee,data='')
        ctx=json.loads(cursor.stdout); assert ctx['additional_context']==plain.stdout.strip()
        pi=run(args,cwd=readonly,extra=ee,timeout=90)
        texts=json.dumps(Handler.requests[-1]['body']['messages'],ensure_ascii=False)
        assert texts.count('startup could not create the state directory')==1 and 'FIRSTMATE_OP: v1 session-start:' in texts
        duplicate=run([W/'bin/fm-sessionstart-run.sh'],extra=ee,data='{"cursor_version":"fixture","source":"startup"}')
        assert not duplicate.stdout and not duplicate.stderr and not (readonly/'state').exists()
        evidence=save('startup-failure-consumers.json',{'commands':transcript[start:],'cursor_additional_context':ctx,'pi_provider_request':Handler.requests[-1],'state_exists':(readonly/'state').exists()})
        done('Make primary state creation fail and receive one visible failure in hook stdout, Cursor context, and real Pi provider input',evidence)
    finally: readonly.chmod(0o700)

    # Scope adversary: gate env and an ordinary linked copy cannot create state.
    start=len(transcript)
    base=D/'scope-base'; run(['git','clone','--quiet',code,base])
    linked=D/'scope-linked'; run(['git','worktree','add','--quiet','-b','scope',linked],cwd=base)
    if (linked/'state').exists(): shutil.rmtree(linked/'state')
    for extra in ({'FM_GATE_REFUSE_BYPASS':'0'}, {'FM_GATE_REFUSE_BYPASS':'0','NO_MISTAKES_GATE':'1'}):
        p=run([W/'bin/fm-sessionstart-run.sh','--source','startup'],extra={'FM_ROOT_OVERRIDE':str(linked),'FM_HOME':str(linked),**extra},data='')
        assert not p.stdout and not p.stderr and not (linked/'state').exists()
    (linked/'.fm-secondmate-home').write_text('scope-secondmate\n')
    gate=run([W/'bin/fm-sessionstart-run.sh','--source','startup'],extra={'FM_ROOT_OVERRIDE':str(linked),'FM_HOME':str(linked),'FM_GATE_REFUSE_BYPASS':'0','NO_MISTAKES_GATE':'1'},data='')
    assert not gate.stdout and not (linked/'state').exists()
    run(args,cwd=linked,extra={'FM_ROOT_OVERRIDE':str(linked),'FM_HOME':str(linked),'FM_GATE_REFUSE_BYPASS':'0','FM_BOOTSTRAP_DETECT_ONLY':'1'},timeout=90)
    texts=json.dumps(Handler.requests[-1]['body']['messages'])
    assert (linked/'state').is_dir() and 'SESSION START - '+str(linked) in texts
    evidence=save('startup-scope.json',{'commands':transcript[start:],'marked_secondmate_provider_request':Handler.requests[-1],'secondmate_state_created':(linked/'state').is_dir()})
    done('Keep gate and unmarked linked copies silent while allowing a marked secondmate to create its own state',evidence)
    server.shutdown()

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
