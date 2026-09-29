exec(open('.test-phase/live.py').read().split('\ncode=D/')[0])
home=D/'worker-home'; project=home/'projects/cwd-adversary'; init(project); origin(project,D/'cwd-adversary-origin.git')
id='cwd-adversary'; (home/'data'/id).mkdir(parents=True,exist_ok=True); (home/'data'/id/'brief.md').write_text('Delivery contract: mode=direct-PR\nDisposable prelaunch refusal.\n')
rc=D/'adversarial-rc'; rc.write_text("cd() { builtin cd '"+str(project)+"'; }\n")
(D/'shell').write_text('#!/bin/bash\nexec /bin/bash --noprofile --rcfile "'+str(rc)+'" -i\n')
marker=E/'must-not-launch.txt'
try:
    run(['tmux','-f','/dev/null','new-session','-d','-s','firstmate','-x','140','-y','40','-c',project])
    run(['tmux','set-option','-g','default-shell',D/'shell'])
    raw="printf 'WRONG_CWD_LAUNCH' > '"+str(marker)+"'"
    p=run([W/'bin/fm-spawn.sh',id,project,'--mode','direct-PR','--yolo','off',raw],extra={'FM_HOME':str(home)},expected=1)
    assert 'not its recorded worktree' in p.stderr and not marker.exists() and not (home/'state'/(id+'.meta')).exists()
    pane=run(['tmux','capture-pane','-p','-t','firstmate:fm-'+id,'-S','-200']).stdout
    actual=run(['tmux','display-message','-p','-t','firstmate:fm-'+id,'#{pane_current_path}']).stdout
    assert actual.strip()==str(project)
    (E/'fresh-worker-cwd-refusal.json').write_text(json.dumps({'commands':transcript,'actual_pane_cwd':actual,'pane':pane,'launch_marker_exists':marker.exists(),'metadata_exists':(home/'state'/(id+'.meta')).exists(),'adversary':'Disposable shell rc redirects cd away from the acquired worktree; real tmux supplies the observed cwd.'},indent=2))
    print('Fresh spawn refuses when an adversarial shell redirects its worktree handoff; no harness starts or metadata publishes')
finally:
    (D/'shell').write_text('#!/bin/bash\nexec /bin/bash --noprofile --norc -i\n')
    subprocess.run([real_tmux,'-S',str(D/'tmux.sock'),'kill-server'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
