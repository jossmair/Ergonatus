from pathlib import Path
import sys,os,subprocess,time,uuid,json,psutil
root=Path(__file__).resolve().parents[1]
environment=os.environ.copy();identity='LectorPackageQA-'+uuid.uuid4().hex
environment.update(USERDOMAIN=identity,ERGONATUS_DATA=str(root/'.test-data'/identity),ERGONATUS_NO_HOTKEYS='1')
start=time.monotonic();process=subprocess.Popen([str(root/'Lector/runtime/Lector.exe'),'--smoke-test','--snapshot',str(root/'docs/validation/lector-packaged.png')],env=environment,cwd=root)
children={}
try:
    while process.poll() is None and time.monotonic()-start<35:
        try:
            for child in psutil.Process(process.pid).children(recursive=True):children[child.pid]=child
        except psutil.NoSuchProcess:pass
        time.sleep(.1)
    assert process.wait(timeout=3)==0
    assert (Path(environment['ERGONATUS_DATA'])/'lector/window.json').is_file()
    report=dict(exit_code=process.returncode,seconds=time.monotonic()-start,window_state_written=True)
    (root/'docs/validation/lector-package.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
finally:
    if process.poll() is None:process.terminate()
    for child in children.values():
        try:
            if child.name()=='ErgoVoice.exe' and child.environ().get('USERDOMAIN')==identity:child.terminate()
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
