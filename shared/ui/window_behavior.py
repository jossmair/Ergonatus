"""Window-only ergonomics. Never intercepts keys outside the owning window."""
import json
from pathlib import Path
from PySide6.QtCore import QObject,QEvent,QPoint,QRect,Qt,QTimer,Signal
from PySide6.QtGui import QGuiApplication,QKeySequence,QShortcut
from PySide6.QtWidgets import QApplication,QMenu,QMessageBox

def fit_window(rect,areas):
    if not areas:return QRect(rect)
    area=max(areas,key=lambda item:rect.intersected(item).width()*rect.intersected(item).height())
    width=min(rect.width(),area.width());height=min(rect.height(),area.height())
    return QRect(max(area.left(),min(rect.x(),area.right()-width+1)),max(area.top(),min(rect.y(),area.bottom()-height+1)),width,height)

class WindowBehavior(QObject):
    message=Signal(str)
    def __init__(self,window):
        super().__init__(window);self.window=window;self.areas=set();self.drag=None;self.keyboard_origin=None
        self.path=None;self.ready=False;self.restoring=False;self.native_drag=False;self.minimum=None
        self.save_timer=QTimer(self);self.save_timer.setSingleShot(True);self.save_timer.setInterval(300);self.save_timer.timeout.connect(self.save)
        window.installEventFilter(self);QApplication.instance().installEventFilter(self)
        self.shortcuts=[]
        for key,callback in [('Alt+F7',self.begin_keyboard_move),('Alt+Space',self.window_menu),('F1',self.help)]:
            shortcut=QShortcut(QKeySequence(key),window);shortcut.activated.connect(callback);self.shortcuts.append(shortcut)
        QGuiApplication.instance().screenRemoved.connect(self.ensure_visible)
        QGuiApplication.instance().screenAdded.connect(self.ensure_visible)

    def detach(self):
        app=QApplication.instance()
        if app:app.removeEventFilter(self)

    def add_drag_area(self,widget):
        self.areas.add(widget);widget.installEventFilter(self);widget.setCursor(Qt.ArrowCursor)
        widget.setToolTip('Glisser pour déplacer · Alt+F7 pour déplacer au clavier · Alt+Espace pour le menu')

    def configure(self,path):
        self.path=Path(path);QTimer.singleShot(0,self.restore)

    def restore(self):
        self.minimum=self.window.minimumSize();self.restoring=True
        try:
            data=json.loads(self.path.read_text(encoding='utf-8')) if self.path and self.path.is_file() and self.path.stat().st_size<2048 else None
            values=data.get('geometry') if isinstance(data,dict) and data.get('version')==1 else None
            if not isinstance(values,list) or len(values)!=4 or any(type(value) is not int or abs(value)>100000 for value in values) or not 100<=values[2]<=10000 or not 100<=values[3]<=10000:values=None
        except (OSError,ValueError,AttributeError):values=None
        if values:self.window.setGeometry(QRect(*values))
        else:
            area=QGuiApplication.primaryScreen().availableGeometry();self.window.move(area.center()-self.window.rect().center())
        self.ensure_visible();self.restoring=False;self.ready=True

    def ensure_visible(self,*_):
        if self.window.isMaximized() or self.window.isMinimized():return
        areas=[screen.availableGeometry() for screen in QGuiApplication.screens()]
        rect=fit_window(self.window.geometry(),areas)
        if self.minimum:self.window.setMinimumSize(min(self.minimum.width(),rect.width()),min(self.minimum.height(),rect.height()))
        if rect!=self.window.geometry():self.window.setGeometry(rect)

    def center(self):
        area=(self.window.screen() or QGuiApplication.primaryScreen()).availableGeometry()
        self.window.move(area.center()-self.window.rect().center());self.ensure_visible();self.save()

    def save(self):
        if not self.path or not self.ready or self.restoring:return
        rect=self.window.normalGeometry() if self.window.isMaximized() else self.window.geometry()
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True);temp=self.path.with_suffix('.tmp')
            temp.write_text(json.dumps(dict(version=1,geometry=[rect.x(),rect.y(),rect.width(),rect.height()])),encoding='utf-8');temp.replace(self.path)
        except OSError:self.message.emit('La position ne peut pas être enregistrée. Le logiciel reste utilisable.')

    def start_native_move(self):
        handle=self.window.windowHandle();return bool(handle and handle.startSystemMove())

    def begin_keyboard_move(self):
        self.keyboard_origin=self.window.pos()
        self.message.emit('Déplacer : flèches · Entrée valide · Échap annule.')

    def finish_keyboard_move(self,cancel=False):
        if self.keyboard_origin is None:return
        if cancel:self.window.move(self.keyboard_origin)
        self.keyboard_origin=None;self.ensure_visible();self.save();self.message.emit('Déplacement annulé.' if cancel else 'Fenêtre déplacée.')

    def window_menu(self):
        menu=QMenu(self.window);menu.addAction('Déplacer au clavier · Alt+F7',self.begin_keyboard_move)
        menu.addAction('Recentrer la fenêtre',self.center);menu.addAction('Aide · F1',self.help);menu.addAction('Masquer la fenêtre',self.window.hide)
        menu.exec(self.window.mapToGlobal(QPoint(16,48)))

    def help(self):
        companion='Ergonatus' not in self.window.windowTitle()
        QMessageBox.information(self.window,'Utiliser '+self.window.windowTitle(),
            'Glissez la barre du haut pour déplacer la fenêtre.\n'
            'Au clavier : Alt+F7, puis les flèches. Entrée valide, Échap annule.\n'
            'Alt+Espace ouvre le menu, avec Recentrer.\n\n'
            'Tab passe à la commande suivante. Entrée ou Espace active une commande.\n'
            'Les commandes secondaires sont dans Plus d’options.\n'+
            ('Masquer ferme la fenêtre sans couper l’aide. Son Orb permet de la retrouver.\n'
            'Quitter le logiciel se trouve dans le menu de son Orb ou de son icône près de l’horloge.' if companion else
            'Les aides restent ouvertes quand vous quittez le hub.\nL’icône près de l’horloge permet de retrouver Ergonatus.'))

    def eventFilter(self,watched,event):
        if not hasattr(self,'keyboard_origin'):return False
        kind=event.type()
        if self.keyboard_origin is not None and hasattr(watched,'window') and watched.window()==self.window and kind in (QEvent.ShortcutOverride,QEvent.KeyPress):
            key=event.key()
            if key in (Qt.Key_Left,Qt.Key_Right,Qt.Key_Up,Qt.Key_Down,Qt.Key_Return,Qt.Key_Enter,Qt.Key_Escape):
                if kind==QEvent.ShortcutOverride:event.accept();return True
                if key==Qt.Key_Escape:self.finish_keyboard_move(True)
                elif key in (Qt.Key_Return,Qt.Key_Enter):self.finish_keyboard_move()
                else:
                    step=40 if event.modifiers()&Qt.ShiftModifier else 10
                    delta={Qt.Key_Left:QPoint(-step,0),Qt.Key_Right:QPoint(step,0),Qt.Key_Up:QPoint(0,-step),Qt.Key_Down:QPoint(0,step)}[key]
                    self.window.move(self.window.pos()+delta)
                return True
        if watched in self.areas:
            if kind==QEvent.MouseButtonDblClick and watched.property('doubleClickSettings') and event.button()==Qt.LeftButton:
                watched.owner.open_settings();event.accept();return True
            if kind==QEvent.MouseButtonPress and event.button()==Qt.LeftButton:
                self.finish_keyboard_move();self.drag=(event.globalPosition().toPoint(),self.window.pos());self.native_drag=self.start_native_move();return True
            if kind==QEvent.MouseMove and self.drag and event.buttons()&Qt.LeftButton:
                if not self.native_drag:self.window.move(self.drag[1]+event.globalPosition().toPoint()-self.drag[0])
                return True
            if kind==QEvent.MouseButtonRelease and event.button()==Qt.LeftButton:
                self.drag=None;self.ensure_visible();self.save();return True
        if watched==self.window:
            if kind in (QEvent.Move,QEvent.Resize) and self.ready and not self.restoring:self.save_timer.start()
            elif kind in (QEvent.Hide,QEvent.Close):self.finish_keyboard_move();self.save()
            elif kind==QEvent.WindowActivate and self.ready:self.ensure_visible()
        return super().eventFilter(watched,event)
