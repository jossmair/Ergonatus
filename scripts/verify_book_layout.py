from pathlib import Path
import sys,json,time
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter,QColor,QFont
from shared.reading_layout import recognize_reading
app=QApplication([]);folder=root/'.test-data/book-layout';folder.mkdir(parents=True,exist_ok=True)
image=QImage(1200,420,QImage.Format_RGB32);image.fill(QColor('white'));painter=QPainter(image);painter.setFont(QFont('Arial',18));painter.setPen(QColor('black'))
for x,title,first,second in [(25,'Page gauche','Premier paragraphe.','Deuxième paragraphe.'),(625,'Page droite','Troisième paragraphe.','Quatrième paragraphe.')]:
    for y,text in [(65,title),(140,first),(265,second)]:painter.drawText(x,y,text)
painter.end();path=folder/'double-page.png';assert image.save(str(path))
started=time.monotonic();text=recognize_reading(path,True)
assert 'gauche' in text and 'droite' in text and text.index('gauche')<text.index('droite') and '\n\n' in text
assert not list(folder.glob('*-page-*.png'))
report=dict(ok=True,seconds=time.monotonic()-started,text=text,scope='Synthetic double-page photograph; actual Windows OCR; no camera opened.')
(root/'docs/validation/lector-book-layout.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report))
