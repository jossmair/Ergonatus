"""Exercise the hub launch path against installed binaries using private test data."""
from pathlib import Path
import os,sys,tempfile,uuid,time,json,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'output/ui-revision-2026-10-27';private=Path(tempfile.mkdtemp(prefix='ergonatus-ui-'))
os.environ.update(USERDOMAIN='UIInstall'+uuid.uuid4().hex,ERGONATUS_DATA=str(private),ERGONATUS_TEST_MODE='1',ERGONATUS_NO_HOTKEYS='1')
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from shared.catalog import Catalog
from shared.domain import Records
from orb_manager.manager import OrbManager
app=QApplication([]);catalog=Catalog('C:/Users/Josselin/Desktop/Ergonatus');manager=OrbManager(catalog)
keys=['dictionnator','explicator','tablinator'];area=app.primaryScreen().availableGeometry()
layout=private/'layout.json';catalog.layout_path=layout
layout.write_text(json.dumps({'version':1,'apps':{key:dict(visible=True,position=[area.right()-60,area.bottom()-100-i*50]) for i,key in enumerate(keys)}}))
for key in keys:
    r=Records(key);r.add('settings',{'orb_hidden':True});r.close()
report={}
try:
    for key in keys:assert catalog.launch(key,minimized=True)
    deadline=time.monotonic()+30;found=[]
    while time.monotonic()<deadline:
        QTest.qWait(200);found=manager.native_orbs()
        if set(row['app'] for row in found)>=set(keys):break
    assert set(row['app'] for row in found)>=set(keys),found
    report['hub_launch_orbs']=found
    assert len({tuple(row['rect'][:2]) for row in found})==3
finally:
    for key,p in catalog.processes.items():
        if p.poll() is None:
            subprocess.run([str(catalog.detect(key)),'--quit-running'],env=os.environ.copy(),timeout=10)
            try:p.wait(timeout=10)
            except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
    manager.server.close()
    for socket in tuple(manager.sockets):socket.abort()
    QTest.qWait(200)
for key in ['corrector','explicator','dictionnator','tablinator','traductor','communicator','temporator','calculinator']:
    exe=catalog.detect(key);snapshot=OUT/'installed-captures'/(key+'.png')
    start=time.monotonic();result=subprocess.run([str(exe),'--smoke-test','--snapshot',str(snapshot)],env=os.environ.copy(),timeout=90)
    report[key]=dict(exit_code=result.returncode,seconds=round(time.monotonic()-start,2),snapshot=snapshot.is_file())
    (OUT/'installed-smoke.json').write_text(json.dumps(report,indent=2))
    assert result.returncode==0,(key,result.returncode)
print(json.dumps(report,indent=2),flush=True)
