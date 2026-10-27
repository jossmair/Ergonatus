from pathlib import Path
import os,sys,subprocess,tempfile,uuid,json,time,hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/audit/current';baseline=json.loads((OUT/'versions.json').read_text(encoding='utf-8'));rows=[]
folder=Path(tempfile.mkdtemp(prefix='current-legacy-audit-'));config=folder/'precisionator.json';config.write_text('{"enabled":false,"startup":false}')
for key,args in [('claviernator',['--smoke-test','--no-hooks','--config-dir',str(folder/'claviernator')]),('precisionator',['--settings','--config',str(config),'--exit-after','2']),('transcrinator',['--ui-snapshot',str(OUT/'captures/transcrinator.png')])]:
    item=next(x for x in baseline['apps'] if x['app']==key);exe=ROOT/item['executable'];assert hashlib.sha256(exe.read_bytes()).hexdigest()==item['sha256']
    env=os.environ.copy();env.update(USERDOMAIN='CurrentLegacy'+uuid.uuid4().hex,TRANSCRI_DATA=str(folder/'Transcrinator'),TRANSCRI_BUNDLE=str(ROOT/'ergoai/transcription'),ERGONATUS_NO_HOTKEYS='1')
    start=time.monotonic()
    try:r=subprocess.run([str(exe),*args],cwd=ROOT,env=env,capture_output=True,timeout=70);row=dict(app=key,exit=r.returncode,seconds=round(time.monotonic()-start,2),output=(r.stdout+r.stderr).decode(errors='replace')[-2000:],sha256=item['sha256'])
    except subprocess.TimeoutExpired:row=dict(app=key,exit='timeout',sha256=item['sha256'])
    rows.append(row);(OUT/'legacy.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(row),flush=True)
