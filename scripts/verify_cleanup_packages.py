"""Smoke checks in temporary data; never closes the user's existing engines."""
from pathlib import Path
import os,subprocess,tempfile,uuid,time,json
import psutil
root=Path(__file__).resolve().parents[1];data=Path(tempfile.mkdtemp(prefix='ergonatus-cleanup-'))
identity='CleanupQA-'+uuid.uuid4().hex;env=os.environ.copy();env.update(USERDOMAIN=identity,ERGONATUS_DATA=str(data),ERGONATUS_NO_HOTKEYS='1',ERGONATUS_TEST_MODE='1')
report=[]
def stop_private_engines():
    for process in psutil.process_iter(['exe','name']):
        try:
            if process.info['name'] in ('ErgoTranslate.exe','ErgoProofread.exe') and process.info['exe'] and Path(process.info['exe']).resolve().is_relative_to(root) and process.environ().get('USERDOMAIN')==identity:
                process.terminate();process.wait(timeout=5)
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
try:
    for name,exe,extra,timeout in [
        ('Hub',root/'Hub/Ergonatus.exe',['--data-dir',str(data/'hub')],35),
        ('Traductor',root/'Traductor/runtime/Traductor.exe',[],90),
        ('Corrector',root/'Corrector/runtime/Corrector.exe',[],120),
    ]:
        start=time.monotonic();result=subprocess.run([str(exe),'--smoke-test']+extra,env=env,cwd=root,timeout=timeout,capture_output=True)
        report.append(dict(app=name,exit_code=result.returncode,seconds=round(time.monotonic()-start,2)))
        # Release the private test model before loading the next one on this PC.
        stop_private_engines()
        assert result.returncode==0,(name,result.stderr.decode(errors='replace')[-600:])
    print(json.dumps(report))
finally:
    (root/'docs/maintenance/cleanup-compiled-smoke-2026-10-20.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    for process in psutil.process_iter(['exe']):
        try:
            if process.info['exe'] and Path(process.info['exe']).resolve().is_relative_to(root) and process.environ().get('USERDOMAIN')==identity:process.terminate()
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
