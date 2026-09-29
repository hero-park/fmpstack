exec(open('.test-phase/live.py').read().split('\ncode=D/')[0])
requests=[]; release=threading.Event()
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_POST(self):
        data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        requests.append({'path':self.path,'body':data})
        if not release.wait(50): return
        self.send_response(200); self.send_header('Content-Type','text/event-stream'); self.end_headers()
        for delta,finish in [({'role':'assistant','content':'DISPOSABLE_PI_WORKER_ACK'},None),({},'stop')]:
            event={'id':'local','object':'chat.completion.chunk','created':int(time.time()),'model':data['model'],'choices':[{'index':0,'delta':delta,'finish_reason':finish}]}
            self.wfile.write(('data: '+json.dumps(event)+'\n\n').encode())
        self.wfile.write(b'data: [DONE]\n\n')
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
cfg=D/'pi-config'; cfg.mkdir(exist_ok=True)
(cfg/'models.json').write_text(json.dumps({'providers':{'evidence-local':{'baseUrl':f'http://127.0.0.1:{server.server_port}/v1','api':'openai-completions','apiKey':'disposable','models':[{'id':'deterministic','reasoning':False,'input':['text'],'contextWindow':65536,'maxTokens':64}]}}}))
home=D/'worker-home'; proj=home/'projects/app'; id='live-pi-lifecycle'
(home/'data'/id).mkdir(parents=True,exist_ok=True); (home/'data'/id/'brief.md').write_text('Delivery contract: mode=direct-PR\nDisposable lifecycle check. Do not use any tools.\n')
state=home/'state'; busy=state/(id+'.busy-state')
def wait(predicate,message):
    for _ in range(300):
        if predicate(): return
        time.sleep(.1)
    raise AssertionError(message)
try:
    run(['tmux','-f','/dev/null','new-session','-d','-s','firstmate','-x','140','-y','40','-c',proj])
    run(['tmux','set-option','-g','default-shell',D/'shell'])
    run([W/'bin/fm-spawn.sh',id,proj,'--mode','direct-PR','--yolo','off','--harness','pi','--model','evidence-local/deterministic'],extra={'FM_HOME':str(home)})
    wait(lambda:len(requests)>0,'Pi never reached the disposable endpoint')
    wait(lambda:busy.exists() and 'state=busy source=pi-ext' in busy.read_text(),'real Pi did not publish agent_start busy')
    during=busy.read_text(); release.set()
    wait(lambda:'state=idle source=pi-ext' in busy.read_text(),'real Pi did not settle idle')
    idle=busy.read_text(); wait(lambda:(state/(id+'.turn-ended')).exists(),'Pi lost turn-end notification')
    meta=dict(line.split('=',1) for line in (state/(id+'.meta')).read_text().splitlines() if '=' in line)
    pane=run(['tmux','capture-pane','-p','-t',meta['window'],'-S','-200']).stdout
    gen=run([W/'bin/fm-busy-event.sh','arm',state,id,'--state','busy','--source','replacement-check','--event','replacement']).stdout.strip()
    replacement=busy.read_text()
    run(['tmux','send-keys','-t',meta['window'],'-l','Stale incarnation probe.'])
    run(['tmux','send-keys','-t',meta['window'],'Enter'])
    wait(lambda:len(requests)>1,'old Pi process did not run the stale incarnation probe')
    time.sleep(1)
    assert busy.read_text()==replacement, 'old generated extension overwrote the new incarnation'
    (E/'pi-worker-lifecycle.json').write_text(json.dumps({'commands':transcript,'provider_requests':requests,'during_request':during,'after_settlement':idle,'replacement_state_unchanged':busy.read_text(),'new_generation':gen,'turn_end_notification':True,'actual_tmux_grid':'140x40','pane':pane},indent=2))
    (E/'pi-worker-terminal.txt').write_text(pane)
    print('Real Pi worker published busy/idle semantic edges, turn-end notification, and rejected stale-generation callbacks')
finally:
    release.set(); server.shutdown()
    subprocess.run([real_tmux,'-S',str(D/'tmux.sock'),'kill-server'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
