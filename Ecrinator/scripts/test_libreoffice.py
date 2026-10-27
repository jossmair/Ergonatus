"""Isolated LibreOffice conversion, with absolute paths and no user profile."""
from pathlib import Path
import os,subprocess,json,sys,uuid
root=Path(__file__).resolve().parents[1]
folder=Path(sys.argv[1]).resolve()
out=root/'test-output'/('libreoffice-'+(sys.argv[2] if len(sys.argv)>2 else 'v08'))
out.mkdir(parents=True,exist_ok=True)
profile=root/'test-output'/('lo-profile-'+uuid.uuid4().hex)
hello=out/'control.txt';hello.write_text('Document de controle LibreOffice.\n',encoding='utf-8')
env=os.environ.copy()
for key in ['PYTHONHOME','PYTHONPATH']:env.pop(key,None)
inputs=[hello,*sorted(folder.glob('*.odt'))]
args=[r'C:\Program Files\LibreOffice\program\soffice.com','-env:UserInstallation='+profile.as_uri(),'--headless','--norestore','--convert-to','pdf','--outdir',str(out),*[str(p) for p in inputs]]
result=subprocess.run(args,cwd=root,env=env,capture_output=True,encoding='utf-8',errors='replace',timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
print(json.dumps({'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'inputs':[{ 'file':str(p),'exists':p.is_file()} for p in inputs],'outputs':[p.name for p in out.glob('*.pdf')]},ensure_ascii=False,indent=2))
assert (out/'control.pdf').is_file(),'LibreOffice did not convert even plain text'
assert result.returncode == 0, 'LibreOffice conversion failed'
assert all((out/(p.stem+'.pdf')).is_file() for p in inputs), 'Some ODT conversions failed'
