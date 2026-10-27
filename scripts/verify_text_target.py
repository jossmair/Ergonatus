from pathlib import Path
import subprocess,sys,os,time,json
import win32gui,win32con,psutil
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shared.text_target import TextTarget,Selection
root=Path(__file__).resolve().parents[1];path=root/'.test-data/text-fixture.json';path.unlink(missing_ok=True)
process=subprocess.Popen([sys.executable,str(root/'scripts/text_fixture.py'),str(path)],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
report={}
try:
    for _ in range(100):
        if path.exists():break
        time.sleep(.05)
    info=json.loads(path.read_text());api=TextTarget()
    # Construct the transaction against this owned fixture; capture is separately exercised when Windows permits foreground activation.
    original=api.document(info['edit']);selected='Les réunion sont terminé.';start=6;end=start+len(selected)
    win32gui.SendMessage(info['edit'],win32con.EM_SETSEL,start,end)
    target=Selection(info['root'],info['edit'],info['pid'],psutil.Process(info['pid']).create_time(),original,start,end,selected)
    # The background test runner cannot acquire Windows foreground permission.
    # Simulate only that permission; document reads/writes remain native across processes.
    report['foreground_authorization']='simulated for write; real Windows EDIT and process identity'
    with patch('win32gui.GetForegroundWindow',return_value=info['root']):wanted=api.replace(target,'Les réunions sont terminées.')
    report['selection_replaced']=wanted=='Avant Les réunions sont terminées. Après'
    api.restore(target,wanted);report['original_restored']=api.document(info['edit'])==original
    win32gui.SendMessage(info['edit'],win32con.EM_SETSEL,0,2)
    try:api.replace(target,'NE DOIT PAS ÊTRE INSÉRÉ');report['changed_selection_rejected']=False
    except ValueError:report['changed_selection_rejected']=api.document(info['edit'])==original
    try:
        win32gui.SetForegroundWindow(info['root']);captured=api.capture();report['capture_nonempty']=bool(captured.selected)
    except Exception as error:report['capture_note']=str(error)
finally:
    if path.exists():
        info=json.loads(path.read_text())
        if win32gui.IsWindow(info['root']):win32gui.PostMessage(info['root'],win32con.WM_CLOSE,0,0)
    process.wait(timeout=25)
(root/'docs/validation/text-target.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
assert all(report.get(key) for key in ('selection_replaced','original_restored','changed_selection_rejected'))
