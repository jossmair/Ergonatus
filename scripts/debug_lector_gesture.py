"""Disposable full gesture test. Records test text only, never user selections."""
from pathlib import Path
import sys,os,json,uuid,time
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
os.environ['USERDOMAIN']='LectorGestureQA-'+uuid.uuid4().hex
os.environ['ERGONATUS_DATA']=str(root/'.test-data'/os.environ['USERDOMAIN'])
os.environ['ERGONATUS_NO_HOTKEYS']='1'
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from shared.apps.text import TextApplication
from unittest.mock import patch
app=QApplication([]);app.setQuitOnLastWindowClosed(False)
path=root/'.test-data/lector-gesture-debug.json';events=[]
def record(kind,value):
    events.append(dict(event=kind,value=value));path.write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding='utf-8')
with patch.object(TextApplication,'warm_lector_voice',lambda self:None):
    window=TextApplication('lector')
    window.orb.setWindowTitle('Lector TEST · Orbe')
    window.orb.move(600,80)
    original=window.selection_picker.probe
    previous=[None]
    def probe():
        result=original();signature=result[1:]
        if signature!=previous[0]:record('probe',signature);previous[0]=signature
        return result
    window.selection_picker.probe=probe
    import win32gui
    original_read=window.read_lector_selection
    window.selection_picker.selected.disconnect()
    def selected(expected):
        title=win32gui.GetWindowText(expected)
        if title not in ('Ergonatus · test de sélection isolé','Lector test lecture — Mozilla Firefox'):return
        record('released',expected);original_read(expected)
    window.selection_picker.selected.connect(selected)
    window.speaker.speak=lambda text,**kwargs:record('spoken',text) or True
    original_error=window.error
    def error(text):record('error',text);original_error(text)
    window.error=error
    # Errors route through bound error at job creation.
    window.activate();record('armed',True)
    QTimer.singleShot(120000,window.quit)
    app.exec()
