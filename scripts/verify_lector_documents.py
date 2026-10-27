"""Native read-only document selection, no clipboard and no browser control."""
from pathlib import Path
import sys,subprocess,time,uuid,json
import win32gui,win32con
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from shared.uia_reading import read_document_selection
path=root/'.test-data'/('rich-selection-'+uuid.uuid4().hex+'.json')
process=subprocess.Popen([sys.executable,str(root/'scripts/reading_fixture.py'),str(path)])
try:
    for _ in range(100):
        if path.exists():break
        time.sleep(.05)
    info=json.loads(path.read_text());time.sleep(.5)
    # A background test runner cannot always take Windows foreground permission.
    # Only that permission is substituted; the external UIA document remains real.
    from unittest.mock import patch
    with patch('win32gui.GetForegroundWindow',return_value=info['root']):
        text=read_document_selection(info['root'])
    assert text=='Ce passage sélectionné doit être lu.',repr(text)
    report=dict(real_read_only_document=True,selection_matched=True,clipboard_used=False,foreground_permission='simulated for owned test window')
    (root/'docs/validation/lector-rich-selection.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
finally:
    if path.exists():
        info=json.loads(path.read_text())
        if win32gui.IsWindow(info['root']):win32gui.PostMessage(info['root'],win32con.WM_CLOSE,0,0)
    process.wait(timeout=35)
