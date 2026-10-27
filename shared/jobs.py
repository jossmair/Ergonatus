"""Workers with GUI-thread result delivery. No GUI objects in workers."""
from PySide6.QtCore import QObject,Signal,QRunnable,QThreadPool

class Signals(QObject):
    done=Signal(object)
    error=Signal(str)
    finished=Signal()

class Job(QRunnable):
    def __init__(self,function):
        super().__init__();self.function=function;self.signals=Signals()
    def run(self):
        try:self.signals.done.emit(self.function())
        except Exception as error:self.signals.error.emit(str(error))
        finally:self.signals.finished.emit()

def background(owner,function,done):
    job=Job(function)
    owner.pending.add(job)
    job.signals.done.connect(done)
    job.signals.error.connect(owner.error)
    job.signals.finished.connect(lambda:owner.pending.discard(job))
    QThreadPool.globalInstance().start(job)
    return job
