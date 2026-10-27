import os
from pathlib import Path
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest


@pytest.fixture(scope="session")
def app():
    from PySide6.QtWidgets import QApplication
    from ui.theme import configure_app
    result = QApplication.instance() or QApplication([])
    configure_app(result)
    return result
