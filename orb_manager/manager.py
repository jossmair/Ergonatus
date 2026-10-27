import hashlib
import json
import os
from PySide6.QtCore import QObject, QTimer, Signal, QPoint
from PySide6.QtNetwork import QLocalServer
from PySide6.QtWidgets import QApplication
from shared.ui.theme import APP_THEMES
from shared.ui.components import ErgoOrb

def clamp_position(pos, area, size=36):
    return [max(area.left(), min(pos[0], area.right() - size + 1)),
            max(area.top(), min(pos[1], area.bottom() - size + 1))]

def stack_positions(area, count, size=36, gap=10):
    rows = max(1, (area.height() - 24) // (size + gap))
    return [clamp_position([area.right()-size-12-(i//rows)*(size+gap),
                            area.bottom()-size-12-(i%rows)*(size+gap)], area, size) for i in range(count)]

def selected_stack(area,order,size=36,gap=10):
    """A vertical pile; reserve Claviernator's existing scroll arrows."""
    positions=[];x=area.right()-size-16;y=area.bottom()-size-16;previous_reserve=0
    for index,key in enumerate(order):
        reserve=18 if key=='claviernator' else 0
        if index:y-=size+gap+previous_reserve+reserve
        else:y-=reserve
        if y<area.top()+reserve+8:x-=size+gap+18;y=area.bottom()-size-16-reserve
        positions.append(clamp_position([x,y],area,size));previous_reserve=reserve
    return positions

class OrbManager(QObject):
    changed = Signal()
    show_requested = Signal()
    STATES = ErgoOrb.STATES

    def __init__(self, catalog, parent=None):
        super().__init__(parent)
        self.catalog = catalog
        self.windows = {}
        self.preview = {}
        self.states = {}
        self.sockets = set()
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.UserAccessOption)
        identity = os.environ.get('USERNAME','local') + os.environ.get('USERDOMAIN','')
        self.server_name = 'Ergonatus.Orbs.v1.' + hashlib.sha256(identity.encode()).hexdigest()[:16]
        # Do not remove a live server. A second hub exits in its entry point.
        self.listening = self.server.listen(self.server_name)
        self.server.newConnection.connect(self.accept)

    def accept(self):
        socket = self.server.nextPendingConnection()
        if socket is None:
            return
        self.sockets.add(socket)
        buffer = bytearray()
        def read():
            buffer.extend(bytes(socket.readAll()))
            if len(buffer) > 4096:
                socket.abort(); return
            if b'\n' not in buffer:
                return
            try:
                request = json.loads(bytes(buffer).decode('utf-8'))
                if request == {'version':1,'command':'show'}:
                    self.show_requested.emit()
                    socket.write(b'{"ok":true}\n'); socket.flush(); socket.disconnectFromServer()
                    return
                if set(request) != {'version','app','state'} or type(request['version']) is not int or request['version'] != 1:
                    raise ValueError()
                app_id, state = request['app'], request['state']
                if app_id not in APP_THEMES or state not in self.STATES:
                    raise ValueError()
                # State only. This endpoint cannot start a process, click, move or inject text.
                self.states[app_id] = state
                if app_id in self.preview:
                    self.preview[app_id].update_state(state)
                self.changed.emit()
                socket.write(b'{"ok":true}\n')
                socket.flush()
            except (ValueError, TypeError, KeyError, UnicodeError):
                socket.write(b'{"ok":false}\n'); socket.flush()
            socket.disconnectFromServer()
        socket.readyRead.connect(read)
        socket.disconnected.connect(lambda: (self.sockets.discard(socket), socket.deleteLater()))
        QTimer.singleShot(2000,socket,socket.abort)
        if socket.bytesAvailable():
            read()

    def native_orbs(self):
        """Observe only verified companion processes; no synthetic duplicate controls."""
        try:
            import win32gui, win32process
        except ImportError:
            return []
        owners = {p.pid: app_id for app_id in APP_THEMES for p in self.catalog.running(app_id)}
        found = []
        def collect(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            app_id = owners.get(pid)
            if not app_id:
                return
            title = win32gui.GetWindowText(hwnd).casefold()
            x,y,r,b = win32gui.GetWindowRect(hwnd)
            if ('orb' in title or 'orbe' in title) and 24 <= r-x <= 160 and 24 <= b-y <= 160:
                found.append(dict(app=app_id, hwnd=hwnd, rect=[x,y,r-x,b-y]))
        win32gui.EnumWindows(collect, None)
        return found

    def show_preview(self, app_id, profile):
        # Explicit preview for graphical validation only; never impersonates an active aide.
        if app_id in self.preview:
            self.preview[app_id].close(); del self.preview[app_id]; return
        orb = ErgoOrb(app_id, floating=True)
        orb.setToolTip(APP_THEMES[app_id]['name'] + ' · aperçu graphique · clic pour fermer')
        orb.set_animations(profile['animations'])
        area = QApplication.primaryScreen().availableGeometry()
        saved = profile['positions'].get(app_id)
        position = saved or stack_positions(area,len(self.preview)+1)[-1]
        screen = QApplication.screenAt(QPoint(*position)) or QApplication.primaryScreen()
        orb.move(*clamp_position(position, screen.availableGeometry()))
        orb.moved.connect(lambda key,pos: profile['positions'].__setitem__(key,pos))
        orb.activated.connect(lambda key: self.close_preview(key))
        self.preview[app_id] = orb
        orb.show()

    def close_preview(self, app_id):
        orb = self.preview.pop(app_id, None)
        if orb:
            orb.close()

    def set_animations(self, enabled):
        for orb in self.preview.values():
            orb.set_animations(enabled)

    def close(self):
        for key in list(self.preview):
            self.close_preview(key)
        for socket in list(self.sockets):
            socket.abort()
        self.server.close()
