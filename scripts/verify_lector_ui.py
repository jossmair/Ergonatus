from pathlib import Path
import os,sys,time,uuid,json,subprocess
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
os.environ['USERDOMAIN']='LectorUIQA-'+uuid.uuid4().hex
os.environ['ERGONATUS_DATA']=str(root/'.test-data'/os.environ['USERDOMAIN'])
os.environ['ERGONATUS_NO_HOTKEYS']='1'
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from shared.apps.text import TextApplication
from unittest.mock import patch
app=QApplication([]);app.setQuitOnLastWindowClosed(False)
with patch.object(TextApplication,'warm_lector_voice',lambda self:None):
    window=TextApplication('lector');window.show()
    def capture():
        window.options.toggle.click();app.processEvents()
        assert window.voice_choice.findText('Homme · naturelle')>=0
        window.grab().save(str(root/'docs/validation/lector-options.png'))
        menu=window.create_orb_menu();menu.ensurePolished();menu.adjustSize()
        menu.grab().save(str(root/'docs/validation/lector-menu.png'))
        window.selection_picker.cursor.grab().save(str(root/'docs/validation/lector-reading-cursor.png'))
        window.quit()
    QTimer.singleShot(1800,capture);app.exec()
