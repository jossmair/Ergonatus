"""Verified selection transactions. Never cut/delete before a replacement is ready."""
import time
from dataclasses import dataclass
from shared.text_target import TextTarget

@dataclass
class WebSelection:
    root:int
    runtime:tuple
    pid:int
    created:float
    document:str
    start:int
    end:int
    selected:str

class CorrectionTarget:
    def __init__(self):self.native=None;self.bridge=None
    def capture(self,expected):
        import win32gui
        if win32gui.GetForegroundWindow()!=expected:raise ValueError('La fenêtre a changé.')
        try:
            self.native=TextTarget();target=self.native.capture()
            return target
        except ValueError:self.native=None
        from shared.selection_accessibility import Accessibility
        self.bridge=Accessibility()
        return self.web_capture(expected)
    def web_capture(self,expected):
        import win32gui,win32process,os
        if win32gui.GetForegroundWindow()!=expected:raise ValueError('La fenêtre a changé. Aucun remplacement.')
        if win32process.GetWindowThreadProcessId(expected)[1]==os.getpid():raise ValueError('Sélectionnez du texte dans une autre application.')
        target=self.bridge.capture(expected);element=self.bridge.elements[target.token];api=self.bridge.api
        pattern=element.GetCurrentPattern(api.UIA_TextPatternId).QueryInterface(api.IUIAutomationTextPattern)
        ranges=pattern.GetSelection()
        if ranges.Length!=1:raise ValueError('Sélection non vérifiable.')
        selected=ranges.GetElement(0);text=selected.GetText(12001)
        if not text or len(text)>12000:raise ValueError('Sélection vide ou trop longue.')
        readonly=selected.GetAttributeValue(40015)
        if type(readonly) not in (bool,int) or readonly!=0:raise ValueError('Texte en lecture seule : aucun remplacement automatique.')
        document=pattern.DocumentRange.GetText(24001)
        if len(document)>24000:raise ValueError('Document trop long pour vérifier le remplacement.')
        prefix=pattern.DocumentRange.Clone();prefix.MoveEndpointByRange(1,selected,0)
        start=len(prefix.GetText(24001));end=start+len(text)
        if document[start:end]!=text:raise ValueError('Positions de sélection incohérentes.')
        return WebSelection(expected,tuple(element.GetRuntimeId()),target.pid,target.created,document,start,end,text)
    def replace(self,target,replacement):
        if self.native:return self.native.replace(target,replacement)
        current=self.web_capture(target.root)
        if current!=target:raise ValueError('Le texte ou la sélection a changé. Aucun remplacement.')
        return self.paste(target,replacement)
    def paste(self,target,replacement):
        import win32clipboard as clip,win32con,win32api,win32gui
        saved=clipboard_snapshot();sequence=None
        try:
            open_clipboard()
            try:clip.EmptyClipboard();clip.SetClipboardText(replacement,win32con.CF_UNICODETEXT)
            finally:clip.CloseClipboard()
            sequence=win32clipboard_sequence()
            if self.web_capture(target.root)!=target:raise ValueError('La sélection a changé. Aucun collage.')
            if any(win32api.GetAsyncKeyState(key)&0x8000 for key in (0x10,0x11,0x12,0x5B,0x5C)):
                raise ValueError('Relâchez les touches de commande puis recommencez.')
            # Only paste, never Cut / Delete. Foreground and selection checked above.
            win32api.keybd_event(0x11,0,0,0)
            try:
                win32api.keybd_event(0x56,0,0,0);win32api.keybd_event(0x56,0,2,0)
            finally:win32api.keybd_event(0x11,0,2,0)
            wanted=target.document[:target.start]+replacement+target.document[target.end:]
            deadline=time.monotonic()+1.5
            while time.monotonic()<deadline:
                if win32gui.GetForegroundWindow()!=target.root:raise ValueError('La fenêtre a changé après le collage. Vérifiez le résultat.')
                element=self.bridge.client.GetFocusedElement()
                if tuple(element.GetRuntimeId())!=target.runtime:raise ValueError('Le champ a changé après le collage. Vérifiez le résultat.')
                pattern=element.GetCurrentPattern(self.bridge.api.UIA_TextPatternId).QueryInterface(self.bridge.api.IUIAutomationTextPattern)
                if pattern.DocumentRange.GetText(24001)==wanted:return wanted
                time.sleep(.03)
            raise ValueError('Collage non confirmé. Vérifiez le texte ; aucune seconde tentative automatique.')
        finally:
            if sequence is not None and win32clipboard_sequence()==sequence:restore_clipboard(saved,sequence)
    def close(self):
        if self.bridge:self.bridge.close()
    def restore(self,target,wanted):
        from shared.text_target import Selection
        if isinstance(target,Selection):return TextTarget().restore(target,wanted)
        import win32gui,win32process,os,psutil
        foreground=win32gui.GetForegroundWindow()
        if foreground!=target.root and win32process.GetWindowThreadProcessId(foreground)[1]!=os.getpid():
            raise ValueError('Une autre fenêtre est active. Rouvrez Corrector pour restaurer.')
        if psutil.Process(target.pid).create_time()!=target.created:raise ValueError('La cible a changé.')
        win32gui.SetForegroundWindow(target.root)
        from shared.selection_accessibility import Accessibility
        self.bridge=Accessibility();element=self.bridge.client.GetFocusedElement()
        if tuple(element.GetRuntimeId())!=target.runtime:raise ValueError('Le champ a changé.')
        api=self.bridge.api;pattern=element.GetCurrentPattern(api.UIA_TextPatternId).QueryInterface(api.IUIAutomationTextPattern)
        if pattern.DocumentRange.GetText(24001)!=wanted:raise ValueError('Le texte a changé depuis la correction. Restauration refusée.')
        inserted=wanted[target.start:len(wanted)-(len(target.document)-target.end)]
        selection=pattern.GetSelection()
        if selection.Length!=1 or selection.GetElement(0).GetText(24001):raise ValueError('La sélection a changé.')
        prefix=pattern.DocumentRange.Clone();prefix.MoveEndpointByRange(1,selection.GetElement(0),0)
        if len(prefix.GetText(24001))!=target.start+len(inserted):raise ValueError('Le curseur a changé.')
        span=pattern.DocumentRange.Clone()
        span.MoveEndpointByUnit(1,0,-(len(wanted)-target.start-len(inserted)))
        span.MoveEndpointByUnit(0,0,target.start)
        prefix=pattern.DocumentRange.Clone();prefix.MoveEndpointByRange(1,span,0)
        if span.GetText(24001)!=inserted or prefix.GetText(24001)!=target.document[:target.start]:raise ValueError('Positions non vérifiables.')
        span.Select();current=self.web_capture(target.root)
        if current.document!=wanted or current.selected!=inserted:raise ValueError('La sélection a changé.')
        self.paste(current,target.selected)

