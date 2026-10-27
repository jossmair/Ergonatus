from pathlib import Path
import sys,os,tempfile,uuid,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.update(ERGONATUS_TEST_MODE='1',ERGONATUS_NO_HOTKEYS='1',ERGONATUS_BACKGROUND_START='1',ERGONATUS_DATA=tempfile.mkdtemp(prefix='suite-details-'),USERDOMAIN='VisualDetails'+uuid.uuid4().hex)
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThreadPool
from suite_design import install
app=QApplication([]);install(app);out=ROOT/'docs/validation/modern-2026-10-24';out.mkdir(exist_ok=True)
def capture(widget,name):
    widget.show();limit=time.monotonic()+.4
    while time.monotonic()<limit:app.processEvents();time.sleep(.01)
    widget.grab().save(str(out/(name+'.png')))
from shared.apps.translator_chat import TraductorWindow
w=TraductorWindow();app.setApplicationName('Traductor');w.add_bubble('Bonjour, je voudrais un verre d’eau.','fr',True);w.add_bubble('Hello, I would like a glass of water.','en');capture(w,'traductor-rempli');w.cleanup();w.hide()
from shared.apps.planner_agenda import PlaninatorWindow
from datetime import date,timedelta
p=PlaninatorWindow();app.setApplicationName('Planinator');p.student_choice.setChecked(True)
for day,subject,note in [(date.today(),'Mathématiques','Réviser les fractions et apporter le cahier.'),(date.today()+timedelta(days=1),'Français','Relire le texte et préparer trois idées.')]:
    p.edit_event(day);p.dialog.subject.setCurrentText(subject);p.dialog.notes.setPlainText(note);p.dialog.save()
p.set_view('Mois');capture(p,'planinator-rempli');p.widget.refresh();capture(p.widget,'planinator-widget-clair');p.cleanup();p.hide()
from shared.apps.sticky_wall import MemorinatorWindow
m=MemorinatorWindow();app.setApplicationName('Memorinator')
for text in ['Pour demain\nPréparer le cahier et la trousse.','Une idée à garder\nFaire une pause après les exercices.','À relire\nLes notes du cours de français.']:m.add_note().editor.setPlainText(text)
capture(m,'memorinator-rempli');m.cleanup();m.hide()
from shared.apps.timer_widget import TemporatorWindow
t=TemporatorWindow();app.setApplicationName('Temporator');t.set_visual(False);capture(t.widget,'temporator-chiffres-clair');t.set_visual(True);capture(t.widget,'temporator-visuel-clair');t.cleanup();t.hide()
from shared.apps.app_launcher import ApplinatorWindow
a=ApplinatorWindow(preload=False);app.setApplicationName('Applinator');a.catalog=[dict(name=name,path=str(ROOT/folder/'runtime'/(folder+'.exe'))) for name,folder in [('Écrinator','Ecrinator'),('PDFinator','PDFinator'),('Calculinator','Calculinator')]];a.shortcuts=list(a.catalog);a.refresh();capture(a,'applinator-choix-clair');a.overlay.reveal();capture(a.overlay,'applinator-widget-clair');a.cleanup();a.hide()
QThreadPool.globalInstance().waitForDone(10000)
print('Captures de contenu et widgets réalisées')
