from pathlib import Path
import os,sys,time,uuid,tempfile,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));OUT=ROOT/'output/audit/2026-10-26-visual-speed';CAP=OUT/'latest-source';CAP.mkdir(exist_ok=True)
os.environ.update(USERDOMAIN='LatestVisual'+uuid.uuid4().hex,ERGONATUS_DATA=tempfile.mkdtemp(),ERGONATUS_TEST_MODE='1',ERGONATUS_NO_HOTKEYS='1',ERGONATUS_BACKGROUND_START='1')
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from suite_design import install
app=QApplication([]);install(app)
from shared.apps.tools import ToolsApplication
from shared.apps.text import TextApplication
from shared.apps.learning import DictionaryWindow,ExplainWindow,TablesWindow
from shared.apps.corrector import CorrectorWindow
from shared.apps.translator_chat import TraductorWindow
from shared.apps.planner_agenda import PlaninatorWindow
from shared.apps.sticky_wall import MemorinatorWindow
from shared.apps.timer_widget import TemporatorWindow
from shared.apps.organizer_workspace import OrganisatorWindow
from shared.apps.app_launcher import ApplinatorWindow
factories={'communicator':lambda:ToolsApplication('communicator'),'calculinator':lambda:ToolsApplication('calculinator'),'scanator':lambda:TextApplication('scanator'),'lector':lambda:TextApplication('lector'),'dictionnator':DictionaryWindow,'explicator':ExplainWindow,'tablinator':TablesWindow,'corrector':CorrectorWindow,'traductor':TraductorWindow,'planinator':PlaninatorWindow,'memorinator':MemorinatorWindow,'temporator':TemporatorWindow,'organisator':lambda:OrganisatorWindow(desktop=Path(tempfile.mkdtemp())),'applinator':lambda:ApplinatorWindow(preload=False),'concentrator':lambda:ToolsApplication('concentrator')}
rows=[];windows=[]
for key,factory in factories.items():
    app.setApplicationName(key);start=time.perf_counter();w=factory();windows.append(w);w.show();app.processEvents();elapsed=time.perf_counter()-start;QTest.qWait(250);w.grab().save(str(CAP/(key+'.png')))
    rows.append(dict(app=key,in_process_first_paint_seconds=round(elapsed,4),width=w.width(),height=w.height()));print(key,flush=True)
    if key=='tablinator':
        w.toggle_widget();QTest.qWait(200);w.widget.grab().save(str(CAP/'tablinator-widget.png'));w.widget.hide()
    w.hide()
    if hasattr(w,'cleanup'):w.cleanup()
    if hasattr(w,'layout_timer'):w.layout_timer.stop()
    if hasattr(w,'orb'):w.orb.hide()
(OUT/'latest-source-timings.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
os._exit(0)