def win32clipboard_sequence():
    import ctypes
    return ctypes.windll.user32.GetClipboardSequenceNumber()


def open_clipboard():
    import win32clipboard
    deadline=time.monotonic()+1
    while True:
        try:win32clipboard.OpenClipboard();return
        except Exception:
            if time.monotonic()>deadline:raise ValueError('Le presse-papiers est occupé. Aucun nouveau collage.')
            time.sleep(.02)


def clipboard_snapshot():
    import win32clipboard as clip,struct
    saved=[];seen=False;open_clipboard()
    try:
        fmt=0
        for _ in range(128):
            fmt=clip.EnumClipboardFormats(fmt)
            if not fmt:break
            seen=True
            try:
                data=clip.GetClipboardData(fmt)
                if fmt==15 and isinstance(data,tuple):data=struct.pack('<IiiII',20,0,0,0,1)+('\0'.join(data)+'\0\0').encode('utf-16-le')
                if isinstance(data,(str,bytes)):saved.append((fmt,data))
            except Exception:continue
        if seen and not saved:raise ValueError('Le presse-papiers ne peut pas être préservé pour ce format.')
        return saved
    finally:clip.CloseClipboard()


def restore_clipboard(saved,sequence):
    import win32clipboard as clip
    open_clipboard()
    try:
        if win32clipboard_sequence()!=sequence:return
        clip.EmptyClipboard()
        for fmt,data in saved:clip.SetClipboardData(fmt,data)
    finally:clip.CloseClipboard()
