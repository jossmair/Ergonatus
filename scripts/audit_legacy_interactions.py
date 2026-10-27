from pathlib import Path
import os,sys,tempfile,uuid,time,json,subprocess
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/audit/current/interactions';reports=[]
folder=Path(tempfile.mkdtemp());config=folder/'precisionator.json';config.write_text('{"enabled":false,"startup":false}')
items=[('claviernator','Claviernator/runtime/Claviernator.exe',['--smoke-test','--no-hooks','--config-dir',str(folder/'keyboard')]),('precisionator','Precisionator/runtime/Precisionator.exe',['--settings','--config',str(config),'--exit-after','2']),('transcrinator','Transcrinator/runtime/Transcrinator.exe',['--ui-snapshot',str(OUT/'transcrinator-current.png')]),('redactor','Redactor/runtime/Redactor.exe',['--no-model','--minimized'])]
for key,path,args in items:
 record=OUT/(key+'.json');record.unlink(missing_ok=True);env=os.environ.copy();env.update(USERDOMAIN='MenuLegacy'+uuid.uuid4().hex,ERGONATUS_INTERACTION_AUDIT=str(record),ERGONATUS_NO_HOTKEYS='1',TRANSCRI_DATA=str(folder/'transcription'),TRANSCRI_BUNDLE=str(ROOT/'ergoai/transcription'),REDACTOR_DATA_DIR=str(folder/'redactor'),REDACTOR_TEST_INSTANCE='qa-'+uuid.uuid4().hex[:12]);p=subprocess.Popen([str(ROOT/path),*args],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));started=time.monotonic()
 try:
  while not record.exists() and p.poll() is None and time.monotonic()-started<35:time.sleep(.1)
  data=json.loads(record.read_text(encoding='utf-8')) if record.exists() else {};reports.append(dict(app=key,audit_available=record.exists(),menus=data.get('menus',[])));print(key,record.exists(),flush=True)
  if key!='redactor':
   try:p.wait(timeout=45)
   except subprocess.TimeoutExpired:pass
 finally:
  if p.poll() is None:p.terminate();p.wait(timeout=8)
(OUT/'legacy-menus.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
assert all(r['audit_available'] and r['menus'] for r in reports)
