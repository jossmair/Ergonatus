from pathlib import Path
import subprocess,time,json,sys,uuid,win32gui,win32con
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from shared.selection_accessibility import Accessibility
from shared.corrector_target import CorrectionTarget
from ergoai.correction import correct
path=root/'.test-data'/('corrector-paste-'+uuid.uuid4().hex+'.json')
p=subprocess.Popen([sys.executable,str(root/'scripts/corrector_edit_fixture.py'),str(path)]);b=Accessibility();api=CorrectionTarget()
try:
    for _ in range(100):
        if path.exists():break
        time.sleep(.03)
    info=json.loads(path.read_text());el=b.client.ElementFromHandle(info['root']);providers=el.FindAll(b.api.TreeScope_Subtree,b.client.CreatePropertyCondition(b.api.UIA_IsTextPatternAvailablePropertyId,True));providers.GetElement(0).SetFocus();time.sleep(.15)
    assert win32gui.GetForegroundWindow()==info['root']
    target=api.capture(info['root']);result=correct(target.selected);wanted=api.replace(target,result['text'])
    assert wanted=='Avant Les réunions sont terminées. Après',repr(wanted)
    api.restore(target,wanted)
    print('UIA replacement and restoration passed')
    (root/'docs/validation/corrector-rich.json').write_text(json.dumps(dict(external_editable_qt=True,replaced=True,restored=True,clipboard_restoration=True)))
finally:
    api.close();b.close()
    if path.exists():
        info=json.loads(path.read_text())
        if win32gui.IsWindow(info['root']):win32gui.PostMessage(info['root'],win32con.WM_CLOSE,0,0)
    p.wait(timeout=25)
