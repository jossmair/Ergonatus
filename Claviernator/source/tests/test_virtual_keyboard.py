import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from dataclasses import asdict
from unittest.mock import Mock
import pytest
from PySide6.QtCore import QEvent, QMimeData, QPoint, QPointF, QRect, QSize, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from fortinatus.config import Settings
from fortinatus.controller import Controller
from fortinatus.desktop_target import DesktopTarget, EditingTarget, PasteDelivery, ScrollTarget, TargetError
from fortinatus.keyboard_layout import erase_character, unicode_character
from fortinatus.keyboard_orb import VirtualKeyboardManager, bounded_panel_position, keyboard_size, monitor_screen, orb_position, panel_position
from fortinatus.theme import configure_app
from fortinatus.virtual_keyboard import KeyCap, VirtualKeyboard

_app = None


@pytest.fixture
def app():
    global _app
    _app = QApplication.instance() or QApplication([])
    configure_app(_app)
    return _app


@pytest.fixture
def keyboard(app):
    item = VirtualKeyboard()
    yield item
    item.hide()
    item.deleteLater()
    app.processEvents()


def character_key(keyboard, base):
    return next(item for item, data in keyboard.character_buttons if data[0] == base)


def test_compose_shift_caps_altgr_and_shortcut_are_separate(keyboard):
    events = []
    keyboard.key_requested.connect(events.append)
    character_key(keyboard, "a").click()
    keyboard.shift_button.click()
    character_key(keyboard, "é").click()
    character_key(keyboard, "b").click()
    keyboard.caps_button.click()
    character_key(keyboard, "a").click()
    keyboard.shift_button.click()
    character_key(keyboard, "z").click()
    keyboard.altgr_button.click()
    character_key(keyboard, "0").click()
    assert keyboard.text == "aÉbAz@"
    assert not keyboard.shift
    keyboard.modifier_buttons[0xA2][0].click()
    character_key(keyboard, "c").click()
    assert events == [[0xA2, ord("C")]]
    assert keyboard.text == "aÉbAz@" and not keyboard.modifiers


def test_unicode_input_covers_supplementary_characters(keyboard):
    keyboard.clear_hex()
    for char in "1F600":
        keyboard.enter_hex(char)
    keyboard.commit_unicode()
    assert keyboard.text == "😀"
    keyboard.backspace()
    assert keyboard.text == ""
    assert not keyboard.insert_button.isEnabled()


@pytest.mark.parametrize("code,expected", [("20AC", "€"), ("U+00E9", "é"), ("1F600", "😀"), ("10FFFF", "\U0010ffff")])
def test_unicode_codepoints(code, expected):
    assert unicode_character(code) == expected


@pytest.mark.parametrize("code", ["", "ZZ", "110000", "D800", "DFFF", "0000", "000A", "1234567"])
def test_unicode_rejects_invalid_input(code):
    with pytest.raises(ValueError):
        unicode_character(code)


@pytest.mark.parametrize("suffix", ["é", "e\u0301", "❤️", "👍🏽", "👩‍💻", "🇫🇷", "👩🏽‍💻", "👨‍👩‍👧‍👦", "👩‍❤️‍💋‍👩"])
def test_backspace_erases_one_character_cluster(suffix):
    assert erase_character("Avant " + suffix) == "Avant "


def test_backspace_keeps_complete_flag_before_an_odd_regional_indicator():
    assert erase_character("🇫🇷🇩") == "🇫🇷"


def test_f12_is_pause_and_never_a_target_shortcut(keyboard):
    emergency, keys = [], []
    keyboard.emergency_requested.connect(lambda: emergency.append(True))
    keyboard.key_requested.connect(keys.append)
    keyboard.send_special(0x7B)
    assert emergency == [True] and not keys


