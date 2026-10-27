"""Run the textbook export in an isolated headless office, without user profiles."""
from pathlib import Path
import subprocess,os,uuid,sys
root=Path(__file__).resolve().parents[1];program=Path('C:/Program Files/LibreOffice/program');pipe='ecr_reference_'+uuid.uuid4().hex;profile=root/'test-output'/pipe
source=root/'test-output/reference-sources/sesamath/manifest.json';out=root/'test-output/reference-sources/sesamath-vectors'
env=os.environ.copy();env['PYTHONHOME']=str(program/'python-core-3.12.14');env['PYTHONPATH']=str(program);env['PATH']=str(program)+os.pathsep+env['PATH'];env['PYTHONIOENCODING']='utf-8'
with (root/'test-output/sesamath-vector-export.log').open('a',encoding='utf-8') as log:
 lo=subprocess.Popen([str(program/'soffice.exe'),'-env:UserInstallation='+profile.as_uri(),'--headless','--norestore','--nodefault','--nofirststartwizard','--accept=pipe,name='+pipe+';urp;StarOffice.ServiceManager'],env=env,creationflags=subprocess.CREATE_NO_WINDOW)
 try:
  result=subprocess.run([str(program/'python.exe'),str(root/'scripts/lo_shape_worker.py'),pipe,str(source),str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1200,creationflags=subprocess.CREATE_NO_WINDOW)
  sys.exit(result.returncode)
 finally:
  if lo.poll() is None:lo.terminate()
