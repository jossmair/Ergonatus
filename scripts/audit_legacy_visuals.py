from pathlib import Path
import sys,os,tempfile
ROOT=Path(__file__).resolve().parents[1];key=sys.argv[1];source=ROOT/key/'source';sys.path.insert(0,str(source));sys.path.insert(0,str(ROOT))
os.environ.update(TRANSCRI_DATA=tempfile.mkdtemp(prefix='transcri-visual-'),REDACTOR_DATA_DIR=tempfile.mkdtemp(prefix='redactor-visual-'))
from PySide6.QtWidgets import QApplication
app=QApplication([]);app.setApplicationName(key)
if key=='Claviernator':
    from fortinatus.config import Settings
    from fortinatus.controller import Controller
    from fortinatus.ui import MainWindow
    from fortinatus.theme import configure_app
    configure_app(app);folder=Path(tempfile.mkdtemp());controller=Controller(Settings(),folder/'settings.json',no_hooks=True);window=MainWindow(controller,folder)
elif key=='Precisionator':
    from services.configuration import Preferences
    from ui.settings_window import SettingsWindow
    from ui.theme import configure_app
    configure_app(app);window=SettingsWindow(Preferences(),mouse_speed=10)
elif key=='Transcrinator':
    from app.core.settings import Settings
    from app.core.device_detector import Hardware
    from app.core.controller import Controller
    from app.ui.main_window import MainWindow
    from app.ui.premium import STYLE
    app.setStyleSheet(STYLE);controller=Controller(Settings(),Hardware('PC',4,16*2**30,8*2**30));window=MainWindow(controller)
elif key=='Redactor':
    from app import theme
    from app.config import Config
    from app.ui.main_window import MainWindow
    theme.configure_app(app);window=MainWindow(Config(animation='none'))
from suite_design import install
install(app);window.show();app.processEvents();app.processEvents()
out=ROOT/'output/audit/2026-10-26-visual-speed/latest-source'/(key.lower()+'.png');window.grab().save(str(out));print(out)
