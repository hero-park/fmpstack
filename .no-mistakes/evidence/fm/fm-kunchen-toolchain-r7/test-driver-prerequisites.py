exec(open('.test-phase/live.py').read().split('\ncode=D/')[0])
code=D/'prereq-code'; shutil.copytree(D/'code-root/bin',code/'bin',dirs_exist_ok=True)
home=D/'prereq-home'
for sub in ['data','state','projects','config']: (home/sub).mkdir(parents=True,exist_ok=True)
project=home/'projects/app'; init(project)
original=(W/'bin/fm-opencode-variants.json').read_bytes()
missing=D/'missing-jq'; missing.mkdir(exist_ok=True)
for path in B.iterdir():
    if path.name!='jq':
        target=missing/path.name
        if not target.exists(): target.symlink_to(path)
for name in ['env','dirname','basename','mktemp','sed','tr','cut','grep','head','sleep','seq','shasum','ps','date','cksum','rm','mkdir','cat','awk','tail','wc','find','stat','perl','realpath','uname','xargs','touch','sort','mv','chmod','cp','tee','pgrep','ln','readlink','rmdir','expr','id','dd','getconf','ls']:
    tool=shutil.which(name)
    if tool and not (missing/name).exists(): (missing/name).symlink_to(tool)
results=[]
for failure in ['missing-parser','missing-data','unreadable-data','corrupt-json','corrupt-shape']:
    id='preflight-'+failure
    (home/'data'/id).mkdir(); (home/'data'/id/'brief.md').write_text('Delivery contract: mode=direct-PR\nDisposable test.\n')
    table=code/'bin/fm-opencode-variants.json'; table.write_bytes(original)
    extra={'FM_HOME':str(home)}
    if failure=='missing-parser': extra['PATH']=str(missing)
    elif failure=='missing-data': table.unlink()
    elif failure=='unreadable-data': table.chmod(0)
    elif failure=='corrupt-json': table.write_text('{broken\n')
    elif failure=='corrupt-shape': table.write_text('{"openai/gpt-5.2-codex":null}\n')
    windows_before=run(['tmux','list-windows','-a','-F','#{window_id}'],expected=None).stdout
    p=run([code/'bin/fm-spawn.sh',id,project,'--mode','direct-PR','--yolo','off','--harness','opencode','--model','openai/gpt-5.2-codex','--effort','xhigh'],extra=extra,expected=1)
    windows_after=run(['tmux','list-windows','-a','-F','#{window_id}'],expected=None).stdout
    if table.exists(): table.chmod(0o600)
    expected={'missing-parser':'jq is required','missing-data':'support data is missing','unreadable-data':'support data is unreadable','corrupt-json':'variant lookup failed','corrupt-shape':'corrupt OpenCode variant support data'}[failure]
    assert expected in p.stderr and windows_after==windows_before and not (home/'state'/(id+'.meta')).exists(), {'failure':failure, 'stderr':p.stderr,'stdout':p.stdout,'before':windows_before,'after':windows_after}
    results.append({'failure':failure,'diagnostic':p.stderr,'endpoint_inventory_unchanged':windows_after==windows_before,'metadata_exists':(home/'state'/(id+'.meta')).exists()})
(code/'bin/fm-opencode-variants.json').write_bytes(original)
(E/'opencode-prerequisites.json').write_text(json.dumps({'commands':transcript,'observations':results},indent=2))
print('OpenCode missing parser, missing/unreadable/corrupt support data refuse before endpoint creation and metadata publication')
# Execute the real bootstrap profile validator through its public CLI.
transcript.clear()
config=home/'config/crew-dispatch.json'
positive={'rules':[{'when':'positive','use':[{'harness':'opencode','model':'anthropic/claude-sonnet-4-5','effort':'high'},{'harness':'opencode','model':'openai/gpt-5.2-codex','effort':'xhigh'}]}],'default':[{'harness':'opencode','model':'openai/gpt-5.1-codex','effort':'high'}]}
config.write_text(json.dumps(positive))
p=run([W/'bin/fm-bootstrap.sh'],extra={'FM_HOME':str(home),'FM_BOOTSTRAP_DETECT_ONLY':'1','FM_BOOTSTRAP_NETWORK':'skip'})
assert 'CREW_DISPATCH:' not in p.stdout
positive['default'][0]['effort']='xhigh'; config.write_text(json.dumps(positive))
p=run([W/'bin/fm-bootstrap.sh'],extra={'FM_HOME':str(home),'FM_BOOTSTRAP_DETECT_ONLY':'1','FM_BOOTSTRAP_NETWORK':'skip'})
assert 'CREW_DISPATCH: invalid config/crew-dispatch.json - invalid effort: opencode:xhigh' in p.stdout
(E/'bootstrap-profiles.json').write_text(json.dumps({'commands':transcript},indent=2))
print('Bootstrap accepts verified OpenCode rule/default arrays and diagnoses unsupported effort')
