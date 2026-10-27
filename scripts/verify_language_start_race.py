from pathlib import Path
import os,sys,time,subprocess,tempfile,uuid,json,psutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
identity='LanguageRace'+uuid.uuid4().hex;os.environ.update(USERDOMAIN=identity,ERGONATUS_DATA=tempfile.mkdtemp())
from ergoai.proofreading_client import request
exe=ROOT/'ergoai/proofreading/runtime/ErgoProofread.exe';children=[]
try:
    children=[subprocess.Popen([str(exe)],env=os.environ.copy(),cwd=ROOT) for _ in range(2)]
    deadline=time.monotonic()+20;status=None
    while time.monotonic()<deadline:
        try:status=request(dict(op='status'));break
        except (OSError,EOFError):time.sleep(.1)
    assert status
    time.sleep(1)
    alive=[]
    for p in psutil.process_iter(['exe']):
        try:
            if p.info['exe'] and Path(p.info['exe'])==exe and p.environ().get('USERDOMAIN')==identity:alive.append(p.pid)
        except psutil.Error:pass
    assert len(alive)==1 and status['pid'] in alive
    report=dict(simultaneous_launches=2,active_hosts=len(alive),model_loaded=status['loaded'],passed=True)
    (ROOT/'output/audit/current/language-start-race.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
finally:
    for p in children:
        if p.poll() is None:p.terminate()
    for p in children:
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:p.kill()
