"""Actual release UI, isolated example data; never capture the user's desktop."""
from pathlib import Path
import os,sys,tempfile,uuid,hashlib,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));OUT=ROOT/'docs/media';OUT.mkdir(parents=True,exist_ok=True)
PUBLISHED=ROOT/'output/releases/2026.10.27/source'
for name in ('Hub/fort_hub.py','suite_design.py','suite_interactions.py','shared/ui/conversation.py','shared/apps/learning.py','shared/apps/communication.py','shared/apps/planner_agenda.py','shared/apps/translator_chat.py','shared/apps/sticky_wall.py'):
    assert (ROOT/name).read_bytes()==(PUBLISHED/name).read_bytes(),('UI differs from release',name)
os.environ.update(USERDOMAIN='GitHubShowcase'+uuid.uuid4().hex,ERGONATUS_DATA=tempfile.mkdtemp(prefix='ergonatus-showcase-'),ERGONATUS_TEST_MODE='1',ERGONATUS_NO_HOTKEYS='1',QT_SCALE_FACTOR='1',QT_FONT_DPI='96')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QThreadPool
from PySide6.QtTest import QTest
from suite_design import install
app=QApplication([]);install(app);windows=[]
def show(w,key,size=None):
    app.setApplicationName(key);windows.append(w)
    if size:w.resize(*size)
    w.show();QTest.qWait(180);return w
def snap(w,name):
    QTest.qWait(250);w.grab().save(str(OUT/(name+'.png')));print(name,flush=True)
def hide(w):
    w.hide()
    if hasattr(w,'orb'):w.orb.hide()
from Hub.fort_hub import HubWindow
h=show(HubWindow(Path(tempfile.mkdtemp())/'hub'),'Ergonatus');snap(h,'hub');h.launcher.opacity_slider.setValue(100);h.launcher.resize(1340,800);h.launcher.rebuild();h.launcher.show();QTest.qWait(200);assert len(h.launcher.tiles)==21 and h.launcher.scroll.verticalScrollBar().maximum()==0;snap(h.launcher,'catalogue');h.launcher.hide();h.hide();h.hub_orb.hide()
from shared.apps.corrector import CorrectorWindow
w=show(CorrectorWindow(),'Corrector',(640,560));w.chat.begin('Je suis aller au collège ce matin.');w.output.setPlainText('Je suis allé au collège ce matin.');w.chat.begin('Les enfant prépare leur exposé.');w.output.setPlainText('Les enfants préparent leur exposé.');snap(w,'corrector');hide(w)
from shared.apps.learning import ExplainWindow,DictionaryWindow,TablesWindow
w=show(ExplainWindow(),'Explicator',(680,650));w.chat.begin('Comment calculer les trois quarts de 20 ?');w.show_explanation("Ce qu'on cherche\nUne partie d’une quantité.\nUn indice\nCommence par partager 20 en quatre groupes égaux.\nÀ toi\nCombien de ces groupes faut-il ensuite prendre ?");w.next_button.setEnabled(True);snap(w,'explicator');hide(w)
w=show(DictionaryWindow(),'Dictionnator',(680,560));w.word.setText('autonomie');w.lookup()
for _ in range(100):
    QTest.qWait(80)
    if not w.busy:break
assert 'autonomie' in w.result.toPlainText().lower();snap(w,'dictionnator');hide(w)
w=show(TablesWindow(),'Tablinator',(900,640))
for a,b in [(3,4),(4,3),(5,5),(7,8)]:c=w.board.card_for(a,b);c.animations=False;c.click()
snap(w,'tablinator');hide(w)
from shared.apps.tools import ToolsApplication
w=show(ToolsApplication('communicator'),'Communicator',(900,680));w.select_card(dict(text='J’ai besoin d’un peu de temps pour répondre.'));snap(w,'communicator');hide(w)
w=show(ToolsApplication('calculinator'),'Calculinator',(600,650));w.student_toggle.setChecked(True);w.toggle_student_mode();w.expression.setText('(x+1)²');w.compute_student('calculate')
for _ in range(100):
    QTest.qWait(80)
    if not w.math_busy:break
snap(w,'calculinator');hide(w)
from shared.apps.translator_chat import TraductorWindow
w=show(TraductorWindow(),'Traductor',(640,560));w.add_bubble('Bonjour, pouvez-vous m’aider à trouver la bibliothèque ?', 'fr',True);w.add_bubble('Hello, could you help me find the library?', 'en');w.add_bubble('Merci beaucoup pour votre aide !','fr',True);w.add_bubble('Thank you very much for your help!','en');snap(w,'traductor');hide(w)
from shared.apps.planner_agenda import PlaninatorWindow
from shared.planner import SUBJECTS
from datetime import date,datetime,timedelta
w=show(PlaninatorWindow(),'Planinator',(1080,680));w.student_choice.setChecked(True);today=date.today();monday=today-timedelta(days=today.weekday())
for offset,subject,caption in [(0,'Français','Préparer la lecture'),(1,'Mathématiques','Réviser les fractions'),(2,'Anglais','Apprendre le vocabulaire'),(3,'SVT','Terminer le schéma'),(4,'Histoire-géographie','Relire la leçon')]:
    when=datetime.combine(monday+timedelta(days=offset),datetime.min.time()).replace(hour=17).timestamp();w.agenda.save(dict(name=caption,when=when,end=when+3600,subject=subject,color=SUBJECTS[subject],notes=caption))
w.set_view('Semaine');w.refresh();snap(w,'planinator');hide(w)
from shared.apps.sticky_wall import MemorinatorWindow
w=show(MemorinatorWindow(),'Memorinator');w.opacity_slider.setValue(100)
for i,text in enumerate(['Mes idées\nUne affiche pour notre projet de classe.','À ne pas oublier\nPrendre mon livre et mon cahier.','Cette semaine\nRéviser les fractions et préparer la lecture.','Une question\nComment expliquer mon idée avec un schéma ?','Pour plus tard\nDécouvrir une nouvelle table de multiplication.','Petit objectif\nAvancer une étape à la fois.']):
    note=w.add_note();note.editor.setPlainText(text);note.move(24+(i%3)*310,24+(i//3)*235)
snap(w,'memorinator');hide(w)
for w in windows:
    w.closing=True
    if hasattr(w,'cleanup'):w.cleanup()
    if hasattr(w,'layout_timer'):w.layout_timer.stop()
    if hasattr(w,'orb'):w.orb.close()
    if hasattr(w,'tray'):w.tray.hide()
    if hasattr(w,'server'):w.server.close()
QThreadPool.globalInstance().waitForDone(10000)
(ROOT/'output/github-showcase').mkdir(exist_ok=True)
(ROOT/'output/github-showcase/captures.json').write_text(json.dumps(dict(release='v2026.10.27',example_data=True,files=[p.name for p in OUT.glob('*.png')]),indent=2))
os._exit(0)
