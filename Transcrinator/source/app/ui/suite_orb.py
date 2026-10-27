from pathlib import Path
from functools import lru_cache
import sys
from PySide6.QtCore import QRectF,Qt
from PySide6.QtGui import QPixmap,QColor,QPen
@lru_cache(maxsize=8)
def image(key):
    for root in (*Path(__file__).resolve().parents,*Path(sys.executable).resolve().parents):
        path=root/'assets/orbs/clear'/(key+'.png')
        if path.is_file():return QPixmap(str(path))
    return QPixmap()
def draw(painter,rect,key,enabled=True,error=False):
    pix=image(key)
    if pix.isNull():return False
    painter.save();painter.setOpacity(1. if enabled else .55);painter.drawPixmap(rect,pix,QRectF(pix.rect()))
    if error:
        painter.setPen(QPen(QColor('white'),1));painter.setBrush(QColor('#C84448'));painter.drawEllipse(QRectF(rect.right()-rect.width()*.25,rect.top(),rect.width()*.25,rect.height()*.25))
    painter.restore();return True
