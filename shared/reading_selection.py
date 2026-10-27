"""Voluntary text-selection mode; observes button state, never synthesises input."""
import ctypes,os
from PySide6.QtCore import QObject,QTimer,QPoint,Qt,Signal
from PySide6.QtGui import QCursor,QPainter,QColor,QPen,QPainterPath
from PySide6.QtWidgets import QWidget,QApplication

class ReadingCursor(QWidget):
    def __init__(self,kind='lector'):
        self.kind=kind
        super().__init__(None,Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.WindowTransparentForInput|Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground);self.setAttribute(Qt.WA_ShowWithoutActivating);self.setFixedSize(38,38)
        self.setWindowTitle('Corrector · sélection' if kind=='corrector' else 'Lector · curseur de lecture');self.setAccessibleName('Mode sélection pour correction' if kind=='corrector' else 'Mode sélection pour lecture')
    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing);painter.setPen(QPen(QColor('#B9EE80'),2));painter.setBrush(QColor('#172719'));painter.drawRoundedRect(2,2,32,32,10,10)
        if self.kind=='corrector':
            painter.setPen(QPen(QColor('#EAF9E0'),3));painter.drawLine(10,18,15,24);painter.drawLine(15,24,27,12);return
        path=QPainterPath();path.moveTo(9,15);path.lineTo(14,15);path.lineTo(20,10);path.lineTo(20,27);path.lineTo(14,22);path.lineTo(9,22);path.closeSubpath();painter.setBrush(QColor('#EAF9E0'));painter.drawPath(path)
        painter.setBrush(Qt.NoBrush);painter.drawArc(18,11,12,16,-65*16,130*16)

class SelectionPicker(QObject):
    selected=Signal(int);cancelled=Signal()
    def __init__(self,parent=None,kind='lector'):
        super().__init__(parent);self.cursor=ReadingCursor(kind);self.timer=QTimer(self);self.timer.setInterval(30);self.timer.timeout.connect(self.poll)
        self.armed=False;self.down=False;self.root=0;self.generation=0;self.release_point=None
    def probe(self):
        import win32gui,win32process
        point=QCursor.pos();down=bool(ctypes.windll.user32.GetAsyncKeyState(1)&0x8000);escape=bool(ctypes.windll.user32.GetAsyncKeyState(27)&0x8000)
        # Qt positions are logical pixels; native hit testing requires physical pixels.
        window=win32gui.WindowFromPoint(win32gui.GetCursorPos());root=win32gui.GetAncestor(window,2) if window else 0
        own=bool(root and win32process.GetWindowThreadProcessId(root)[1]==os.getpid())
        return point,down,escape,root,own,win32gui.GetForegroundWindow()
    def start(self):
        self.generation+=1;self.armed=True;self.down=False;self.root=0;self.release_point=None;self.cursor.show();self.timer.start();self.poll()
    def stop(self):
        self.generation+=1;self.armed=False;self.timer.stop();self.cursor.hide()
    def poll(self):
        if not self.armed:return
        point,down,escape,root,own,foreground=self.probe()
        screen=QApplication.screenAt(point) or QApplication.primaryScreen();area=screen.availableGeometry()
        self.cursor.move(min(point.x()+18,area.right()-38),min(point.y()+16,area.bottom()-38))
        if escape:self.cancelled.emit();return
        if down and not self.down:self.root=0 if own else root
        if not down and self.down and self.root and foreground==self.root:
            import win32gui
            self.release_point=win32gui.GetCursorPos()
            expected=self.root;generation=self.generation
            def ready():
                if self.armed and generation==self.generation:self.selected.emit(expected)
            QTimer.singleShot(130,ready)
        self.down=down

def read_selection(expected,point=None):
    import win32gui
    if win32gui.GetForegroundWindow()!=expected:raise ValueError('La fenêtre a changé. Sélectionnez à nouveau le texte.')
    try:
        from shared.text_target import TextTarget
        return TextTarget().capture().selected
    except ValueError:
        # Preserve the proven focused-control reader (including Firefox).
        # The broader document search is a fallback, not a replacement.
        from shared.selection_validation import read_uia_selection
        try:return read_uia_selection(expected)
        except Exception:
            from shared.uia_reading import read_document_selection
            return read_document_selection(expected,point=point)
