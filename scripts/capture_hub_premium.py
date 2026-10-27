from pathlib import Path
import os,sys,uuid,tempfile
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root));os.environ.update(USERDOMAIN='HubPremium'+uuid.uuid4().hex,ERGONATUS_DATA=tempfile.mkdtemp(),ERGONATUS_TEST_MODE='1',ERGONATUS_NO_HOTKEYS='1')
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from suite_design import install
from Hub.fort_hub import HubWindow
app=QApplication([]);app.setApplicationName('Ergonatus');install(app);w=HubWindow(Path(tempfile.mkdtemp()));w.show();QTest.qWait(350);out=root/'output/audit/current/captures';w.grab().save(str(out/'hub-premium.png'));w.toggle_launcher();QTest.qWait(250);w.launcher.grab().save(str(out/'hub-premium-21-apps.png'));assert len(w.launcher.tiles)==21;print('21 apps; scrollbar max',w.launcher.scroll.verticalScrollBar().maximum());w.close()
