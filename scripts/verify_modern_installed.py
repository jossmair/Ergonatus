from pathlib import Path
import os,sys,subprocess,tempfile,uuid,json,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from shared.ui.theme import APP_THEMES
rows=[]
for key in ['ergonatus','lector','scanator','applinator','temporator','concentrator','calculinator','communicator','memorinator','planinator','organisator','traductor','corrector']:
    folder='Hub' if key=='ergonatus' else APP_THEMES[key]['folder']
    exe=ROOT/folder/('Ergonatus.exe' if key=='ergonatus' else 'runtime/'+folder+'.exe')
    env=os.environ.copy();env.update(ERGONATUS_TEST_MODE='1',ERGONATUS_NO_HOTKEYS='1',ERGONATUS_BACKGROUND_START='1',ERGONATUS_DATA=tempfile.mkdtemp(prefix='modern-exe-'),USERDOMAIN='ModernExe'+uuid.uuid4().hex)
    started=time.monotonic()
    try:
        r=subprocess.run([str(exe),'--smoke-test'],cwd=ROOT,env=env,timeout=115,capture_output=True)
        row=dict(app=key,exit=r.returncode,seconds=round(time.monotonic()-started,1),output=(r.stdout+r.stderr).decode(errors='replace')[-2000:])
    except subprocess.TimeoutExpired:row=dict(app=key,exit='timeout')
    rows.append(row);print(json.dumps(row),flush=True)
(ROOT/'docs/maintenance/modern-installed-smokes-2026-10-24.json').write_text(json.dumps(rows,indent=2))
sys.exit(0 if all(r['exit']==0 for r in rows) else 1)
