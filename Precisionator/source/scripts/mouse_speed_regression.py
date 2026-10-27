"""Test the real Windows API by writing back the current speed unchanged."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from main import VERSION
from services.mouse_speed import get_speed, set_speed

report = {"version": VERSION, "tests": {}, "scope": "Read and reapply current speed only; no pointer movement or input injection"}
original = None
try:
    original = get_speed()
    report["original_speed"] = original
    report["tests"]["read_windows_preference"] = 1 <= original <= 20
    set_speed(original)
    report["tests"]["idempotent_write_readback"] = get_speed() == original
except Exception as error:
    report["error"] = str(error)
finally:
    if original is not None:
        try:
            if get_speed() != original:
                set_speed(original)
            report["tests"]["original_speed_preserved"] = get_speed() == original
        except Exception as error:
            report["restore_error"] = str(error)
    report["result"] = "passed" if report["tests"] and all(report["tests"].values()) and not any(key in report for key in ("error", "restore_error")) else "failed"
    (ROOT / f"docs/validation/mouse-speed-{VERSION}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report["result"] == "passed" else 1)
