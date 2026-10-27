import math
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QPoint, Signal, QRect, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QLinearGradient, QPainterPath, QRegion
from PySide6.QtWidgets import (QMainWindow, QPushButton, QFrame, QDialog, QLabel, QApplication,
                             QProgressBar, QWidget, QVBoxLayout)
from shared.ui.theme import APP_THEMES
from shared.catalog import suite_root

class ErgoBackdrop(QWidget):
    """Quiet coloured ribbons, painted at native resolution for every DPI."""
    def __init__(self, app_id, parent=None):
        super().__init__(parent)
        self.accent=QColor(APP_THEMES[app_id]['accent'])
        self.wallpaper=QPixmap()
        self.setObjectName('ErgoBackdrop')

    def paintEvent(self, event):
        from shared.ui.theme import system_high_contrast
        if system_high_contrast():
            painter=QPainter(self);painter.fillRect(self.rect(),QColor('#000000'));return
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(),QColor('#F6F9FD'))
        return
        if not self.wallpaper.isNull():
            image=self.wallpaper.scaled(self.size(),Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation)
            painter.drawPixmap((self.width()-image.width())//2,(self.height()-image.height())//2,image)
            return
        painter.scale(self.width()/1060,self.height()/800)
        wash=QLinearGradient(0,0,1060,800)
        colour=QColor(self.accent);colour.setAlpha(100)
        wash.setColorAt(0,colour);wash.setColorAt(.55,QColor('#0D1519'));wash.setColorAt(1,colour)
        painter.fillRect(0,0,1060,800,wash)
        for offset in range(14):
            path=QPainterPath();path.moveTo(590+offset*14,-40)
            path.cubicTo(1120,180,500,470,1120+offset*9,840)
            tint=QColor(self.accent);tint.setAlpha(12+offset%4*3)
            painter.setPen(QPen(tint,2+offset%3));painter.drawPath(path)

class ErgoWindow(QMainWindow):
    """Common starting geometry; windows remain resizable on smaller displays."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.resize(680, 550)
        self.setMinimumSize(600, 480)
        from shared.ui.window_behavior import WindowBehavior
        self.behavior=WindowBehavior(self)

    def drag_area(self,widget):self.behavior.add_drag_area(widget)

    def start_drag(self,event):
        if event.button()==Qt.LeftButton and self.windowHandle():self.windowHandle().startSystemMove()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if getattr(self,'_clean_hub_frame',False):self.clearMask();return
        path=QPainterPath();path.addRoundedRect(QRectF(self.rect()),16,16)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

class ErgoButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName(text)

class ErgoCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('Card')

class ErgoDialog(QDialog):
    pass

class ErgoStatus(QLabel):
    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self.setAccessibleName(text)
        self.setWordWrap(True)

class ErgoTooltip(QLabel):
    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)

class ErgoProgress(QProgressBar):
    pass

class ErgoSettingsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

class ErgoOptions(QFrame):
    """Secondary actions stay reachable with one keyboard-operable button."""
    def __init__(self, parent=None, label='Plus d’options', expanded_label='Moins d’options'):
        super().__init__(parent)
        self.closed_label=label;self.expanded_label=expanded_label
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        self.toggle=ErgoButton(label);self.toggle.setCheckable(True)
        layout.addWidget(self.toggle)
        self.body=QWidget();self.content=QVBoxLayout(self.body);self.content.setContentsMargins(0,8,0,0)
        layout.addWidget(self.body);self.body.hide()
        self.toggle.toggled.connect(self.set_expanded)

    def set_expanded(self, expanded):
        self.body.setVisible(expanded)
        self.toggle.setText(self.expanded_label if expanded else self.closed_label)
        self.toggle.setAccessibleName(self.toggle.text())

class ErgoOrb(QWidget):
    """Raster orb with gentle breathing; fixed hit target and voluntary activation."""
    activated = Signal(str)
    doubleActivated = Signal(str)
    moved = Signal(str, object)
    STATES = ('Disponible', 'Activée', 'Traitement en cours', 'Action réussie', 'Attention', 'Erreur')

    def __init__(self, app_id, floating=False, parent=None, preview=True):
        super().__init__(parent)
        self.app_id = app_id
        self.theme = APP_THEMES[app_id]
        self.floating = floating
        self.preview = preview
        self.state = 'Disponible'
        self.phase = 0.
        self.press_pos = self.origin = None
        self.dragged = False
        self.setFixedSize(36, 36) if floating else self.setFixedSize(64,64)
        self.setFocusPolicy(Qt.StrongFocus if not floating else Qt.NoFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        if floating:
            self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.image = QPixmap(str(suite_root() / 'assets' / 'orbs' / f'{app_id}.png')).scaled(128,128,Qt.KeepAspectRatio,Qt.SmoothTransformation)
        self.timer = QTimer(self)
        self.timer.setInterval(120)
        self.timer.timeout.connect(self.tick)
        self.animations = True
        self.single_click=QTimer(self);self.single_click.setSingleShot(True);self.single_click.setInterval(QApplication.doubleClickInterval());self.single_click.timeout.connect(lambda:self.activated.emit(self.app_id))
        self.update_state('Disponible')

    def update_state(self, state):
        if state not in self.STATES:
            raise ValueError('État Orb inconnu.')
        self.state = state
        label = f"{self.theme['name']} · {state}" + (' · aperçu graphique' if self.floating and self.preview else '')
        self.setToolTip(label)
        self.setAccessibleName(label)
        self.update()

    def set_animations(self, enabled):
        self.animations = enabled
        if enabled and self.isVisible():
            self.timer.start()
        else:
            self.timer.stop()
            self.phase = 0
            self.update()

    def showEvent(self, event):
        super().showEvent(event)
        if self.animations:
            self.timer.start()

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def tick(self):
        self.phase += .10
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.scale(self.width()/64,self.height()/64)
        pulse = 1.5 * math.sin(self.phase) if self.animations else 0
        if not self.image.isNull():
            painter.save()
            painter.setOpacity(.95 + .05 * math.sin(self.phase) if self.animations else 1.)
            painter.drawPixmap(2, 2, 60, 60, self.image)
            painter.restore()
        else:
            # Honest vector fallback until the generated bitmap is available.
            painter.setBrush(QColor('#152127'))
            painter.setPen(QPen(QColor(self.theme['accent']), 3))
            painter.drawEllipse(8, 8, 48, 48)
            painter.setPen(QColor('#FFFFFF'))
            font = painter.font(); font.setPointSize(20); painter.setFont(font)
            painter.drawText(QRect(0,0,64,64), Qt.AlignCenter, self.theme['icon'])
        painter.setPen(QPen(QColor(self.theme['accent']), 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPoint(32, 32), 28 + pulse, 28 + pulse)
        if self.state in ('Attention', 'Erreur', 'Action réussie', 'Traitement en cours'):
            painter.setBrush(QColor('#152127'))
            painter.drawEllipse(43, 42, 20, 20)
            painter.setPen(QColor('#FFFFFF'))
            font = painter.font(); font.setPointSize(11); painter.setFont(font)
            marker = {'Attention':'!', 'Erreur':'×', 'Action réussie':'✓', 'Traitement en cours':'…'}[self.state]
            painter.drawText(43, 42, 20, 20, Qt.AlignCenter, marker)
        if self.hasFocus():
            painter.setPen(QPen(QColor('#FFFFFF'), 2)); painter.drawRoundedRect(1, 1, 62, 62, 8, 8)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.press_pos = event.globalPosition().toPoint()
            self.origin = self.pos()
            self.dragged = False

    def mouseMoveEvent(self, event):
        if self.press_pos is not None and event.buttons() & Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self.press_pos
            if delta.manhattanLength() > 8:
                self.dragged = True
                if self.floating:
                    self.move(self.origin + delta)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.press_pos is not None:
            if self.dragged and self.floating:
                self.moved.emit(self.app_id, [self.x(), self.y()])
            elif not self.dragged and self.rect().contains(event.position().toPoint()):
                if self.app_id=='lector':self.single_click.start()
                else:self.activated.emit(self.app_id)
            self.press_pos = None

    def mouseDoubleClickEvent(self,event):
        if self.app_id in ('lector','corrector','planinator','applinator','organisator','ergonatus','explicator','tablinator','temporator') and event.button()==Qt.LeftButton:
            self.single_click.stop();self.press_pos=None;self.dragged=False;self.doubleActivated.emit(self.app_id);event.accept()
        else:super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Space):
            self.activated.emit(self.app_id)
        else:
            super().keyPressEvent(event)
