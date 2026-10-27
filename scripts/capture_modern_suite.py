from pathlib import Path
import sys,os,tempfile,uuid,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.update(ERGONATUS_TEST_MODE='1',ERGONATUS_NO_HOTKEYS='1',ERGONATUS_BACKGROUND_START='1',ERGONATUS_DATA=tempfile.mkdtemp(prefix='modern-suite-'),USERDOMAIN='ModernQA'+uuid.uuid4().hex)
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThreadPool
from suite_design import install
app=QApplication([]);install(app)
from Hub.fort_hub import HubWindow
from shared.apps.text import TextApplication
from shared.apps.tools import ToolsApplication
from shared.apps.corrector import CorrectorWindow
from shared.apps.translator_chat import TraductorWindow
from shared.apps.planner_agenda import PlaninatorWindow
from shared.apps.sticky_wall import MemorinatorWindow
from shared.apps.timer_widget import TemporatorWindow
from shared.apps.organizer_workspace import OrganisatorWindow
from shared.apps.app_launcher import ApplinatorWindow
OUT=ROOT/'docs/validation/modern-2026-10-24';OUT.mkdir(exist_ok=True)
factories={'hub':lambda:HubWindow(Path(tempfile.mkdtemp())/'hub'),'lector':lambda:TextApplication('lector'),'scanator':lambda:TextApplication('scanator'),'corrector':CorrectorWindow,'traductor':TraductorWindow,'calculinator':lambda:ToolsApplication('calculinator'),'communicator':lambda:ToolsApplication('communicator'),'concentrator':lambda:ToolsApplication('concentrator'),'planinator':PlaninatorWindow,'memorinator':MemorinatorWindow,'temporator':TemporatorWindow,'organisator':lambda:OrganisatorWindow(desktop=Path(tempfile.mkdtemp())),'applinator':lambda:ApplinatorWindow(preload=False)}
windows=[]
for key,factory in factories.items():
    w=factory();windows.append(w);w.show()
    deadline=time.monotonic()+.8
    while time.monotonic()<deadline:app.processEvents();time.sleep(.02)
    w.grab().save(str(OUT/(key+'.png')));print(key,flush=True)
    w.hide()
    if hasattr(w,'cleanup'):w.cleanup()
    if hasattr(w,'layout_timer'):w.layout_timer.stop()
    if hasattr(w,'hub_orb'):w.hub_orb.hide()
QThreadPool.globalInstance().waitForDone(10000)
for w in windows:
    if hasattr(w,'shutting_down'):w.close()