def test_paste_delivered_once_restores_rich_clipboard_and_preserves_new_copy(app):
    desktop = Mock()
    desktop.sequence.return_value = 10
    delivery = PasteDelivery(desktop)
    clipboard = app.clipboard()
    saved = QMimeData()
    saved.setText("Original")
    saved.setHtml("<b>Original</b>")
    clipboard.setMimeData(saved)
    target = EditingTarget(1, 2, 3, "Document")
    assert delivery.paste(target, "é 😀\nTexte")
    desktop.send_keys.assert_called_once_with(target, [0xA2, 0x56])
    assert clipboard.text() == "é 😀\nTexte"
    with pytest.raises(TargetError):
        delivery.paste(target, "doublon")
    delivery.restore()
    assert clipboard.text() == "Original" and clipboard.mimeData().html() == "<b>Original</b>"
    delivery.paste(target, "suivant")
    clipboard.setText("Nouvelle copie")
    desktop.sequence.return_value = 11
    delivery.restore()
    assert clipboard.text() == "Nouvelle copie"


def test_refused_target_sends_nothing_and_leaves_clipboard(app):
    desktop = Mock()
    desktop.prepare.side_effect = TargetError("Zone fermée")
    app.clipboard().setText("Original")
    delivery = PasteDelivery(desktop)
    with pytest.raises(TargetError):
        delivery.paste(None, "À conserver")
    desktop.send_keys.assert_not_called()
    assert app.clipboard().text() == "Original" and not delivery.busy


def test_partial_native_shortcut_releases_only_its_own_keys():
    desktop = DesktopTarget.__new__(DesktopTarget)
    desktop.prepare = Mock()
    desktop.adapter = Mock()
    desktop.adapter.key.side_effect = lambda key, down: (key, down)
    desktop.adapter.send.side_effect = [RuntimeError("partial"), None]
    with pytest.raises(RuntimeError):
        desktop.send_keys(None, [0xA2, 0x56])
    assert desktop.adapter.send.call_args_list[1].args[0] == [(0x56, False), (0xA2, False)]


def test_busy_clipboard_never_pastes_stale_contents(app):
    desktop = Mock()
    delivery = PasteDelivery(desktop)
    clipboard = Mock()
    original = QMimeData()
    original.setText("Ancien contenu")
    clipboard.mimeData.return_value = original
    clipboard.text.return_value = "Ancien contenu"
    delivery.clipboard = clipboard
    with pytest.raises(TargetError, match="occupé"):
        delivery.paste(None, "Nouveau texte")
    desktop.send_keys.assert_not_called()
    clipboard.setMimeData.assert_not_called()
    assert not delivery.busy


def test_manager_refresh_persists_option_and_keeps_draft_on_failure(app, tmp_path):
    controller = Controller(Settings(), tmp_path / "settings.json", no_hooks=True)
    desktop = Mock()
    target = EditingTarget(1, 2, 3, "Document")
    desktop.capture.return_value = target
    manager = VirtualKeyboardManager(controller, desktop=desktop)
    manager.capture_target()
    manager.toggle()
    assert manager.panel.isVisible() and manager.target == target
    manager.panel.append_text("Mon brouillon")
    desktop.prepare.side_effect = TargetError("Zone fermée")
    manager.insert(manager.panel.text)
    assert manager.panel.text == "Mon brouillon"
    assert "Zone fermée" in manager.panel.error.text()
    controller.settings.virtual_keyboard = False
    assert controller.commit()
    assert not manager.orb.isVisible() and not manager.panel.isVisible()
    assert not Settings.load(controller.path).virtual_keyboard
    assert manager.panel.text == "Mon brouillon"
    manager.stop()


def test_legacy_config_loads_keyboard_option_and_boolean_is_validated():
    data = asdict(Settings())
    del data["virtual_keyboard"]
    assert Settings.from_dict(data).virtual_keyboard
    data["virtual_keyboard"] = "oui"
    with pytest.raises(ValueError):
        Settings.from_dict(data)


