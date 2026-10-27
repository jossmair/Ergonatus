"""Conservative selection-only Win32 EDIT transactions, without clipboard or keystrokes.

Modern/rich editors deliberately fall back to manual copy. Never writes a whole field.
"""
from dataclasses import dataclass
import ctypes as C
from ctypes import wintypes as W
import os
import psutil

@dataclass(frozen=True)
class Selection:
    root:int
    edit:int
    pid:int
    created:float
    document:str
    start:int
    end:int
    selected:str

def validate_span(document,start,end,selected):
    raw=document.encode('utf-16-le')
    if not 0<=start<end<=len(raw)//2<32767: raise ValueError('Sélection vide ou trop longue.')
    if raw[start*2:end*2].decode('utf-16-le')!=selected: raise ValueError('La sélection a changé.')

class TextTarget:
    def __init__(self):
        import win32gui,win32process,win32con
        self.gui,self.process,self.constants=win32gui,win32process,win32con
        self.user=C.WinDLL('user32',use_last_error=True)
        self.user.SendMessageTimeoutW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM,W.UINT,W.UINT,C.POINTER(C.c_size_t)]
        self.user.SendMessageTimeoutW.restype=W.LPARAM
        self.user.GetGUIThreadInfo.argtypes=[W.DWORD,C.c_void_p];self.user.GetGUIThreadInfo.restype=W.BOOL
        self.user.IsWindowUnicode.argtypes=[W.HWND];self.user.IsWindowUnicode.restype=W.BOOL

    def message(self,hwnd,msg,wparam=0,lparam=0):
        result=C.c_size_t()
        if not self.user.SendMessageTimeoutW(hwnd,msg,wparam,lparam,2,500,C.byref(result)):
            raise ValueError('Le champ ne répond pas ; aucune nouvelle action envoyée.')
        return result.value

    def document(self,hwnd):
        length=self.message(hwnd,0xE)
        if length>=32767: raise ValueError('Champ trop long pour un remplacement fiable.')
        buffer=C.create_unicode_buffer(length+1)
        self.message(hwnd,0xD,length+1,C.addressof(buffer));return buffer.value

    def capture(self):
        root=self.gui.GetForegroundWindow()
        tid,pid=self.process.GetWindowThreadProcessId(root)
        if pid==os.getpid(): raise ValueError('Sélectionnez le texte dans une autre application puis utilisez l’Orb.')
        class Info(C.Structure):
            _fields_=[('cbSize',W.DWORD),('flags',W.DWORD),('active',W.HWND),('focus',W.HWND),('capture',W.HWND),('menu',W.HWND),('move',W.HWND),('caret',W.HWND),('rect',W.RECT)]
        info=Info();info.cbSize=C.sizeof(info)
        if not self.user.GetGUIThreadInfo(tid,C.byref(info)): raise ValueError('Champ actif non accessible.')
        edit=info.focus
        if not edit or self.gui.GetClassName(edit).casefold()!='edit':
            raise ValueError('Cet éditeur ne fournit pas une sélection fiable. Collez le texte ici, puis copiez le résultat.')
        if not self.user.IsWindowUnicode(edit):raise ValueError('Ce champ ancien ne fournit pas de positions Unicode fiables. Utilisez la copie manuelle.')
        if self.gui.GetWindowLong(edit,-16)&0x800:raise ValueError('Ce champ est en lecture seule. Vous pouvez copier le résultat.')
        if self.gui.GetWindowLong(edit,-16)&0x20: raise ValueError('Champ confidentiel : capture refusée.')
        if self.gui.GetAncestor(edit,2)!=root or self.process.GetWindowThreadProcessId(edit)[1]!=pid: raise ValueError('Cible incohérente.')
        document=self.document(edit);span=self.message(edit,0xB0);start,end=span&65535,span>>16
        selected=document.encode('utf-16-le')[start*2:end*2].decode('utf-16-le')
        validate_span(document,start,end,selected)
        if self.gui.GetForegroundWindow()!=root: raise ValueError('La fenêtre active a changé.')
        return Selection(root,edit,pid,psutil.Process(pid).create_time(),document,start,end,selected)

    def check(self,target,expected_document=None,expected_span=None):
        if not self.gui.IsWindow(target.edit) or self.gui.GetClassName(target.edit).casefold()!='edit': raise ValueError('La cible a disparu.')
        if not self.gui.IsWindowVisible(target.edit) or not self.gui.IsWindowEnabled(target.edit) or self.gui.IsIconic(target.root):raise ValueError('La cible n’est plus disponible.')
        if self.gui.GetWindowLong(target.edit,-16)&0x20:raise ValueError('Le champ est devenu confidentiel.')
        if not self.user.IsWindowUnicode(target.edit) or self.gui.GetWindowLong(target.edit,-16)&0x800:raise ValueError('Le champ ne permet plus un remplacement fiable.')
        if self.process.GetWindowThreadProcessId(target.edit)[1]!=target.pid or psutil.Process(target.pid).create_time()!=target.created: raise ValueError('Le processus cible a changé.')
        if self.gui.GetAncestor(target.edit,2)!=target.root: raise ValueError('La fenêtre cible a changé.')
        if self.document(target.edit)!=(target.document if expected_document is None else expected_document): raise ValueError('Le document a changé. Aucun remplacement effectué.')
        if expected_span is not None:
            raw=self.message(target.edit,0xB0)
            if (raw&65535,raw>>16)!=expected_span: raise ValueError('La sélection a changé. Aucun remplacement effectué.')

    def replace(self,target,replacement):
        if not replacement or len(replacement)>24000: raise ValueError('Texte de remplacement invalide.')
        validate_span(target.document,target.start,target.end,target.selected)
        self.check(target,expected_span=(target.start,target.end))
        foreground=self.gui.GetForegroundWindow()
        if foreground!=target.root and self.process.GetWindowThreadProcessId(foreground)[1]!=os.getpid():raise ValueError('Une autre fenêtre est devenue active. Aucun remplacement effectué.')
        # EM_REPLACESEL is the only document write; never SetValue / SetWindowText.
        buffer=C.create_unicode_buffer(replacement)
        self.check(target,expected_span=(target.start,target.end))
        self.message(target.edit,0xC2,1,C.addressof(buffer))
        raw=target.document.encode('utf-16-le')
        wanted=(raw[:target.start*2]+replacement.encode('utf-16-le')+raw[target.end*2:]).decode('utf-16-le')
        if self.document(target.edit)!=wanted: raise ValueError('Résultat non confirmé. Vérifiez la cible ; aucune seconde tentative automatique.')
        return wanted

    def restore(self,target,wanted):
        inserted_length=(len(wanted.encode('utf-16-le'))-len(target.document.encode('utf-16-le')))//2+target.end-target.start
        end=target.start+inserted_length
        self.check(target,expected_document=wanted,expected_span=(end,end))
        self.message(target.edit,0xB1,target.start,end)
        self.check(target,expected_document=wanted,expected_span=(target.start,end))
        buffer=C.create_unicode_buffer(target.selected)
        self.message(target.edit,0xC2,1,C.addressof(buffer))
        if self.document(target.edit)!=target.document: raise ValueError('Annulation non confirmée. Vérifiez la cible.')
