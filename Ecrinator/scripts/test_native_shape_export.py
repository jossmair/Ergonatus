from pathlib import Path
import subprocess,os,uuid,json
root=Path('.').resolve();program=Path('C:/Program Files/LibreOffice/program');pipe='ecr_reference_'+uuid.uuid4().hex;profile=root/'test-output'/pipe
source=root/'test-output/reference-sources/sesamath-geometry-1.odt';out=root/'test-output/reference-sources/sesamath-uno-test'
env=os.environ.copy();env['PYTHONHOME']=str(program/'python-core-3.12.14');env['PYTHONPATH']=str(program);env['PATH']=str(program)+os.pathsep+env['PATH'];env['PYTHONIOENCODING']='utf-8'
lo=subprocess.Popen([str(program/'soffice.exe'),'-env:UserInstallation='+profile.as_uri(),'--headless','--norestore','--nodefault','--nofirststartwizard','--accept=pipe,name='+pipe+';urp;StarOffice.ServiceManager'],env=env,creationflags=subprocess.CREATE_NO_WINDOW)
try:
 r=subprocess.run([str(program/'python.exe'),str(root/'scripts/lo_shape_worker.py'),pipe,str(source),str(out)],env=env,capture_output=True,encoding='utf-8',errors='replace',timeout=60,creationflags=subprocess.CREATE_NO_WINDOW);print(json.dumps({'code':r.returncode,'stdout':r.stdout,'stderr':r.stderr},ensure_ascii=False))
finally:
 if lo.poll()is None:lo.terminate()
