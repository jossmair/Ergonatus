"""Real Windows OCR, synthetic image, rich MIME inspection without touching the clipboard."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap,QPainter,QFont,QColor
from PySide6.QtCore import QMimeData
from shared.ocr import recognize,format_text,clipboard_html
app=QApplication([]);folder=ROOT/'.test-data/scan-ocr-native';folder.mkdir(parents=True,exist_ok=True)
picture=QPixmap(700,180);picture.fill(QColor('white'));painter=QPainter(picture);painter.setPen(QColor('black'));painter.setFont(QFont('Arial',18));painter.drawText(20,55,'Bonjour Ergonatus');painter.drawText(20,110,'Le texte est prêt à copier.');painter.end()
path=folder/'synthetic.png';assert picture.save(str(path))
raw=recognize(path);text=format_text(raw,'paragraphs');html=clipboard_html(text,'paragraphs')
mime=QMimeData();mime.setText(text);mime.setHtml(html)
assert 'Bonjour' in text and 'copier' in text and mime.hasText() and mime.hasHtml()
report=dict(ok=True,raw=raw,text=text,html=html,mime_formats=list(mime.formats()),scope='Synthetic image; actual Windows OCR; MIME inspected in memory, no personal clipboard write or desktop capture.')
(ROOT/'docs/validation/scan-ocr-rich.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=True))
