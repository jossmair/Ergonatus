"""Run the actual EXE with separate model files and inspect its real local status."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time
import pywintypes
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.ipc_client import request


def main():
    root = Path(__file__).resolve().parents[1]
    executable = root / "dist" / "Redactor-0.4.1" / "Redactor.exe"
    env = dict(os.environ, REDACTOR_DATA_DIR=str(root / ".test-data" / "packaged-smoke"), REDACTOR_TEST_INSTANCE="qa-package")
    process = subprocess.Popen([str(executable), "--minimized"], env=env)
    started = time.perf_counter()
    report = {}
    try:
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise AssertionError(f"L’exécutable s’est arrêté : {process.returncode}")
            try:
                status = request(process.pid)
                if status["payload"].get("state") == "ready":
                    report = {"packaged_exe": str(executable), "ready": True,
                              "startup_to_ready_seconds": time.perf_counter() - started,
                              "separate_gguf": True, "pid": process.pid}
                    break
                if status["payload"].get("state") == "error":
                    raise AssertionError("L’exécutable signale une erreur du moteur.")
            except (OSError, pywintypes.error):
                pass
            time.sleep(.15)
        assert report, "Le paquet n’est pas devenu prêt dans le budget de test."
        response = request(process.pid, "correct", "Les réunion sont terminé.")
        assert response["payload"].get("localValidationRequired") is True
        report["draft_requires_local_validation"] = True
        try:
            request(process.pid, "insert", "INTERDIT")
            raise AssertionError("Insertion distante acceptée")
        except ValueError:
            report["external_insert_absent"] = True
    finally:
        # Only the disposable process created above is terminated. Interactive
        # graceful worker shutdown is tested separately by verify_engine.py.
        if process.poll() is None:
            process.terminate()
            process.wait(5)
    report["test_process_released"] = True
    (root / "docs" / "validation" / "package.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
