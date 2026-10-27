"""Capture current learning interfaces using offline dictionary and real model evidence."""
from pathlib import Path
import os,sys,uuid,tempfile,time,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.update(ERGONATUS_DATA=tempfile.mkdtemp(),USERDOMAIN='LearningVisual'+uuid.uuid4().hex,ERGONATUS_NO_HOTKEYS='1',ERGONATUS_TEST_MODE='1')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QThreadPool
from PySide6.QtGui import QImage,QPainter,QFont,QColor
from suite_design import install
from shared.apps.learning import DictionaryWindow,ExplainWindow,TablesWindow
app=QApplication([]);install(app);OUT=ROOT/'output/audit/current/captures';OUT.mkdir(exist_ok=True)
def until(predicate):
 end=time.monotonic()+12
 while not predicate():
  assert time.monotonic()<end
  app.processEvents();time.sleep(.02)
def close(w):
 w.closing=True;w.cleanup();QThreadPool.globalInstance().waitForDone(10000);app.processEvents();w.layout_timer.stop();w.orb.close();w.tray.hide();w.server.close();w.records.close();w.close();app.processEvents()
app.setApplicationName('Dictionnator');w=DictionaryWindow();w.show();w.word.setText('fraction');w.lookup();until(lambda:not w.busy);app.processEvents();w.grab().save(str(OUT/'dictionnator-local.png'));close(w)
# Real Windows OCR on a readable synthetic exercise image; never captures user content.
image=QImage(1450,230,QImage.Format_RGB32);image.fill(QColor('white'));p=QPainter(image);p.setPen(QColor('black'));p.setFont(QFont('Segoe UI',24));p.drawText(30,70,'Léa a 3 boîtes de 4 billes.');p.drawText(30,145,'Combien a-t-elle de billes au total ?');p.end();path=Path(tempfile.gettempdir())/('learning-ocr-'+uuid.uuid4().hex+'.png');image.save(str(path))
from shared.ocr import recognize
try:ocr=recognize(path)
finally:path.unlink(missing_ok=True)
assert 'billes' in ocr.lower();(ROOT/'output/audit/current/learning-real-ocr.txt').write_text(ocr,encoding='utf-8')
app.setApplicationName('Explicator');w=ExplainWindow();w.show();w.source.setPlainText(ocr);evidence=json.loads((ROOT/'output/audit/current/learning-real-results.json').read_text(encoding='utf-8'));w.show_explanation(evidence['hint']['text']);w.next_button.setEnabled(True);app.processEvents();w.grab().save(str(OUT/'explicator-local.png'));close(w)
app.setApplicationName('Tablinator');w=TablesWindow();w.show();w.board.card_for(3,4).animations=False;w.board.card_for(3,4).click();app.processEvents();w.grab().save(str(OUT/'tablinator.png'));w.toggle_widget();w.widget.board.card_for(3,4).animations=False;w.widget.board.card_for(3,4).click();app.processEvents();w.widget.grab().save(str(OUT/'tablinator-widget.png'));close(w)
print('Three current interfaces captured; real Windows OCR verified.')
