import os,sys,tempfile,uuid
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
os.environ.update(ERGONATUS_TEST_MODE='1',ERGONATUS_NO_HOTKEYS='1',USERDOMAIN='PortableLauncher'+uuid.uuid4().hex,ERGONATUS_DATA=tempfile.mkdtemp())
from PySide6.QtWidgets import QApplication
from suite_design import install
from Hub.fort_hub import HubWindow
app=QApplication([]);app.setApplicationName('Ergonatus');install(app)
w=HubWindow(Path(tempfile.mkdtemp()));w.launcher.resize(1280,720);w.launcher.rebuild();w.launcher.show();app.processEvents()
w.launcher.grab().save(str(root/'docs/validation/modern-2026-10-24/portable-launcher-names.png'))
w.close();app.processEvents()
