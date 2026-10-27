"""Reproducible local timing on 1,000 synthetic events in isolated storage."""
import os
import uuid
import sys
import time
import json
from pathlib import Path
from datetime import date,datetime
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
os.environ['ERGONATUS_DATA']=str(root/'.qa'/('planinator-perf-'+uuid.uuid4().hex))
os.environ['ERGONATUS_NO_HOTKEYS']='1';os.environ['USERDOMAIN']='QA-'+uuid.uuid4().hex
from PySide6.QtWidgets import QApplication
from shared.apps.planner_agenda import PlaninatorWindow
app=QApplication([]);start=time.perf_counter();w=PlaninatorWindow();w.show();app.processEvents();startup=time.perf_counter()-start
base=datetime.combine(date.today(),datetime.min.time()).timestamp()
for i in range(1000):
    start=base+(i%120)*86400+32400+(i//120)*600
    w.agenda.save(dict(name='Rendez-vous '+str(i+1),when=start,end=start+3600,notes='Informations conservées localement.'))
start=time.perf_counter();w.changed();app.processEvents();week=time.perf_counter()-start
start=time.perf_counter();w.set_view('Mois');app.processEvents();month=time.perf_counter()-start
start=time.perf_counter();w.activate();app.processEvents();widget=time.perf_counter()-start
result=dict(events=1000,source_first_window_seconds=round(startup,3),week_refresh_seconds=round(week,3),month_refresh_seconds=round(month,3),widget_show_seconds=round(widget,3),note='Mesure locale unique, pas un benchmark matériel universel.')
(root/'docs/validation/planinator-performance.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=True))
w.cleanup();w.closing=True;w.layout_timer.stop();w.orb.close();w.tray.hide();w.server.close();w.records.close();w.close();app.processEvents()