def test_orb_follows_companion_without_overlap_and_clamps_multimonitor():
    area = QRect(-1920, 0, 1920, 1040)
    companion = QRect(-70, 950, 36, 36)
    point = orb_position(area, QSize(48, 48), companion=companion)
    orb = QRect(point, QSize(48, 48))
    assert area.contains(orb)
    assert orb.bottom() < companion.top() - 9
    assert abs(orb.center().x() - companion.center().x()) <= 1
    panel = QRect(panel_position(area, QSize(820, 510), orb), QSize(820, 510))
    assert area.contains(panel)


@pytest.mark.parametrize("area", [QRect(-1920, 0, 1920, 1040), QRect(1920, 0, 1536, 824), QRect(0, -1080, 1920, 1040)])
def test_orb_follows_pointer_monitor_even_if_companion_is_on_previous_screen(app, monkeypatch, area):
    from types import SimpleNamespace
    import fortinatus.keyboard_orb as module
    screen, previous = Mock(), Mock()
    screen.availableGeometry.return_value = area
    manager = VirtualKeyboardManager.__new__(VirtualKeyboardManager)
    manager.stopped = False
    manager.orb = Mock(down=False)
    manager.orb.isVisible.return_value = False
    manager.orb.size.return_value = QSize(36, 36)
    manager.orb.geometry.return_value = QRect(area.topLeft(), QSize(36, 36))
    monkeypatch.setattr(module, "QGuiApplication", SimpleNamespace(screenAt=lambda point: screen,
                                                                primaryScreen=lambda: previous))
    monkeypatch.setattr(module, "transcrinator_anchor", lambda preferred: (previous, QRect(1800, 950, 36, 36)))
    manager.place()
    position = manager.orb.move.call_args.args[0]
    assert position == orb_position(area)
    assert area.contains(QRect(position, QSize(36, 36)))
    manager.orb.down = True
    manager.orb.move.reset_mock()
    manager.place()
    manager.orb.move.assert_not_called()
    manager.orb.down = False
    manager.orb.isVisible.return_value = True
    manager.orb.underMouse.return_value = True
    manager.orb.geometry.return_value = QRect(position, QSize(36, 36))
    manager.place()
    manager.orb.move.assert_not_called()


@pytest.mark.parametrize("position", [QPoint(-9999, -9999), QPoint(9999, 9999), QPoint(-1500, 200)])
def test_dragged_panel_is_kept_accessible_inside_monitor(position):
    area, size = QRect(-1920, 0, 1920, 1040), QSize(820, 510)
    bounded = bounded_panel_position(area, size, position)
    assert area.adjusted(8, 8, -8, -8).contains(QRect(bounded, size))


def test_companion_monitor_matches_friendly_qt_name_at_mixed_dpi():
    primary, second = Mock(), Mock()
    primary.name.return_value = r"\\.\DISPLAY1"
    primary.geometry.return_value = QRect(0, 0, 1280, 720)
    second.name.return_value = "VC279"
    second.geometry.return_value = QRect(1920, 0, 1920, 1080)
    assert monitor_screen([primary, second], r"\\.\DISPLAY2", QPoint(1920, 0)) == second
    assert monitor_screen([primary, second], r"\\.\DISPLAY9", QPoint(0, -1000)) is None


