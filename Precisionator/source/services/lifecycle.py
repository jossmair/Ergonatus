"""Single instance and read-only power/session lifecycle notifications."""
import ctypes as C
from ctypes import wintypes as W

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, QTimer, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

NAME = "Precisionator.SingleInstance.v1"


class SingleInstance:
    def __init__(self):
        self.kernel = C.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateMutexW.argtypes = [C.c_void_p, W.BOOL, W.LPCWSTR]
        self.kernel.CreateMutexW.restype = W.HANDLE
        self.kernel.CloseHandle.argtypes = [W.HANDLE]
        self.handle = None

    def acquire(self):
        C.set_last_error(0)
        handle = self.kernel.CreateMutexW(None, False, "Local\\" + NAME)
        if not handle:
            raise C.WinError(C.get_last_error())
        if C.get_last_error() == 183:
            self.kernel.CloseHandle(handle)
            return False
        self.handle = handle
        return True

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


class InstanceServer(QObject):
    def __init__(self, opened):
        super().__init__()
        self.opened = opened
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.UserAccessOption)
        self.server.newConnection.connect(self.receive)
        QLocalServer.removeServer(NAME)
        if not self.server.listen(NAME):
            raise OSError(self.server.errorString())

    def receive(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            socket.disconnectFromServer()
            socket.deleteLater()
            self.opened()

    @staticmethod
    def notify():
        socket = QLocalSocket()
        socket.connectToServer(NAME)
        socket.waitForConnected(800)
        socket.disconnectFromServer()


class Lifecycle(QAbstractNativeEventFilter):
    def __init__(self, hwnd, suspended, resumed, changed):
        super().__init__()
        self.hwnd = hwnd
        self.suspended, self.resumed, self.changed = suspended, resumed, changed
        self.wts = C.WinDLL("wtsapi32", use_last_error=True)
        self.wts.WTSRegisterSessionNotification.argtypes = [W.HWND, W.DWORD]
        self.wts.WTSUnRegisterSessionNotification.argtypes = [W.HWND]
        if not self.wts.WTSRegisterSessionNotification(hwnd, 0):
            raise C.WinError(C.get_last_error())

    def nativeEventFilter(self, event_type, message):
        msg = W.MSG.from_address(int(message))
        if msg.message == 0x218:  # WM_POWERBROADCAST
            if msg.wParam == 4:
                self.suspended()
            elif msg.wParam in (7, 18):
                QTimer.singleShot(500, self.resumed)
        elif msg.message == 0x2B1:  # WM_WTSSESSION_CHANGE
            if msg.wParam in (2, 4, 6, 7):
                self.suspended()
            elif msg.wParam in (1, 3, 5, 8):
                QTimer.singleShot(500, self.resumed)
        elif msg.message == 0x7E:  # WM_DISPLAYCHANGE; per-window DPI is not hotplug.
            self.changed()
        return False, 0

    def close(self):
        self.wts.WTSUnRegisterSessionNotification(self.hwnd)
