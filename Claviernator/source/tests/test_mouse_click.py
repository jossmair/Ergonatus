import os

import pytest

from fortinatus.config import Mapping, Profile
from fortinatus.engine import Engine


@pytest.mark.parametrize("button", ["left", "right", "middle"])
def test_normal_click_stays_down_until_key_up_and_does_not_repeat(button):
    events = []
    engine = Engine(events.append)
    engine.configure(Profile(mappings=[Mapping(0x70, "mouse_click", button=button)]))
    assert engine.event(0x70, True)
    assert events == [("mouse", button, True)]
    for _ in range(5):
        assert engine.event(0x70, True)
    assert engine.event(0x70, False)
    assert events == [("mouse", button, True), ("mouse", button, False)]
    assert not engine.owners
    engine.event(0x70, True)
    assert events[-1] == ("mouse", button, True)


@pytest.mark.parametrize("button", ["left", "right", "middle"])
def test_single_click_preserves_another_keys_held_drag(button):
    events = []
    engine = Engine(events.append)
    engine.configure(Profile(mappings=[Mapping(0x70, "mouse_click", button=button),
                                       Mapping(0x71, "mouse_hold", button=button)]))
    engine.event(0x71, True)
    engine.event(0x70, True)
    engine.event(0x70, False)
    assert events == [("mouse", button, True)]
    engine.event(0x71, False)
    assert events == [("mouse", button, True), ("mouse", button, False)]


@pytest.fixture(scope="module")
def application():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from fortinatus.theme import configure_app
    app = QApplication.instance() or QApplication([])
    configure_app(app)
    yield app


@pytest.mark.parametrize("kind,button", [("mouse_click", "left"), ("mouse_click", "right"),
                                        ("mouse_hold", "left"), ("mouse_hold", "right"),
                                        ("mouse_hold", "middle"), ("mouse_toggle", "right")])
def test_explicit_click_choice_survives_edit_and_save(application, kind, button):
    from fortinatus.dialog import MappingDialog
    dialog = MappingDialog(None, mapping=Mapping(0x70, kind, button=button))
    assert dialog.stack.currentWidget() is dialog.pages[kind]
    dialog.save()
    assert dialog.mapping.kind == kind
    assert dialog.mapping.button == button
    dialog.deleteLater()
    application.processEvents()
