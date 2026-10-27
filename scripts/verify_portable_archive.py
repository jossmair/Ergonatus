"""Read back a portable ZIP and smoke-test extracted hub and calendar binaries."""
from pathlib import Path
import os,json,tempfile,uuid,zipfile,subprocess,shutil,hashlib
ROOT=Path(__file__).resolve().parents[1]
archive=ROOT/'output/releases/Ergonatus-portable-2026-10-25.zip'
target=Path(tempfile.mkdtemp(prefix='ergonatus-portable-check-')).resolve()
report={}
try:
    with zipfile.ZipFile(archive) as z:
        manifest=json.loads(z.read('Ergonatus/PORTABLE-MANIFEST.json'))
        for name in z.namelist():
            short=name.removeprefix('Ergonatus/')
            if short.startswith(('Hub/','Planinator/runtime/','assets/')) or short=='suite_design.py' or (short.count('/')==2 and short.endswith('.exe') and '/runtime/' in short):
                destination=(target/short).resolve();assert destination.is_relative_to(target)
                destination.parent.mkdir(parents=True,exist_ok=True)
                with z.open(name) as src,destination.open('wb') as dst:shutil.copyfileobj(src,dst)
                expected=manifest['files'].get(short)
                if expected:assert hashlib.sha256(destination.read_bytes()).hexdigest()==expected['sha256'],short
        for name in manifest['files']:
            if '/runtime/_internal/' in name:(target/name.split('/_internal/')[0]/'_internal').mkdir(parents=True,exist_ok=True)
    env=os.environ.copy();env.update(USERDOMAIN='PortableExtract'+uuid.uuid4().hex,ERGONATUS_DATA=str(target/'Data'),ERGONATUS_TEST_MODE='1',ERGONATUS_NO_HOTKEYS='1')
    for key,exe in [('hub','Hub/Ergonatus.exe'),('planinator','Planinator/runtime/Planinator.exe')]:
        result=subprocess.run([str(target/exe),'--smoke-test'],cwd=target,env=env,capture_output=True,timeout=45)
        report[key]=dict(exit=result.returncode,output=(result.stdout+result.stderr).decode(errors='replace')[-1500:]);assert result.returncode==0,report[key]
    report['extracted_hashes_verified']=True
    (ROOT/'output/releases/Ergonatus-portable-verification.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)
finally:
    assert target.parent==Path(tempfile.gettempdir()).resolve() and target.name.startswith('ergonatus-portable-check-')
    shutil.rmtree(target)
