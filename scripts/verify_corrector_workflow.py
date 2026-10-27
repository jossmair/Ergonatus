from pathlib import Path
import os,sys,uuid,json,subprocess,time
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
os.environ.update(USERDOMAIN='CorrectorWorkflowQA-'+uuid.uuid4().hex,ERGONATUS_DATA=str(root/'.test-data/corrector-workflow'),ERGONATUS_NO_HOTKEYS='1')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint
from PySide6.QtTest import QTest
import win32gui,win32con
from shared.apps.corrector import CorrectorWindow
from shared.selection_accessibility import Accessibility
from shared.corrector_target import clipboard_snapshot,CorrectionTarget
app=QApplication([]);window=CorrectorWindow();bridge=Accessibility();path=root/'.test-data'/('corrector-workflow-'+uuid.uuid4().hex+'.json')
child=subprocess.Popen([sys.executable,str(root/'scripts/corrector_edit_fixture.py'),str(path)])
try:
    for _ in range(100):
        if path.exists():break
        QTest.qWait(30)
    info=json.loads(path.read_text());element=bridge.client.ElementFromHandle(info['root']);providers=element.FindAll(bridge.api.TreeScope_Subtree,bridge.client.CreatePropertyCondition(bridge.api.UIA_IsTextPatternAvailablePropertyId,True));provider=providers.GetElement(0);provider.SetFocus();QTest.qWait(150)
    assert win32gui.GetForegroundWindow()==info['root']
    before=dict(clipboard_snapshot());window.activate();window.picker.timer.stop()
    for down in (True,False):
        window.picker.probe=lambda down=down:(QPoint(100,100),down,False,info['root'],False,win32gui.GetForegroundWindow())
        window.picker.poll()
    QTest.qWait(200)
    for _ in range(1200):
        if not window.busy:break
        QTest.qWait(20);time.sleep(.01)
    assert window.transaction is not None,window.status.text()
    assert window.output.toPlainText()=='Les réunions sont terminées',repr(window.output.toPlainText())
    pattern=provider.GetCurrentPattern(bridge.api.UIA_TextPatternId).QueryInterface(bridge.api.IUIAutomationTextPattern)
    assert pattern.DocumentRange.GetText(24001)=='Avant Les réunions sont terminées. Après'
    after=dict(clipboard_snapshot());assert all(after.get(fmt)==value for fmt,value in before.items())
    window.restore_original()
    for _ in range(100):
        if window.transaction is None:break
        QTest.qWait(20);time.sleep(.01)
    assert pattern.DocumentRange.GetText(24001)=='Avant Les réunion sont terminé. Après'
    report=dict(orb_selection_pipeline=True,external_rich_editor=True,replaced=True,restored=True,clipboard_supported_formats_preserved=True)
    (root/'docs/validation/corrector-workflow.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
finally:
    window.closing=True;window.cleanup();window.layout_timer.stop();window.orb.close();window.tray.hide();window.server.close();window.records.close();window.close();bridge.close()
    if path.exists():
        info=json.loads(path.read_text())
        if win32gui.IsWindow(info['root']):win32gui.PostMessage(info['root'],win32con.WM_CLOSE,0,0)
    child.wait(timeout=25)
    try:
        import psutil
        from ergoai.proofreading_client import request
        process=psutil.Process(request(dict(op='status'))['pid'])
        if process.environ().get('USERDOMAIN')==os.environ['USERDOMAIN']:process.terminate()
    except Exception:pass