def test_header_drag_moves_keyboard_without_activating_or_changing_draft(keyboard, app):
    keyboard.move(200, 200)
    keyboard.append_text("À insérer")
    keyboard.set_target(EditingTarget(1, 2, 3, "Mon document"))
    keyboard.show()
    app.processEvents()
    start = keyboard.pos()
    local = QPointF(70, 16)
    origin = QPointF(keyboard.handle.mapToGlobal(local.toPoint()))
    moved = []
    keyboard.moved.connect(lambda: moved.append(keyboard.pos()))
    def send(kind, point, global_point, button, buttons):
        event = QMouseEvent(kind, point, global_point, button, buttons, Qt.NoModifier)
        app.sendEvent(keyboard.handle, event)
    send(QEvent.MouseButtonPress, local, origin, Qt.LeftButton, Qt.LeftButton)
    send(QEvent.MouseMove, local + QPointF(2, 1), origin + QPointF(2, 1), Qt.NoButton, Qt.LeftButton)
    assert keyboard.pos() == start
    delta = QPoint(110, -70)
    send(QEvent.MouseMove, local + QPointF(delta), origin + QPointF(delta), Qt.NoButton, Qt.LeftButton)
    send(QEvent.MouseButtonRelease, local, origin + QPointF(delta), Qt.LeftButton, Qt.NoButton)
    assert keyboard.pos() == start + delta and moved == [start + delta]
    assert keyboard.text == "À insérer" and keyboard.destination.text() == "Vers : Mon document"
    assert keyboard.windowFlags() & Qt.WindowDoesNotAcceptFocus
    assert keyboard.testAttribute(Qt.WA_ShowWithoutActivating)
    assert keyboard.handle.focusPolicy() == Qt.NoFocus


def test_reopening_keyboard_restores_manual_position_on_same_screen(app, tmp_path):
    controller = Controller(Settings(), tmp_path / "settings.json", no_hooks=True)
    desktop = Mock()
    desktop.capture.return_value = EditingTarget(1, 2, 3, "Mon document")
    manager = VirtualKeyboardManager(controller, desktop=desktop)
    try:
        manager.toggle()
        manager.panel.move(50, 60)
        manager.remember_panel_position()
        position = manager.panel.pos()
        manager.panel.hide_keyboard()
        manager.toggle()
        assert manager.panel.pos() == position
        assert manager.orb.size() == QSize(36, 36)
    finally:
        manager.stop()


@pytest.mark.parametrize("new_target", [EditingTarget(1, 5, 3, "Document"), EditingTarget(8, 9, 10, "Autre application")])
def test_open_keyboard_follows_new_field_without_losing_composed_text(app, tmp_path, new_target):
    desktop = Mock()
    desktop.capture.return_value = EditingTarget(1, 2, 3, "Document")
    manager = VirtualKeyboardManager(Controller(Settings(), tmp_path / "settings.json", no_hooks=True), desktop=desktop)
    try:
        manager.toggle()
        manager.panel.append_text("Mon texte")
        desktop.capture.return_value = new_target
        manager.track_target()
        assert manager.target == manager.last_target == new_target
        assert manager.panel.text == "Mon texte"
        assert manager.panel.destination.text() == "Vers : " + new_target.title
        desktop.capture.return_value = None
        manager.track_target()
        assert manager.target == new_target  # Clicking our tool does not discard it.
    finally:
        manager.stop()


def test_insert_and_shortcuts_refresh_field_even_before_poll_timer(app, tmp_path):
    desktop = Mock()
    desktop.capture.return_value = EditingTarget(1, 2, 3, "Document")
    manager = VirtualKeyboardManager(Controller(Settings(), tmp_path / "settings.json", no_hooks=True), desktop=desktop)
    try:
        manager.toggle()
        manager.panel.append_text("Ici")
        new_target = EditingTarget(1, 5, 3, "Document")
        desktop.capture.return_value = new_target
        delivery = Mock()
        delivery.paste.return_value = True
        manager.delivery = delivery
        manager.insert("Ici")
        delivery.paste.assert_called_once_with(new_target, "Ici")
        assert manager.panel.text == ""
        third = EditingTarget(8, 9, 10, "Autre application")
        desktop.capture.return_value = third
        manager.send_keys([0xA2, 65])
        desktop.send_keys.assert_called_once_with(third, [0xA2, 65])
    finally:
        manager.stop()


