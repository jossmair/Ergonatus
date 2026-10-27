"""Generated green hourglass; calm animation, no focus or pointer interception."""
import math,time
from PySide6.QtCore import Qt,QTimer,QRectF
from PySide6.QtGui import QPainter,QColor,QPixmap,QCursor,QPainterPath,QLinearGradient,QPolygonF,QPen
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QWidget,QApplication
from shared.catalog import suite_root

class ReadingBusy(QWidget):
    def __init__(self,title='Lector · préparation de la lecture',accessible_name='Patientez, la lecture se prépare'):
        super().__init__(None,Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.WindowTransparentForInput|Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground);self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(132,142);self.setWindowTitle(title);self.setAccessibleName(accessible_name)
        self.picture=QPixmap(str(suite_root()/'assets/lector/hourglass-frame.png'));self.started=0;self.phase=0
        self.timer=QTimer(self);self.timer.setInterval(40);self.timer.timeout.connect(self.advance)
    def begin(self,animated=True):
        if self.isVisible():return
        screen=QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen();area=screen.availableGeometry()
        self.move(area.center().x()-self.width()//2,area.center().y()-self.height()//2)
        self.started=time.monotonic();self.phase=0;self.show()
        if animated:self.timer.start()
        self.update()
    def finish(self):self.timer.stop();self.hide()
    def advance(self):self.phase=time.monotonic()-self.started;self.update()
    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing);painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setPen(QColor('#6C9F36'));painter.setBrush(QColor(8,24,15,230));painter.drawRoundedRect(1,1,130,140,18,18)
        painter.save();painter.translate(66,58)
        cycle=self.phase%5;progress=min(1,cycle/4.3);turn=max(0,min(1,(cycle-4.3)/.7));turn=turn*turn*(3-2*turn)
        painter.rotate(turn*180);painter.scale(64/1024,96/1536)
        painter.drawPixmap(QRectF(-512,-768,1024,1536),self.picture,QRectF(self.picture.rect()))
        top=QPainterPath();top.moveTo(0,-15);top.cubicTo(-40,-150,-290,-200,-280,-450);top.cubicTo(-280,-620,280,-620,280,-450);top.cubicTo(290,-200,40,-150,0,-15)
        bottom=QPainterPath();bottom.moveTo(0,15);bottom.cubicTo(40,170,280,220,280,450);bottom.cubicTo(280,580,-280,580,-280,450);bottom.cubicTo(-280,220,-40,170,0,15)
        gradient=QLinearGradient(-200,0,220,0);gradient.setColorAt(0,QColor('#3C922A'));gradient.setColorAt(.55,QColor('#BBF579'));gradient.setColorAt(1,QColor('#60BA3F'))
        painter.save();painter.setClipPath(top);painter.fillRect(QRectF(-300,-510+progress*495,600,550),gradient);painter.restore()
        peak=520-progress*500;painter.save();painter.setClipPath(bottom);painter.setPen(Qt.NoPen);painter.setBrush(gradient);painter.drawPolygon(QPolygonF([QPointF(-280,535),QPointF(280,535),QPointF(0,peak)]));painter.restore()
        if progress<1:
            painter.setPen(QPen(QColor('#C7FF8C'),8))
            for index in range(9):
                y=18+(self.phase*230+index*49)%max(20,peak-18);painter.drawPoint(QPointF(math.sin(index)*4,y))
        painter.restore();painter.setPen(QColor('#E2F3D9'));painter.drawText(QRectF(8,111,116,25),Qt.AlignCenter,'Patientez…')
