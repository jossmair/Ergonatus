import multiprocessing
import sys
from pathlib import Path

if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    # Explicit developer-only trace, never enabled in ordinary use.
    import os
    if os.environ.get("TRANSCRI_TEST_STACK"):
        import faulthandler
        trace = open(os.environ["TRANSCRI_TEST_STACK"], "w", encoding="utf-8")
        faulthandler.dump_traceback_later(12, repeat=True, file=trace)
    from app.main import main

    sys.exit(main())