def test_closing_document_does_not_redirect_paste_to_app_underneath(app, tmp_path):
    desktop = Mock()
    old = EditingTarget(1, 2, 3, "Document")
    desktop.capture.return_value = old
    manager = VirtualKeyboardManager(Controller(Settings(), tmp_path / "settings.json", no_hooks=True), desktop=desktop)
    try:
        manager.toggle()
        manager.panel.append_text("À conserver")
        desktop.target_exists.return_value = False
        desktop.pointer_over.return_value = False
        new_target = EditingTarget(8, 9, 10, "Fenêtre derrière")
        desktop.capture.return_value = new_target
        desktop.prepare.side_effect = TargetError("Document fermé")
        manager.insert(manager.panel.text)
        assert manager.target == old and manager.panel.text == "À conserver"
        desktop.send_keys.assert_not_called()
        desktop.pointer_over.return_value = True
        manager.track_target()
        assert manager.target == new_target  # A new explicit choice is accepted.
    finally:
        manager.stop()


@pytest.mark.parametrize("area", [QRect(0, 0, 3840, 2160), QRect(1920, 0, 1920, 1080), QRect(0, 0, 1280, 720)])
def test_keyboard_stays_compact_on_large_and_scaled_monitors(area):
    assert keyboard_size(area) == QSize(900, 320)


def test_rows_remain_grouped_when_a_monitor_change_requests_a_large_window(keyboard, app):
    keyboard.show()
    keyboard.resize(1000, 760)
    app.processEvents()
    assert keyboard.width() <= 900 and keyboard.height() <= 320
    number = character_key(keyboard, "1")
    letter = character_key(keyboard, "a")
    assert 40 <= letter.y() - number.y() <= 50


@pytest.fixture
def picker(app, tmp_path):
    desktop = Mock()
    desktop.capture.return_value = EditingTarget(1, 2, 3, "Premier champ")
    desktop.mouse_buttons_held.return_value = False
    desktop.target_exists.return_value = True
    manager = VirtualKeyboardManager(Controller(Settings(), tmp_path / "settings.json", no_hooks=True), desktop=desktop)
    manager.toggle()
    manager.panel.append_text("À insérer ✓")
    yield manager, desktop
    manager.stop()


@pytest.mark.parametrize("arrows", [True, False])
def test_choose_field_hides_keyboard_and_only_a_click_returns_with_draft(picker, arrows):
    manager, desktop = picker
    manager.controller.settings.hover_scroll = arrows
    manager.panel.pick_button.click()
    assert manager.choosing_target and not manager.panel.isVisible()
    next_target = EditingTarget(8, 9, 10, "Nouveau champ")
    desktop.capture.return_value = next_target
    manager.track_target()
    manager.finish_target_pick()
    assert not manager.panel.isVisible()  # Focus/pointer changes alone do not finish picking.
    manager.remember_scroll_target(ScrollTarget(8, 9, 10, 100, 100))
    manager.finish_target_pick()
    assert manager.panel.isVisible() and not manager.choosing_target
    assert manager.target == next_target and manager.panel.text == "À insérer ✓"
    desktop.send_keys.assert_not_called()  # Selection never inserts anything automatically.


def test_choose_field_waits_for_click_release_or_drag_selection_to_finish(picker):
    manager, desktop = picker
    manager.begin_target_pick()
    manager.remember_scroll_target(ScrollTarget(1, 2, 3, 100, 100))
    desktop.mouse_buttons_held.return_value = True
    manager.finish_target_pick()
    assert not manager.panel.isVisible() and manager.pick_timer.isActive()
    desktop.mouse_buttons_held.return_value = False
    manager.finish_target_pick()
    assert manager.panel.isVisible() and manager.panel.text == "À insérer ✓"


@pytest.mark.parametrize("target", [None, EditingTarget(88, 9, 10, "Autre fenêtre"),
                                     EditingTarget(1, 9, 44, "Fenêtre réutilisée")])
def test_unrelated_or_closed_pick_target_never_returns_or_inserts(picker, target):
    manager, desktop = picker
    manager.begin_target_pick()
    manager.remember_scroll_target(ScrollTarget(1, 2, 3, 100, 100))
    desktop.capture.return_value = target
    manager.finish_target_pick()
    assert not manager.panel.isVisible() and manager.choosing_target
    assert manager.panel.text == "À insérer ✓"
    desktop.send_keys.assert_not_called()


