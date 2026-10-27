"""Real inference smoke, isolated from the user's language host."""
from pathlib import Path
import os,sys,tempfile,uuid,subprocess,threading,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.update(ERGONATUS_DATA=tempfile.mkdtemp(),USERDOMAIN='LearningModel'+uuid.uuid4().hex,ERGONATUS_NO_HOTKEYS='1')
log=(ROOT/'output/audit/current/learning-real-host.log').open('w',encoding='utf-8')
p=subprocess.Popen([str(ROOT/'ergoai/proofreading/runtime/ErgoProofread.exe')],cwd=ROOT,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
try:
 from ergoai.learning import ask
 results={}
 for key,op,text in [('hint','explain','Léa a 3 boîtes de 4 billes. Combien a-t-elle de billes au total ?')]:
  results[key]=ask(op,text,threading.Event(),level='Primaire')
 (ROOT/'output/audit/current/learning-real-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(results,ensure_ascii=False))
finally:
 p.terminate();p.wait(timeout=15);log.close()
 import psutil
 for child in psutil.Process().children():
  try:
   if Path(child.exe()).resolve()==(ROOT/'ergoai/runtime/ErgoAI.exe').resolve():child.terminate();child.wait(timeout=15)
  except (psutil.Error,OSError):pass
