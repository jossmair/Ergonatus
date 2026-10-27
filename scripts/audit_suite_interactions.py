"""Fresh UI/menu audit of exact installed Qt executables, with isolated data."""
from pathlib import Path
import sys,os,json,time,uuid,tempfile,subprocess,hashlib,psutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from shared.ui.theme import APP_THEMES
OUT=ROOT/'output/audit/current/interactions';OUT.mkdir(exist_ok=True);reports=[]
for key,item in APP_THEMES.items():
 if key in ('ergonatus','claviernator','precisionator','transcrinator','redactor','ecrinator','pdfinator'):continue
 exe=ROOT/item['folder']/'runtime'/(item['folder']+'.exe');env=os.environ.copy();identity='InteractionAudit'+uuid.uuid4().hex;record=OUT/(key+'.json');record.unlink(missing_ok=True)
 env.update(USERDOMAIN=identity,ERGONATUS_DATA=tempfile.mkdtemp(),ERGONATUS_TEST_MODE='1',ERGONATUS_NO_HOTKEYS='1',ERGONATUS_INTERACTION_AUDIT=str(record));p=subprocess.Popen([str(exe),'--minimized'],env=env,cwd=ROOT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));started=time.monotonic()
 try:
  while not record.exists() and p.poll() is None and time.monotonic()-started<18:time.sleep(.1)
  data=json.loads(record.read_text(encoding='utf-8')) if record.exists() else {};menus=data.get('menus',[]);labels=sum(menus,[]);ok=any('Ouvrir '+item['name']==v for v in labels) and any('À quoi sert '+item['name'] in v for v in labels)
  reports.append(dict(app=key,ok=ok,exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),menus=menus));print(key,ok,flush=True)
  subprocess.run([str(exe),'--quit-running'],env=env,cwd=ROOT,capture_output=True,timeout=8)
 finally:
  try:p.wait(timeout=8)
  except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
  for process in psutil.process_iter(['exe']):
   try:
    if process.info['exe'] and Path(process.info['exe']).is_relative_to(ROOT/'ergoai') and process.environ().get('USERDOMAIN')==identity:process.terminate();process.wait(timeout=5)
   except (psutil.Error,ValueError):pass
 (OUT/'installed-menus.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
assert all(r['ok'] for r in reports)
