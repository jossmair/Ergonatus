from pathlib import Path
import os,sys,tempfile,time,uuid,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.update(ERGONATUS_DATA=tempfile.mkdtemp(),USERDOMAIN='InteractionVisual'+uuid.uuid4().hex,ERGONATUS_NO_HOTKEYS='1')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThreadPool
from PySide6.QtTest import QTest
from suite_design import install
from shared.apps.learning import ExplainWindow
app=QApplication([]);app.setApplicationName('Explicator');install(app);w=ExplainWindow();w.show();QTest.qWait(200);out=ROOT/'output/audit/current/captures'
menu=w.create_orb_menu();menu.popup(w.geometry().center());QTest.qWait(150);menu.grab().save(str(out/'suite-orb-menu-explicator.png'));menu.close()
w.start_task(lambda event:time.sleep(1.8),lambda result:None);QTest.qWait(650);busy=app._suite_interactions.hourglass;assert busy.isVisible();busy.grab().save(str(out/'suite-hourglass.png'));QTest.qWait(200);busy.grab().save(str(out/'suite-hourglass-grains.png'));QTest.qWait(1300);assert not busy.isVisible()
w.closing=True;w.cleanup();QThreadPool.globalInstance().waitForDone(5000);w.layout_timer.stop();w.orb.close();w.tray.hide();w.server.close();w.records.close();w.close();app.processEvents()
print('Menu explicite et sablier animé capturés, fin de traitement vérifiée.')
