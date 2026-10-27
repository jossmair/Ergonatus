"""Isolated native Qt validation; never touches the user's agenda."""
import os
import sys
import json
import uuid
from pathlib import Path
from datetime import datetime,date,time,timedelta
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
out=root/'docs/validation';out.mkdir(exist_ok=True)
os.environ['ERGONATUS_DATA']=str(root/'.qa'/('planinator-'+uuid.uuid4().hex))
os.environ['ERGONATUS_NO_HOTKEYS']='1';os.environ['USERDOMAIN']='QA-'+uuid.uuid4().hex
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from shared.apps.planner_agenda import PlaninatorWindow

app=QApplication([]);app.setQuitOnLastWindowClosed(False);w=PlaninatorWindow()
for offset,hour,title,category,place in ((0,9,'Préparer la semaine','Personnel','À la maison'),(0,14,'Rendez-vous orthophonie','Santé','Cabinet · dossier à apporter'),(1,10,'Réunion avec l’équipe','École','Salle 2'),(2,15,'Projet de groupe','Travail','Bibliothèque'),(4,18,'Dîner en famille','Famille','Chez nous')):
    start=datetime.combine(date.today()+timedelta(days=offset),time(hour)).timestamp()
    w.agenda.save(dict(name=title,when=start,end=start+3600,category=category,place=place,notes='Les informations utiles sont conservées ici.'))
w.changed();w.show()
report={}
def capture():
    try:
        app.processEvents();w.grab().save(str(out/'planinator-week.png'))
        w.activate();app.processEvents();w.widget.grab().save(str(out/'planinator-widget.png'))
        assert w.widget.grab().toImage().pixelColor(0,0).alpha()==0
        report['widget_alpha_corner']=0;report['events']=len(w.agenda.events())
        w.activate();assert not w.widget.isVisible();w.set_view('Mois');app.processEvents();w.grab().save(str(out/'planinator-month.png'))
        w.edit_event(date.today());app.processEvents();w.dialog.grab().save(str(out/'planinator-editor.png'));w.dialog.reject();app.processEvents()
        w.orb.doubleActivated.emit('planinator');assert w.isVisible()
        report['orb_toggle_and_double_click']=True;report['passed']=True
        (out/'planinator-native.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        w.cleanup();app.exit(0)
    except Exception:
        import traceback;traceback.print_exc();app.exit(1)
QTimer.singleShot(700,capture);sys.exit(app.exec())
