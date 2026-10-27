from pathlib import Path
import os,sys,tempfile,uuid,subprocess,json,time
ROOT=Path(__file__).resolve().parents[1];env=os.environ.copy();env.update(ERGONATUS_DATA=tempfile.mkdtemp(),ERGONATUS_NO_HOTKEYS='1',ERGONATUS_TEST_MODE='1',USERDOMAIN='LearningPackaged'+uuid.uuid4().hex);reports=[]
for name,path in [('Dictionnator','Dictionnator/runtime/Dictionnator.exe'),('Explicator','Explicator/runtime/Explicator.exe'),('Tablinator','Tablinator/runtime/Tablinator.exe'),('Ergonatus','Hub/Ergonatus.exe')]:
 start=time.monotonic();result=subprocess.run([str(ROOT/path),'--smoke-test','--snapshot',str(ROOT/'output/audit/current/captures'/(name.lower()+'-installed.png'))],env=env,cwd=ROOT,capture_output=True,timeout=35);report=dict(app=name,exit=result.returncode,seconds=round(time.monotonic()-start,2));reports.append(report);print(report,flush=True)
 if result.returncode:raise RuntimeError(name+' '+result.stderr.decode(errors='replace')[-500:])
(ROOT/'output/audit/current/learning-installed-tests.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
