"""Verify real packaged startup using isolated settings and IPC identities."""
import json,os,subprocess,tempfile,time,uuid,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtNetwork import QLocalSocket
from shared.catalog import Catalog,suite_root
from shared.profiles import ProfileStore,default_profile
from shared.apps.base import instance_name
import win32gui,win32process,win32api,win32con

root=suite_root();data=Path(tempfile.mkdtemp(prefix='ergonatus-startup-'))
os.environ.update(ERGONATUS_TEST_MODE='1',ERGONATUS_NO_HOTKEYS='1',ERGONATUS_DATA=str(data),USERDOMAIN='ErgonatusStartupQA'+uuid.uuid4().hex)
app=QApplication([]);profile=default_profile();profile['active']=['lector']
ProfileStore(data/'hub/profiles.json').save([profile],profile['name'])
hub=subprocess.Popen([str(root/'Hub/Ergonatus.exe'),'--data-dir',str(data/'hub')],cwd=root,creationflags=subprocess.CREATE_NO_WINDOW)
catalog=Catalog();ready=False;child_pids=set()
try:
    deadline=time.monotonic()+35
    while time.monotonic()<deadline and hub.poll() is None:
        socket=QLocalSocket();socket.connectToServer(instance_name('lector'))
        if socket.waitForConnected(200):socket.disconnectFromServer();ready=True;break
        time.sleep(.2)
    assert ready,'Selected app did not start automatically'
    import psutil
    child_pids={p.pid for p in psutil.Process(hub.pid).children(recursive=True)}
    report={'selected':['lector'],'legacy_autolaunch':False,'compiled_startup_verified':ready}
    (root/'docs/validation/modern-startup-smoke.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
finally:
    threads=set()
    def collect(hwnd,arg):
        thread,pid=win32process.GetWindowThreadProcessId(hwnd)
        if pid==hub.pid:threads.add(thread)
    win32gui.EnumWindows(collect,None)
    for thread in threads:win32api.PostThreadMessage(thread,win32con.WM_QUIT,0,0)
    socket=QLocalSocket();socket.connectToServer(instance_name('lector'))
    if socket.waitForConnected(500):
        socket.write(b'{"version":1,"command":"quit"}\n');socket.waitForBytesWritten(500);socket.disconnectFromServer()
    hub.wait(timeout=15)

