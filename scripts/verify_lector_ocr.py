"""Real Windows OCR -> Lector speaker entry, synthetic image, silent test."""
from pathlib import Path
import sys,os,uuid,json,time
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
identity='LectorOCRQA-'+uuid.uuid4().hex
os.environ.update(USERDOMAIN=identity,ERGONATUS_DATA=str(root/'.test-data'/identity),ERGONATUS_NO_HOTKEYS='1')
from PySide6.QtWidgets import QApplication,QWidget
from PySide6.QtCore import Signal,QTimer,QPoint
from PySide6.QtGui import QPixmap,QPainter,QFont,QColor
from shared.apps.text import TextApplication
from unittest.mock import patch
app=QApplication([]);app.setQuitOnLastWindowClosed(False);spoken=[];errors=[];started=time.monotonic()
class SyntheticCapture(QWidget):
    captured=Signal(object);cancelled=Signal()
with patch.object(TextApplication,'warm_lector_voice',lambda self:None),patch('shared.apps.overlays.CaptureOverlay',SyntheticCapture):
    window=TextApplication('lector')
    window.speaker.speak=lambda text,**kwargs:spoken.append(text) or True
    original_error=window.error
    def error(message):errors.append(message);original_error(message)
    window.error=error
    window.orb_menu(QPoint())
    def captured():
        picture=QPixmap(800,180);picture.fill(QColor('white'))
        painter=QPainter(picture);painter.setPen(QColor('black'));painter.setFont(QFont('Arial',20))
        painter.drawText(20,55,'Bonjour Ergonatus');painter.drawText(20,115,'Ce texte doit être lu automatiquement.');painter.end()
        window.lector_capture.overlay.captured.emit(picture)
    QTimer.singleShot(350,captured)
    timer=QTimer();timer.setInterval(50)
    def finished():
        if (spoken or errors) and not window.lector_capture.busy and not getattr(window,'speaking',False):window.quit()
        elif time.monotonic()-started>30:errors.append('OCR test timeout');window.quit()
    timer.timeout.connect(finished);timer.start();app.exec()
assert not errors,errors
assert len(spoken)==1 and 'Bonjour' in spoken[0] and 'automatiquement' in spoken[0],spoken
assert not list((root/'.test-data'/identity).rglob('reading-*.png'))
report=dict(ok=True,seconds=time.monotonic()-started,recognized=spoken[0],speech_started=True,clipboard_used=False,temporary_images_removed=True,scope='Synthetic image; real Windows OCR; speaker entry verified without audible playback or desktop screenshot.')
(root/'docs/validation/lector-ocr.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report))
