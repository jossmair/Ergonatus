from types import SimpleNamespace
import hashlib
import os
import zipfile

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QTabWidget, QPushButton, QPlainTextEdit

from app.core.controller import Controller
from app.core.device_detector import Hardware
from app.core.settings import Settings
from app.services.engine_manager import choose_backend, runtime_file
from app.services.model_manager import Artifact, RuntimeInstaller
from app.ui.main_window import MainWindow
from app.ui.retained_action import RetainedTextAction


def test_nested_release_runtime_detection(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    binary = tmp_path / "runtimes/parakeet/cpu/release-folder/parakeet.dll"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"discovery fixture only; not executable")
    hw = Hardware("test", 4, 16 * 2**30, 8 * 2**30)
    assert runtime_file("parakeet", "cpu") == binary
    assert choose_backend("parakeet", "auto", hw) == "cpu"
    assert choose_backend("parakeet", "cpu", hw) == "cpu"
    with pytest.raises(RuntimeError, match="GPU"):
        choose_backend("parakeet", "gpu", hw)


def test_missing_runtime_identifies_engine_and_search_folder(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    hw = Hardware("test", 4, 16 * 2**30, 8 * 2**30)
    with pytest.raises(RuntimeError) as result:
        choose_backend("parakeet", "auto", hw)
    assert "Parakeet Ultra" in str(result.value)
    assert str(tmp_path / "runtimes/parakeet") in str(result.value)


def test_gpu_selection_skips_cuda_with_missing_dependencies(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    for key in os.environ:
        if key == "CUDA_PATH" or key.startswith("CUDA_PATH_V12_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("SystemRoot", str(tmp_path / "windows"))
    for backend in ("cpu", "cuda", "vulkan"):
        binary = tmp_path / "runtimes/parakeet" / backend / "parakeet.dll"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"discovery fixture only")
    hw = Hardware("test", 4, 16 * 2**30, 8 * 2**30, [{"cuda_capability": 7.5}], vulkan_loader=True)
    monkeypatch.setattr("app.services.engine_manager.run", lambda *a, **kw: SimpleNamespace(returncode=0))
    assert choose_backend("parakeet", "gpu", hw) == "vulkan"
    hw.vulkan_loader = False
    with pytest.raises(RuntimeError, match="GPU"):
        choose_backend("parakeet", "gpu", hw)
    assert choose_backend("parakeet", "auto", hw) == "cpu"


def test_cuda_companion_extracts_dlls_and_preserves_licenses(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    cache = tmp_path / "cache"
    cache.mkdir()
    archive = cache / "fixture.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("release/cudart64_12.dll", b"fixture only")
        bundle.writestr("release/LICENSE", b"NVIDIA license fixture")
    artifact = Artifact("fixture.zip", "https://unused", archive.stat().st_size,
                        hashlib.sha256(archive.read_bytes()).hexdigest(), "test")
    monkeypatch.setattr("app.services.model_manager.PARAKEET_CUDA", artifact)
    target = tmp_path / "runtime"
    target.mkdir()
    RuntimeInstaller().install_parakeet_cuda(target)
    assert (target / "cudart64_12.dll").read_bytes() == b"fixture only"
    assert (target / "cuda-notices/release/LICENSE").read_bytes() == b"NVIDIA license fixture"


def test_simple_ui_and_retained_text_recovery(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    settings = Settings()
    hardware = Hardware("test", 4, 16 * 2**30, 8 * 2**30)
    controller = Controller(settings, hardware)
    window = MainWindow(controller)
    assert window.findChildren(QComboBox) == [window.trigger_key]
    assert window.findChildren(QCheckBox) == [window.number_style, window.units, window.startup]
    assert not window.findChildren(QTabWidget)
    assert window.testAttribute(Qt.WA_TranslucentBackground)
    assert not any("Retour" in button.text() for button in window.findChildren(QPushButton))
    window.show()
    app.processEvents()
    screenshot = window.grab().toImage()
    for x, y in ((0, 0), (screenshot.width() - 1, 0),
                 (0, screenshot.height() - 1), (screenshot.width() - 1, screenshot.height() - 1)):
        assert screenshot.pixelColor(x, y).alpha() == 0
    assert screenshot.pixelColor(screenshot.width() // 2, screenshot.height() // 2).alpha() == 255
    controller.status.emit("Prêt")
    assert window.status.text() == "Prêt"
    assert not window.findChildren(QPlainTextEdit)
    assert not any("Copier" in button.text() for button in window.findChildren(QPushButton))
    recovery = RetainedTextAction(controller, window)
    assert not recovery.isEnabled()
    controller.retained_changed.emit("Bonjour, ça marche !")
    assert not window.findChildren(QPlainTextEdit)
    assert recovery.isEnabled()
    commands = []
    monkeypatch.setattr(controller, "request", commands.append)
    copied = []
    clipboard = SimpleNamespace(setText=copied.append, text=lambda: copied[-1])
    monkeypatch.setattr(QApplication, "clipboard", staticmethod(lambda: clipboard))
    recovery.trigger()
    assert copied == ["Bonjour, ça marche !"]
    assert commands == ["clear_retained"]
    controller.retained_changed.emit("")
    assert not recovery.isEnabled()
    window.hide()
    window.deleteLater()
    app.processEvents()


def test_automatic_launch_migrates_old_manual_preferences(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    settings = Settings(engine="retired", acceleration="gpu", microphone=14,
                        hotkey="double", insertion_strategy="clipboard", progressive=False,
                        hub_visible=True, hub_compact=True, experience_revision=3)
    assert settings.configure_automatic()
    assert (settings.engine, settings.acceleration, settings.microphone) == ("parakeet", "auto", None)
    assert settings.hotkey == "single" and not settings.progressive
    assert not settings.notifications
    assert settings.insertion_strategy == "auto" and settings.setup_done
    assert settings.hub_visible and not settings.hub_compact
    assert not settings.configure_automatic()
