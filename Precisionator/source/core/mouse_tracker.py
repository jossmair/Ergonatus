"""Read the physical pointer without observing keys or installing hooks."""
from PySide6.QtCore import QObject, QTimer, Qt, Signal
import time


class MouseTracker(QObject):
    sampled = Signal(float, int, int)
    failed = Signal(str)

    def __init__(self, desktop):
        super().__init__()
        self.desktop = desktop
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.poll)
        self.last = None
        self.changed_at = time.monotonic()

    def poll(self):
        try:
            position = self.desktop.pointer()
            now = time.monotonic()
            if position != self.last:
                self.last = position
                self.changed_at = now
            interval = 50 if now - self.changed_at > 1 else 16
            if self.timer.interval() != interval:
                self.timer.setInterval(interval)
            self.sampled.emit(now, *position)
        except OSError as error:
            self.timer.stop()
            self.failed.emit(str(error))

    def start(self):
        self.last = None
        self.changed_at = time.monotonic()
        self.timer.start(16)

    def stop(self):
        self.timer.stop()
