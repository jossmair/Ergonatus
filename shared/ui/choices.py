"""Compact rounded selectors with a readable, consistently styled popup."""
from PySide6.QtCore import Qt,QRectF,QPointF
from PySide6.QtGui import QPainter,QColor,QPen
from PySide6.QtWidgets import QComboBox,QListView

class ChoiceBox(QComboBox):
    def __init__(self,*args):
        super().__init__(*args);self.setCursor(Qt.PointingHandCursor);self.setMinimumHeight(36);self.setView(QListView());self.setMaxVisibleItems(9)
        self.view().setStyleSheet('QListView {background:#FFFFFF;color:#21364D;border:1px solid #A8BCBE;border-radius:10px;padding:6px;outline:0;font:10pt "Segoe UI";} QListView::item {padding:9px 12px;border-radius:6px;min-height:20px;} QListView::item:selected {background:#DDEFEA;color:#173E35;} QListView::item:hover {background:#EFF7F4;}')
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setBrush(QColor('#FFFFFF'));p.setPen(QPen(QColor('#5C8B81') if self.underMouse() else QColor('#A8BCBE'),1));p.drawRoundedRect(QRectF(self.rect()).adjusted(.5,.5,-.5,-.5),9,9);p.setPen(QColor('#21364D'));p.setFont(self.font());p.drawText(self.rect().adjusted(12,0,-30,0),Qt.AlignVCenter,self.fontMetrics().elidedText(self.currentText(),Qt.ElideRight,max(0,self.width()-44)));x=self.width()-17;y=self.height()/2;p.setPen(QPen(QColor('#527A70'),1.8,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));p.drawPolyline([QPointF(x-4,y-2),QPointF(x,y+2),QPointF(x+4,y-2)]);p.end()
