"""Read a real selection from a disposable external Windows EDIT, without clipboard."""
from pathlib import Path
import json,subprocess,sys,time,uuid
import win32gui,win32con
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from shared.reading_selection import read_selection
path=root/'.test-data'/('lector-selection-'+uuid.uuid4().hex+'.json')
process=subprocess.Popen([sys.executable,str(root/'scripts/text_fixture.py'),str(path)])
try:
    for _ in range(100):
        if path.exists():break
        time.sleep(.05)
    info=json.loads(path.read_text())
    win32gui.SetForegroundWindow(info['root']);time.sleep(.15)
    selected=read_selection(info['root'])
    assert selected=='Les réunion sont terminé',repr(selected)
    report=dict(real_external_selection=True,selected=selected,clipboard_used=False)
    (root/'docs/validation/lector-selection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
finally:
    if path.exists():
        info=json.loads(path.read_text())
        if win32gui.IsWindow(info['root']):win32gui.PostMessage(info['root'],win32con.WM_CLOSE,0,0)
    process.wait(timeout=25)
