from PySide6.QtCore import Qt,QRect,QPoint,Signal
from PySide6.QtGui import QColor,QPainter,QPen,QCursor
from PySide6.QtWidgets import QApplication,QWidget

class CaptureOverlay(QWidget):
    captured=Signal(object);cancelled=Signal()
    def __init__(self):
        super().__init__(None,Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
        self.screen=QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        self.picture=self.screen.grabWindow(0);self.setGeometry(self.screen.geometry());self.start=self.end=None
        self.setCursor(Qt.CrossCursor);self.setFocusPolicy(Qt.StrongFocus);self.setWindowTitle('Choisir la zone de capture · Échap pour annuler')
    def paintEvent(self,event):
        painter=QPainter(self);painter.drawPixmap(self.rect(),self.picture);painter.fillRect(self.rect(),QColor(0,0,0,100))
        if self.start is not None:
            rect=QRect(self.start,self.end).normalized();painter.setPen(QPen(QColor('#FFFFFF'),2));painter.drawRect(rect)
    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton:self.start=event.position().toPoint();self.end=self.start;self.update()
        elif event.button()==Qt.RightButton:self.cancel()
    def mouseMoveEvent(self,event):
        if self.start is not None:self.end=event.position().toPoint();self.update()
    def mouseReleaseEvent(self,event):
        if event.button()!=Qt.LeftButton or self.start is None:return
        rect=QRect(self.start,event.position().toPoint()).normalized().intersected(self.rect())
        if rect.width()<4 or rect.height()<4:self.cancel();return
        scale=self.picture.devicePixelRatio();physical=QRect(round(rect.x()*scale),round(rect.y()*scale),round(rect.width()*scale),round(rect.height()*scale))
        result=self.picture.copy(physical);self.close();self.captured.emit(result)
    def keyPressEvent(self,event):
        if event.key()==Qt.Key_Escape:self.cancel()
    def cancel(self):self.close();self.cancelled.emit()

class FocusSelector(QWidget):
    selected=Signal(object,object);cancelled=Signal()
    def __init__(self):
        super().__init__(None,Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
        self.screen=QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        self.setGeometry(self.screen.geometry());self.setAttribute(Qt.WA_TranslucentBackground)
        self.start=self.end=None;self.setCursor(Qt.CrossCursor);self.setFocusPolicy(Qt.StrongFocus)
        self.setWindowTitle('Tracer la zone de concentration · Échap pour annuler')
    def paintEvent(self,event):
        painter=QPainter(self);painter.fillRect(self.rect(),QColor(0,0,0,75))
        painter.setPen(QColor('white'));painter.drawText(self.rect().adjusted(24,24,-24,-24),Qt.AlignTop|Qt.AlignHCenter,'Tracez votre zone de concentration · Échap pour annuler')
        if self.start is not None:
            painter.setRenderHint(QPainter.Antialiasing);painter.setPen(QPen(QColor('#BDBEFF'),2));painter.drawRoundedRect(QRect(self.start,self.end).normalized(),10,10)
    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton:self.start=self.end=event.position().toPoint();self.update()
        elif event.button()==Qt.RightButton:self.cancel()
    def mouseMoveEvent(self,event):
        if self.start is not None:self.end=event.position().toPoint();self.update()
    def mouseReleaseEvent(self,event):
        if event.button()!=Qt.LeftButton or self.start is None:return
        rect=QRect(self.start,event.position().toPoint()).normalized().intersected(self.rect())
        if rect.width()<24 or rect.height()<24:self.cancel();return
        self.close();self.selected.emit(self.screen,rect)
    def keyPressEvent(self,event):
        if event.key()==Qt.Key_Escape:self.cancel()
    def cancel(self):self.close();self.cancelled.emit()

class FocusOverlay(QWidget):
    dismissed=Signal()
    def __init__(self,screen,rect,opacity=85):
        super().__init__(None,Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.WindowDoesNotAcceptFocus)
        from PySide6.QtGui import QRegion,QPainterPath
        self.setAttribute(Qt.WA_TranslucentBackground);self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setGeometry(screen.geometry());self.hole=QRect(rect);self.opacity=opacity
        path=QPainterPath();path.addRoundedRect(self.hole,10,10)
        self.setMask(QRegion(self.rect()).subtracted(QRegion(path.toFillPolygon().toPolygon())))
        self.setWindowTitle('Concentrator · clic dans le sombre ou Échap pour sortir')
        self.setCursor(Qt.PointingHandCursor)
    def paintEvent(self,event):
        painter=QPainter(self);painter.fillRect(self.rect(),QColor(0,0,0,round(255*self.opacity/100)))
    def mousePressEvent(self,event):
        if self.mask().contains(event.position().toPoint()):self.dismissed.emit();event.accept()
    def keyPressEvent(self,event):
        if event.key()==Qt.Key_Escape:self.dismissed.emit()

