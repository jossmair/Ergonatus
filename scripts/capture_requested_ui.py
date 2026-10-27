from pathlib import Path
import sys,os,tempfile,uuid,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));OUT=ROOT/'output/ui-revision-2026-10-27/captures';OUT.mkdir(parents=True,exist_ok=True)
os.environ.update(USERDOMAIN='RequestedUI'+uuid.uuid4().hex,ERGONATUS_DATA=tempfile.mkdtemp(),ERGONATUS_TEST_MODE='1',ERGONATUS_NO_HOTKEYS='1')
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt,QThreadPool
from suite_design import install
app=QApplication([]);install(app);windows=[]
def show(w,key):
 app.setApplicationName(key);windows.append(w);w.show();QTest.qWait(180);return w
def snap(w,key):
 QTest.qWait(180);w.grab().save(str(OUT/(key+'.png')));print(key,flush=True)
from shared.apps.corrector import CorrectorWindow
w=show(CorrectorWindow(),'Corrector');w.chat.begin('Les enfant mange des pomme.');w.output.setPlainText('Les enfants mangent des pommes.');snap(w,'corrector-sms');w.hide()
from shared.apps.learning import ExplainWindow,DictionaryWindow,TablesWindow
w=show(ExplainWindow(),'Explicator');w.chat.begin('Léa a trois boîtes contenant chacune des billes. Comment trouver le total ?');w.show_explanation("Ce qu'on cherche\nLe total de billes.\nUn indice\nDessine les groupes, puis représente leur contenu.\nÀ toi\nQuelle opération permet de réunir ces groupes ?");w.next_button.setEnabled(True);snap(w,'explicator-sms');w.hide()
w=show(DictionaryWindow(),'Dictionnator');w.word.setText('souris');w.lookup();QTest.qWait(500);snap(w,'dictionary');w.word.setFocus();w.word.clear();QTest.keyClicks(w.word,'math');QTest.qWait(400);snap(w.completer.popup(),'dictionary-completion');w.completer.popup().hide();w.recent.showPopup();QTest.qWait(100);snap(w.recent.view().window(),'dictionary-history');w.recent.hidePopup();w.hide()
from shared.apps.tools import ToolsApplication
w=show(ToolsApplication('communicator'),'Communicator');w.select_card(dict(text='Je veux essayer seul'));snap(w,'communicator');w.hide()
w=show(ToolsApplication('calculinator'),'Calculinator');w.expression.setText('5x^2-4x+6');w.expression.clearFocus();w.result.setText('12');snap(w,'calculator');w.hide()
from shared.apps.timer_widget import TemporatorWindow
w=show(TemporatorWindow(),'Temporator');w.visual_choice.setChecked(True);w.show_widget();snap(w.widget,'timer');w.widget.hide();w.hide()
from shared.apps.sticky_wall import MemorinatorWindow
w=show(MemorinatorWindow(),'Memorinator');w.add_note().editor.setPlainText('Une idée à retenir.');snap(w,'notes');w.hide()
from shared.apps.planner_agenda import PlaninatorWindow
w=show(PlaninatorWindow(),'Planinator');w.set_view('Mois');snap(w,'planner');w.hide()
from shared.apps.organizer_workspace import OrganisatorWindow
from shared.apps.organizer_binder import BinderWindow
w=show(OrganisatorWindow(desktop=Path(tempfile.mkdtemp())),'Organisator');b=BinderWindow(w);b.reveal();snap(b,'binder');b.hide();w.hide()
from shared.apps.translator_chat import TraductorWindow
w=show(TraductorWindow(),'Traductor');w.source.showPopup();snap(w.source.view().window(),'translation-languages');w.source.hidePopup();w.job_id='pending-example';app._suite_interactions.poll();QTest.qWait(380);app._suite_interactions.poll();snap(app._suite_interactions.hourglass,'hourglass');w.job_id=None;app._suite_interactions.poll()
menu=w.create_orb_menu();menu.popup(w.mapToGlobal(w.rect().center()));snap(menu,'orb-menu');menu.hide();app._suite_interactions.show_help(w,'traductor');snap(w._suite_help_dialog,'help');w._suite_help_dialog.close();w.hide()
w=show(TablesWindow(),'Tablinator');w.board.card_for(3,4).animations=False;w.board.card_for(3,4).click();snap(w,'tables');w.hide()
for w in windows:
 if hasattr(w,'cleanup'):w.cleanup()
QThreadPool.globalInstance().waitForDone(5000)
os._exit(0)
