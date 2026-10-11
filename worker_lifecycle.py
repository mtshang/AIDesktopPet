"""Keep background jobs alive and let the UI drain them before exiting."""
from PySide6.QtCore import QObject, QCoreApplication, Signal, Slot


class WorkerRegistry(QObject):
    drained = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.workers = set()
        self.closing = False

    def start(self, worker):
        if self.closing or worker.isRunning():
            return False
        if not getattr(worker, "_registry_connected", False):
            worker.finished.connect(self._finished)
            worker._registry_connected = True
        self.workers.add(worker)
        worker.start()
        return True

    @Slot()
    def _finished(self):
        worker = self.sender()
        if worker is not None:
            worker.wait()
            self.workers.discard(worker)
        if self.closing and not self.workers:
            self.drained.emit()

    def begin_shutdown(self):
        self.closing = True
        if not self.workers:
            self.drained.emit()


_registry = None


def worker_registry():
    global _registry
    if _registry is None:
        _registry = WorkerRegistry(QCoreApplication.instance())
    return _registry


def start_worker(worker):
    return worker_registry().start(worker)


def is_shutting_down():
    return _registry is not None and _registry.closing
