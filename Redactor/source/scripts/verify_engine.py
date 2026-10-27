"""Real GGUF cancellation, recovery and responsive Qt event-loop checks."""
from pathlib import Path
import os
import sys
import threading
import time
import json
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ai.engine import LlamaEngine
from app.ai.prompts import Request


def main():
    root = Path(__file__).resolve().parents[1]
    engine = LlamaEngine()
    engine.load(root / "models" / "LFM2-700M-Q4_K_M.gguf")
    assert engine._abort_callback is not None
    timer = threading.Timer(.05, engine.cancel)
    started = time.perf_counter()
    timer.start()
    try:
        list(engine.stream(Request("expand", "Une association prépare une réunion. " * 12), 256))
    finally:
        timer.join()
    assert engine.metrics.finish_reason == "cancelled"
    elapsed = time.perf_counter() - started
    engine.stop.clear()
    recovered = "".join(engine.stream(Request("correct", "Les réunion sont terminé."), 64))
    assert recovered.strip()
    engine.close()
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["REDACTOR_DATA_DIR"] = str(root / ".test-data" / "engine-qt")
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    from app.controller import Controller
    from app import theme
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    theme.configure_app(app)
    controller = Controller(app)
    counters = {"during_generation": 0, "pieces": 0, "completed": False, "started": False, "error": ""}
    heartbeat = QTimer()
    heartbeat.setInterval(20)
    heartbeat.timeout.connect(lambda: counters.__setitem__("during_generation", counters["during_generation"] + 1) if controller.window.busy else None)
    heartbeat.start()
    def ready(_):
        controller.window.select_action("correct")
        controller.window.editor.setPlainText("Bonjours Madame Dupont, je vous envoi les document demain.")
        controller.generate()
    def piece(_): counters["pieces"] += 1
    def complete(_):
        counters["completed"] = True
    def poll():
        if counters["completed"] or counters["error"]:
            startup.stop()
            if counters["completed"]:
                controller.window.grab().save(str(root / "docs" / "validation" / "redactor-live-chat.png"))
            controller.quit()
        elif controller.window.engine_ready and not counters["started"]:
            counters["started"] = True
            ready(None)
    startup = QTimer()
    startup.setInterval(50)
    startup.timeout.connect(poll)
    startup.start()
    controller.engine_worker.piece.connect(piece)
    controller.engine_worker.finished.connect(complete)
    controller.engine_worker.failed.connect(lambda error: counters.__setitem__("error", error))
    QTimer.singleShot(45000, controller.quit)
    app.exec()
    assert counters["completed"] and counters["during_generation"] > 1 and counters["pieces"] > 0, counters
    assert not controller.engine_thread.isRunning() and not controller.windows_thread.isRunning()
    report = {"native_abort_callback": True, "cancel_seconds_including_50ms_trigger": elapsed,
              "recovery_generation": recovered, "qt": counters, "workers_released": True}
    (root / "docs" / "validation" / "engine-integration.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()
