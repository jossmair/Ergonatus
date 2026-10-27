"""Isolated compiled smoke checks; never signals the user's live suite instances."""
import json,os,subprocess,tempfile,time,uuid
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtNetwork import QLocalSocket
from shared.catalog import Catalog,suite_root
from shared.apps.base import instance_name

root=suite_root();data=Path(tempfile.mkdtemp(prefix='ergonatus-quit-'))
os.environ.update(ERGONATUS_TEST_MODE='1',ERGONATUS_NO_HOTKEYS='1',ERGONATUS_DATA=str(data),USERDOMAIN='ErgonatusQA'+uuid.uuid4().hex)
app=QApplication([]);catalog=Catalog();path=catalog.detect('ecrinator')
process=subprocess.Popen([str(path),'--minimized'],cwd=path.parent,creationflags=subprocess.CREATE_NO_WINDOW)
ready=False
try:
    deadline=time.monotonic()+25
    while time.monotonic()<deadline and process.poll() is None:
        socket=QLocalSocket();socket.connectToServer(instance_name('ecrinator'))
        if socket.waitForConnected(200):socket.disconnectFromServer();ready=True;break
        time.sleep(.2)
    assert ready,'Isolated companion did not start'
    catalog.running=lambda key:[process] if key=='ecrinator' else []
    catalog.quit_suite();code=process.wait(timeout=15);assert code==0,code
    start=time.monotonic()
    result=subprocess.run([str(root/'Hub/Ergonatus.exe'),'--smoke-test','--data-dir',str(data/'hub'),'--snapshot',str(root/'docs/validation/ergonatus-updated-compiled.png')],cwd=root,timeout=35)
    assert result.returncode==0,result.returncode
    report={'isolated_companion_quit_exit':code,'compiled_hub_smoke_exit':result.returncode,'hub_smoke_seconds':round(time.monotonic()-start,3)}
    (root/'docs/validation/ergonatus-updated-smoke.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
finally:
    if process.poll() is None:
        catalog.running=lambda key:[process] if key=='ecrinator' else []
        catalog.quit_suite()
