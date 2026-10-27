from types import SimpleNamespace
from shared.catalog import Catalog

def test_quit_suite_requests_ipc_and_native_gui_exit(monkeypatch,tmp_path):
    import PySide6.QtNetwork as network
    import win32gui,win32process,win32api
    sent=[];posted=[]
    class Socket:
        def connectToServer(self,name):sent.append(name)
        def waitForConnected(self,timeout):return True
        def write(self,data):sent.append(data)
        def waitForBytesWritten(self,timeout):return True
        def disconnectFromServer(self):pass
    monkeypatch.setattr(network,'QLocalSocket',Socket)
    monkeypatch.setattr(win32gui,'EnumWindows',lambda callback,arg:[callback(hwnd,arg) for hwnd in (1,2)])
    monkeypatch.setattr(win32process,'GetWindowThreadProcessId',lambda hwnd:(100+hwnd,55 if hwnd==1 else 999))
    monkeypatch.setattr(win32api,'PostThreadMessage',lambda *args:posted.append(args))
    catalog=Catalog(tmp_path)
    monkeypatch.setattr(catalog,'running',lambda key:[SimpleNamespace(pid=55)] if key=='redactor' else [SimpleNamespace(pid=56)] if key=='ecrinator' else [])
    catalog.quit_suite()
    assert b'{"version":1,"command":"quit"}\n' in sent
    assert len(posted)==1 and posted[0][0]==101
