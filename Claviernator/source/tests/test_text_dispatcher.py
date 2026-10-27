import threading

from fortinatus.windows import TextDispatcher, WindowsInput


class Adapter:
    text_chunks = staticmethod(WindowsInput.text_chunks)

    def __init__(self):
        self.events = []
        self.entered = threading.Event()
        self.continue_sending = threading.Event()

    def emit(self, event):
        self.events.append(event)
        self.entered.set()
        self.continue_sending.wait(1)


def test_pause_cancels_remaining_unicode_chunks_and_queued_text():
    adapter = Adapter()
    errors = []
    worker = TextDispatcher(adapter, errors.append)
    try:
        worker.submit("Bonjour 🌿 suite")
        worker.submit("texte suivant")
        assert adapter.entered.wait(1)
        worker.cancel()
        adapter.continue_sending.set()
    finally:
        worker.stop()
    assert adapter.events == [("text", "Bonjour ")]
    assert not errors


def test_send_failure_cancels_pending_text_and_reports_error():
    reported = threading.Event()
    class Failing(Adapter):
        def emit(self, event):
            raise RuntimeError("blocked")
    errors = []
    def error(text):
        errors.append(text)
        reported.set()
    worker = TextDispatcher(Failing(), error)
    try:
        worker.submit("Texte")
        assert reported.wait(1)
    finally:
        worker.stop()
    assert errors == ["blocked"]

