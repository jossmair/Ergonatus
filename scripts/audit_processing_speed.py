from pathlib import Path
import os,sys,time,json,tempfile,uuid,threading,statistics,psutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));OUT=ROOT/'output/audit/2026-10-26-visual-speed'
if '--after' in sys.argv:OUT=OUT/'after'
OUT.mkdir(parents=True,exist_ok=True)
identity='ProcessingAudit'+uuid.uuid4().hex
os.environ.update(USERDOMAIN=identity,ERGONATUS_DATA=tempfile.mkdtemp(),ERGONATUS_NO_HOTKEYS='1')
from shared import catalog
catalog.suite_root=lambda:Path('C:/Users/Josselin/Desktop/Ergonatus')
rows=[]
def measured(name,fn):
    start=time.perf_counter()
    try:result=fn();row=dict(test=name,seconds=round(time.perf_counter()-start,4),result=result)
    except Exception as e:row=dict(test=name,seconds=round(time.perf_counter()-start,4),error=str(e))
    rows.append(row);(OUT/'processing.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(row,ensure_ascii=True),flush=True)
try:
    from shared.dictionary import lookup
    for word in ['chat','photosynthèse','responsabilité','hipopotame','chat']:
        measured('dictionary:'+word,lambda word=word:{k:v for k,v in lookup(word).items() if k!='html'})
    from PySide6.QtGui import QImage,QPainter,QFont,QColor
    from PySide6.QtWidgets import QApplication
    app=QApplication([]);im=QImage(1100,180,QImage.Format_RGB32);im.fill(QColor('white'));p=QPainter(im);p.setPen(QColor('black'));p.setFont(QFont('Arial',26));p.drawText(25,70,'Les élèves préparent leur exercice de mathématiques.');p.end();image=OUT/'ocr-input.png';im.save(str(image))
    from shared.ocr import recognize
    measured('ocr:first',lambda:recognize(image));measured('ocr:repeat',lambda:recognize(image))
    if '--after' in sys.argv:
        from ergoai.correction import correct
    else:
        from ergoai.proofreading_client import correct
    text="Hier, je suis aller au magasin avec mes amis. On a acheter plusieurs chose mais les prix était trop chère. Ensuite, nous somme rentrer chez nous parce qu'il commencer à pleuvoir. J'ai oublier mon sac dans la voiture et personne ne la retrouver. Demain, je retournerais le chercher si j'ai le temp."
    measured('corrector:first-long',lambda:correct(text,threading.Event()))
    measured('corrector:warm-short',lambda:correct('Les petite fille joue dans le jardin.',threading.Event()))
    from ergoai.learning import ask
    measured('explicator:hint',lambda:ask('explain','Léa a 3 boîtes de 4 billes. Combien a-t-elle de billes au total ?',threading.Event(),level='Primaire'))
finally:
    for p in psutil.process_iter(['exe']):
        try:
            if p.info['exe'] and 'ergoai' in p.info['exe'].lower() and p.environ().get('USERDOMAIN')==identity:
                p.terminate();p.wait(timeout=8)
        except (psutil.Error,OSError):pass
