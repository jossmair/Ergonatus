"""Fresh installed binaries, isolated data; no user documents or processes changed."""
from pathlib import Path
import os,sys,time,json,uuid,subprocess,hashlib,tempfile,psutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from shared.ui.theme import APP_THEMES
TARGET=Path('C:/Users/Josselin/Desktop/Ergonatus')
OUT=ROOT/'output/audit/2026-10-26-visual-speed'
if '--after' in sys.argv:OUT=OUT/'after'
OUT.mkdir(parents=True,exist_ok=True);CAP=OUT/'captures';CAP.mkdir(exist_ok=True)
rows=[]
for key,item in APP_THEMES.items():
    relative=Path('Hub/Ergonatus.exe') if key=='ergonatus' else Path(item['folder'])/'runtime'/(item['folder']+'.exe')
    exe=TARGET/relative;local=ROOT/relative
    row=dict(app=key,name=item['name'],exe=str(exe),exists=exe.exists())
    if not exe.exists():rows.append(row);continue
    row['sha256']=hashlib.sha256(exe.read_bytes()).hexdigest();row['workspace_same']=local.exists() and hashlib.sha256(local.read_bytes()).hexdigest()==row['sha256']
    if key in ('ecrinator','pdfinator','redactor'):
        row['test']='not_launched_pending_native_protocol';rows.append(row);continue
    folder=Path(tempfile.mkdtemp(prefix='visual-speed-'));identity='VisualSpeed'+uuid.uuid4().hex
    env=os.environ.copy();env.update(USERDOMAIN=identity,ERGONATUS_DATA=str(folder),ERGONATUS_TEST_MODE='1',ERGONATUS_NO_HOTKEYS='1',ERGONATUS_BACKGROUND_START='1',TRANSCRI_DATA=str(folder/'transcri'),TRANSCRI_BUNDLE=str(TARGET/'ergoai/transcription'))
    cap=CAP/(key+'.png');args=['--smoke-test','--snapshot',str(cap)]
    if key=='claviernator':args=['--smoke-test','--no-hooks','--config-dir',str(folder)]
    if key=='precisionator':
        config=folder/'settings.json';config.write_text('{"enabled":false,"startup":false}');args=['--settings','--config',str(config),'--exit-after','2']
    if key=='transcrinator':args=['--ui-snapshot',str(cap)]
    start=time.perf_counter()
    with (OUT/(key+'.log')).open('wb') as log:
        p=subprocess.Popen([str(exe),*args],cwd=TARGET,env=env,stdout=log,stderr=log)
        first=None
        while p.poll() is None and time.perf_counter()-start<55:
            if first is None and cap.exists():first=time.perf_counter()-start
            time.sleep(.05)
        if p.poll() is None:p.kill();p.wait();row['timeout']=True
    row.update(exit=p.returncode,total_seconds=round(time.perf_counter()-start,3),snapshot_seconds=round(first,3) if first else None,capture=cap.exists(),test='installed_smoke')
    rows.append(row);(OUT/'executables.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(row,ensure_ascii=True),flush=True)
    # Each test has its own service identity. Remove its private model before
    # the next test so artificial copies cannot distort available memory.
    for service in psutil.process_iter(['exe']):
        try:
            if service.info['exe'] and Path(service.info['exe']).is_relative_to(TARGET/'ergoai') and service.environ().get('USERDOMAIN')==identity:
                service.terminate();service.wait(timeout=8)
        except (psutil.Error,OSError):pass
(OUT/'executables.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
