"""Local developer probe: stack traces only, no audio capture or dictation."""
import faulthandler
from pathlib import Path


if __name__ == "__main__":
    path = Path("build/shutdown-stack.txt")
    with path.open("w", encoding="utf-8") as trace:
        faulthandler.enable(file=trace)
        faulthandler.dump_traceback_later(12, file=trace)
        from app.main import main

        result = main()
        faulthandler.cancel_dump_traceback_later()
        raise SystemExit(result)
