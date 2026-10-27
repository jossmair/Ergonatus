import hashlib
from types import SimpleNamespace

import pytest

from app.core.controller import Controller
from app.core.device_detector import Hardware
from app.core.focus_manager import FocusManager
from app.core.settings import Settings
from app.core.text import TextFormatter, TextLedger
from app.engines.base import Transcript
from app.services.model_manager import Artifact, ModelManager


def test_turnkey_preset_once_and_settings_persist(tmp_path, monkeypatch):
    bundle, profile = tmp_path / "bundle", tmp_path / "profile"
    bundle.mkdir()
    (bundle / "bundle.json").write_text('{}')
    monkeypatch.setenv("TRANSCRI_BUNDLE", str(bundle))
    monkeypatch.setenv("TRANSCRI_DATA", str(profile))
    settings = Settings(engine="parakeet", acceleration="gpu", progressive=True)
    assert settings.configure_turnkey()
    loaded = Settings.load()
    assert loaded.engine == "parakeet" and loaded.acceleration == "auto"
    assert loaded.progressive and loaded.setup_done and loaded.turnkey_configured
    loaded.acceleration = "gpu"
    assert not loaded.configure_turnkey()
    assert loaded.acceleration == "gpu"


def test_bundled_weights_verified_without_writing_application_folder(tmp_path, monkeypatch):
    bundle, profile = tmp_path / "bundle", tmp_path / "profile"
    models = bundle / "models"
    models.mkdir(parents=True)
    monkeypatch.setenv("TRANSCRI_BUNDLE", str(bundle))
    monkeypatch.setenv("TRANSCRI_DATA", str(profile))
    data = b"real integrity fixture, not an inference model"
    artifact = Artifact("model.gguf", "https://unused", len(data), hashlib.sha256(data).hexdigest(), "test")
    monkeypatch.setitem(__import__('app.services.model_manager', fromlist=['MODELS']).MODELS, "parakeet", artifact)
    path = models / artifact.name
    path.write_bytes(data)
    manager = ModelManager()
    assert manager.path("parakeet") == path
    assert not manager.installed("parakeet")
    manager.verify("parakeet")
    assert manager.installed("parakeet")
    assert manager.receipt("parakeet").is_relative_to(profile)
    assert list(models.iterdir()) == [path]
    path.write_bytes(b"corrupt")
    assert not manager.installed("parakeet")
    with pytest.raises(RuntimeError, match="corrompu"):
        manager.verify("parakeet")


def test_left_shift_never_moves_focus_or_clicks_pointer():
    focus = object.__new__(FocusManager)
    focused = object()
    focus.uia = SimpleNamespace(GetFocusedElement=lambda: focused)
    focus._safe = lambda element: False
    focus._native_target = lambda element: None
    with pytest.raises(RuntimeError, match="Aucun éditeur"):
        focus.locate()
    focus._safe = lambda element: True
    focus._capture = lambda element: element
    assert focus.locate() is focused


def test_one_final_insertion_no_text_sent_during_speech():
    controller = Controller(Settings(progressive=False), Hardware("test", 4, 16 * 2**30, 8 * 2**30))
    controller.ledger, controller.formatter = TextLedger(), TextFormatter(controller.settings)
    controller.blocked, controller.last_audio = False, 0
    sent = []
    controller.focus = SimpleNamespace(valid=lambda: True)
    controller.injector = SimpleNamespace(insert=lambda text: sent.append(text) or True)
    controller._transcript(Transcript("a", "Bonjour", True, 1))
    controller._transcript(Transcript("b", "oui oui.", True, 2))
    controller._transcript(Transcript("b", "oui oui.", True, 2))
    assert sent == []
    controller._insert_pending(force=True)
    assert sent == ["Bonjour oui oui."]
    assert controller.ledger.pending == []
    controller._insert_pending(force=True)
    assert len(sent) == 1
