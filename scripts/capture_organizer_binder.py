from pathlib import Path
import os,sys,tempfile,uuid,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.update(ERGONATUS_DATA=tempfile.mkdtemp(),ERGONATUS_NO_HOTKEYS='1',ERGONATUS_TEST_MODE='1',USERDOMAIN='BinderVisual'+uuid.uuid4().hex)
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEvent,QThreadPool
from suite_design import install
from shared.apps.organizer_workspace import OrganisatorWindow
from shared.organizer import create_space
import pymupdf
app=QApplication([]);app.setApplicationName('Organisator');install(app)
desktop=Path(tempfile.mkdtemp());root,config=create_space(desktop,'Mon classeur de collège','Collège')
with pymupdf.open() as pdf:
    for title,subtitle in [('Les fractions','Comprendre les parts d’un tout'),('À vous de jouer','Lire, comparer et représenter')]:
        page=pdf.new_page();page.draw_rect(pymupdf.Rect(0,0,595,120),color=None,fill=(.89,.95,.9));page.insert_text((44,48),'MATHÉMATIQUES  /  COURS',fontsize=11,color=(.22,.40,.29));page.insert_text((44,83),title,fontsize=25,color=(.12,.27,.18));page.insert_text((44,160),subtitle,fontsize=17,color=(.12,.27,.18))
        for i,line in enumerate(['Une fraction exprime une partie d’une unité.','Le numérateur indique le nombre de parts choisies.','Le dénominateur indique le nombre total de parts.']):page.insert_text((44,210+i*30),line,fontsize=12)
        for i in range(4):page.draw_rect(pymupdf.Rect(50+i*85,330,126+i*85,415),color=(.45,.65,.5),fill=(.48,.72,.55) if i<3 else (1,1,1))
        page.insert_text((50,455),'3 parts coloriées sur 4 : trois quarts.',fontsize=14,color=(.15,.34,.21));page.insert_text((44,760),'Mon classeur  /  Chapitre 3',fontsize=10,color=(.4,.5,.42))
    pdf.save(root/'Mathématiques/Cours/01 - Les fractions.pdf')
for name,text in [('02 - À retenir.txt','Une fraction représente une partie du tout.\n\nJe repère le numérateur et le dénominateur.'),('03 - Ma méthode.txt','Je lis la consigne.\nJe dessine les parts.\nJe vérifie ma réponse.')]: (root/'Mathématiques/Cours'/name).write_text(text,encoding='utf-8')
(root/'Français/Cours/La poésie.txt').write_text('Les mots et les images.\n\nLire à voix haute, repérer les rimes.',encoding='utf-8')
w=OrganisatorWindow(desktop);w.use_space(root,config);w.toggle_binder();b=w.binder
out=ROOT/'output/audit/current/captures';out.mkdir(parents=True,exist_ok=True)
def until(predicate,timeout=10):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        app.processEvents();app.sendPostedEvents(None,QEvent.DeferredDelete);time.sleep(.02)
        if predicate():return
    assert predicate()
until(lambda:len(b.documents)==4)
b.set_section('Mathématiques',animate=False);until(lambda:b.current is not None and b.open_button.isEnabled());b.canvas.turn.animation.stop();b.canvas.turn.hide();app.processEvents()
b.grab().save(str(out/'organisator-classeur-plein-ecran.png'))
b.opacity_slider.setValue(45);app.processEvents();b.grab().save(str(out/'organisator-classeur-fond45.png'));b.opacity_slider.setValue(88)
b.step(1);until(lambda:b.page==1 and b.open_button.isEnabled());b.canvas.turn.animation.pause();b.canvas.turn.set_progress(.32);app.processEvents();b.grab().save(str(out/'organisator-classeur-page-tournee.png'));b.canvas.turn.animation.stop();b.canvas.turn.hide()
w.closing=True;w.cleanup();QThreadPool.globalInstance().waitForDone(10000);app.processEvents();w.layout_timer.stop();w.orb.close();w.server.close();w.records.close();w.close()
print('Classeur plein écran, opacité et page tournée capturés.')
