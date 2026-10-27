"""Explicit Windows hotkeys only; no keyboard hook or synthetic input."""
import ctypes
from ctypes import wintypes
from PySide6.QtCore import QAbstractNativeEventFilter,QTimer

KEYS={'corrector':(0x6509,0x78,'Ctrl+Alt+F9'),'traductor':(0x650A,0x79,'Ctrl+Alt+F10'),'lector':(0x650B,0x7A,'Ctrl+Alt+F11')}
class Hotkey(QAbstractNativeEventFilter):
    def __init__(self,app_id,callback):
        super().__init__();self.identifier,self.key,self.label=KEYS[app_id];self.callback=callback
        self.user=ctypes.WinDLL('user32',use_last_error=True)
        self.active=bool(self.user.RegisterHotKey(None,self.identifier,0x0001|0x0002|0x4000,self.key))
    def nativeEventFilter(self,event_type,message):
        msg=wintypes.MSG.from_address(int(message))
        if self.active and msg.message==0x312 and msg.wParam==self.identifier:
            QTimer.singleShot(0,self.callback);return True,0
        return False,0
    def close(self):
        if self.active:self.user.UnregisterHotKey(None,self.identifier);self.active=False
