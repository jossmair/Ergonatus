"""Disposable standard EDIT fixture, never attaches to an existing user window."""
import json
from pathlib import Path
import sys
import time
import win32gui,win32api,win32con
path=Path(sys.argv[1]);name='ErgonatusTextFixture'+str(__import__('os').getpid())
wc=win32gui.WNDCLASS();wc.lpszClassName=name;wc.hInstance=win32api.GetModuleHandle(None)
def procedure(hwnd,message,wparam,lparam):
    if message==win32con.WM_DESTROY:win32gui.PostQuitMessage(0);return 0
    return win32gui.DefWindowProc(hwnd,message,wparam,lparam)
wc.lpfnWndProc=procedure;win32gui.RegisterClass(wc)
root=win32gui.CreateWindow(name,'Ergonatus · test de sélection isolé',win32con.WS_OVERLAPPEDWINDOW,40,40,520,180,0,0,wc.hInstance,None)
edit=win32gui.CreateWindowEx(0,'EDIT','Avant Les réunion sont terminé. Après',win32con.WS_CHILD|win32con.WS_VISIBLE|win32con.WS_BORDER|win32con.ES_AUTOHSCROLL,12,20,460,50,root,0,wc.hInstance,None)
win32gui.ShowWindow(root,win32con.SW_SHOW)
try:win32gui.SetForegroundWindow(root)
except Exception:pass
win32gui.SetFocus(edit);win32gui.SendMessage(edit,win32con.EM_SETSEL,6,30)
path.write_text(json.dumps(dict(root=root,edit=edit,pid=__import__('os').getpid())))
deadline=time.monotonic()+(float(sys.argv[2]) if len(sys.argv)>2 else 20)
while time.monotonic()<deadline:
    if win32gui.PumpWaitingMessages():break
    time.sleep(.01)
if win32gui.IsWindow(root):win32gui.DestroyWindow(root)