def test_orb_cancels_pending_pick_and_restores_draft_without_late_reopening(picker):
    manager, desktop = picker
    manager.begin_target_pick()
    manager.remember_scroll_target(ScrollTarget(1, 2, 3, 100, 100))
    manager.toggle()
    assert manager.panel.isVisible() and not manager.choosing_target and not manager.pick_timer.isActive()
    assert manager.panel.text == "À insérer ✓"
    manager.panel.hide_keyboard()
    manager.finish_target_pick()
    manager.remember_scroll_target(ScrollTarget(1, 2, 3, 100, 100))
    assert not manager.panel.isVisible() and not manager.pick_timer.isActive()


def test_disabling_virtual_keyboard_cancels_pick_without_late_reappearance(picker):
    manager, desktop = picker
    manager.begin_target_pick()
    manager.remember_scroll_target(ScrollTarget(1, 2, 3, 100, 100))
    manager.controller.settings.virtual_keyboard = False
    manager.refresh()
    manager.finish_target_pick()
    assert not manager.choosing_target and not manager.pick_timer.isActive()
    assert not manager.panel.isVisible() and not manager.orb.isVisible()
    assert manager.panel.text == "À insérer ✓"


def test_erase_is_available_on_every_page_and_never_empties_prepared_text(keyboard, app):
    keys = []
    keyboard.key_requested.connect(keys.append)
    keyboard.set_target(EditingTarget(1, 2, 3, "Champ sélectionné"))
    keyboard.append_text("Texte à conserver")
    keyboard.show()
    for page in range(3):
        keyboard.stack.setCurrentIndex(page)
        app.processEvents()
        assert keyboard.erase_button.isVisible() and keyboard.erase_button.isEnabled()
        keyboard.toggle_modifier(0xA2, True)
        keyboard.erase_button.click()
        assert keyboard.text == "Texte à conserver" and not keyboard.modifiers
    assert keys == [[8], [8], [8]]  # Never send Ctrl+Backspace (whole word).
    keyboard.clear_text()
    assert keyboard.erase_button.isEnabled()  # The target can be edited with no draft.
    keyboard.set_target(None)
    assert not keyboard.erase_button.isEnabled()


def test_erase_uses_newly_selected_field_even_before_poll_and_preserves_draft(picker):
    manager, desktop = picker
    new_target = EditingTarget(8, 9, 10, "Nouveau champ")
    desktop.capture.return_value = new_target
    manager.panel.erase_button.click()
    desktop.send_keys.assert_called_once_with(new_target, [8])
    assert manager.panel.text == "À insérer ✓"


def test_keyboard_background_is_translucent_but_keys_remain_readable(keyboard, app):
    keyboard.show()
    app.processEvents()
    image = keyboard.grab().toImage()
    # Empty space under the keys must reveal the desktop, unlike opaque wallpaper.
    alpha = image.pixelColor(image.width() // 2, int(315 * image.devicePixelRatio())).alpha()
    assert 180 <= alpha <= 215
    key = character_key(keyboard, "a")
    point = key.mapTo(keyboard, key.rect().center()) * image.devicePixelRatio()
    assert image.pixelColor(point).alpha() >= 250


def test_page_tabs_and_actions_stay_beside_every_keyboard_page(keyboard, app):
    keyboard.show()
    for page in range(3):
        keyboard.stack.setCurrentIndex(page)
        app.processEvents()
        central = keyboard.stack.geometry()
        for button in keyboard.tabs.buttons():
            assert button.mapTo(keyboard, button.rect().topRight()).x() < central.left()
        for button in (keyboard.erase_button, keyboard.pick_button, keyboard.insert_button):
            assert button.isVisible()
            assert button.mapTo(keyboard, button.rect().topLeft()).x() > central.right()
            assert keyboard.rect().contains(button.mapTo(keyboard, button.rect().bottomRight()))
