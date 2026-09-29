exec(open('.test-phase/live.py').read().split('\ncode=D/')[0])
prior=D/'prior'; prior.mkdir(exist_ok=True)
p=subprocess.Popen(['git','archive','ec309ab','bin'],cwd=W,stdout=subprocess.PIPE)
subprocess.run(['tar','-xf','-','-C',str(prior)],stdin=p.stdout,check=True); assert p.wait()==0
parent=D/'registry-parent'
old=D/'prior-project-mode.sh'; old.write_bytes(subprocess.check_output(['git','show','dd087d98a21fec8254a5b5c3740291df83fb12f3:bin/fm-project-mode.sh'],cwd=W)); old.chmod(0o755)
before=run([old,'foo'],extra={'FM_HOME':str(parent)}).stdout.strip()
after=run([W/'bin/fm-project-mode.sh','foo'],extra={'FM_HOME':str(parent)}).stdout.strip()
assert before=='no-mistakes off' and after=='direct-PR off'
(B/'opencode').write_text('#!/bin/bash\nnpm exec --prefix "'+str(D/'vendor')+'" -- opencode debug config > "'+str(E/'prior-opencode-config.json')+'"\n')
home=D/'prior-home'
for sub in ['data','state','config','projects']: (home/sub).mkdir(parents=True,exist_ok=True)
project=home/'projects/prior-app'; init(project); origin(project,D/'prior-origin.git')
id='prior-parser'; (home/'data'/id).mkdir(); (home/'data'/id/'brief.md').write_text('Delivery contract: mode=direct-PR\nDisposable before-fix check.\n')
try:
    run(['tmux','-f','/dev/null','new-session','-d','-s','firstmate','-x','140','-y','40','-c',project])
    run(['tmux','set-option','-g','default-shell',D/'shell'])
    p=run([prior/'bin/fm-spawn.sh',id,project,'--harness','opencode','--model','openai/gpt-5.2-codex','--effort','xhigh','--mode','direct-PR','--yolo','off'],extra={'FM_HOME':str(home),'PATH':str(D/'missing-jq')})
    meta=(home/'state'/(id+'.meta')).read_text()
    pane=run(['tmux','capture-pane','-p','-J','-t','firstmate:fm-'+id,'-S','-120']).stdout
    import re
    carrier=re.search(r"OPENCODE_CONFIG_CONTENT='([^']*)'",pane)
    assert carrier, pane
    config=json.loads(carrier.group(1))
    assert 'effort=xhigh' in meta and config=={'permission':{'*':'allow'}}
    (E/'before-after-regressions.json').write_text(json.dumps({'commands':transcript,'registry_before':before,'registry_after':after,'prior_parser_failure_launched':True,'prior_metadata':meta,'prior_emitted_launch_config':config,'prior_pane':pane,'target_prerequisite_evidence':str(E/'opencode-prerequisites.json')},indent=2))
    print('Reproduced pre-fix registry prefix collision and silent OpenCode parser failure; target behavior is separately verified')
finally:
    subprocess.run([real_tmux,'-S',str(D/'tmux.sock'),'kill-server'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
