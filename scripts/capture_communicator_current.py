from pathlib import Path
import sys,os,tempfile,uuid,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.update(ERGONATUS_DATA=tempfile.mkdtemp(),ERGONATUS_NO_HOTKEYS='1',ERGONATUS_TEST_MODE='1',ERGONATUS_BACKGROUND_START='1',USERDOMAIN='CommunicatorDesign'+uuid.uuid4().hex)
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEvent
from suite_design import install
from shared.apps.tools import ToolsApplication
app=QApplication([]);app.setApplicationName('Communicator');install(app);w=ToolsApplication('communicator');w.show()
out=ROOT/'output/audit/current/captures'
def capture(name):
    until=time.monotonic()+.35
    while time.monotonic()<until:app.processEvents();app.sendPostedEvents(None,QEvent.DeferredDelete);time.sleep(.01)
    w.grab().save(str(out/name))
capture('communicator-redesigned.png')
w.category.setCurrentText('Autonomie');capture('communicator-autonomie.png')
w.select_card(dict(text='Je communique avec ce tableau'));w.compose_button.setChecked(True);w.select_card(dict(text='Laissez-moi le temps de répondre'));capture('communicator-message.png')
w.resize(720,620);capture('communicator-compact.png')
assert all(w.board_widget.rect().contains(b.mapTo(w.board_widget,b.rect().bottomRight())) for b in w.card_buttons)
w.cleanup();w.closing=True;w.orb.close();w.server.close();w.records.close();w.close();app.processEvents()
