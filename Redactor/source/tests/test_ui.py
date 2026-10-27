import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication
from app import theme
from app.config import Config
from app.ui.main_window import MainWindow
from app.ui.orb import OrbWidget
from app.windows.suite import choose_position
from app.ui.widgets import Switch
from app.ui.settings import SettingsDialog
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication([])
    theme.configure_app(app)
    return app


def test_ui_actions_and_streaming_are_gated(app):
    window = MainWindow(Config(animation="none"))
    assert not window.generate.isEnabled()
    assert not window.copy.isEnabled()
    assert window.insert.isHidden() and window.target.isHidden()
    window.set_engine(True, "Prêt")
    assert window.generate.isEnabled()
    window.append_result("Une proposition.")
    assert window.copy.isEnabled()
    window.set_busy(True)
    assert not window.copy.isEnabled() and window.result.isReadOnly()
    window.set_busy(False)
    assert not window.result.isReadOnly()
    window.result.setPlainText("Ma modification")
    assert window.result.toPlainText() == "Ma modification"
    window.select_action("correct")
    assert not window.style.isEnabled()
    window.hide()


def test_copy_button_copies_only_latest_edited_answer(app):
    from types import SimpleNamespace
    from app.controller import Controller
    window = MainWindow(Config(animation="none"))
    window.editor.setPlainText("Message utilisateur à ne pas copier")
    window.chat_history = [("assistant", "Ancienne réponse à ne pas copier")]
    answer = "Bonjour Élodie,\nVoici ma réponse modifiée."
    window.result.setPlainText(answer)
    controller = SimpleNamespace(app=app, window=window, inserting=False)
    window.copy_requested.connect(lambda: Controller.copy(controller))
    window.copy.click()
    assert app.clipboard().text() == answer
    assert "Réponse copiée" in window.notice.text()
    window.set_busy(True)
    window.result.setPlainText("Texte encore en génération")
    window.copy.click()
    assert app.clipboard().text() == answer
    window.hide()


def test_orb_stops_timer_when_hidden_or_motion_off(app):
    orb = OrbWidget()
    orb.show()
    orb.configure("normal")
    assert orb.timer.interval() >= 34
    assert orb.timer.isActive()
    orb.configure("none")
    assert not orb.timer.isActive()
    orb.configure("reduced")
    assert orb.timer.interval() == 200
    orb.hide()
    assert not orb.timer.isActive()


def test_fourth_slot_and_removed_monitor(app):
    area = QRect(0, 0, 1920, 1080)
    companions = [("transcrinator", (1868, 1028, 36, 36)), ("claviernator", (1868, 982, 36, 36)), ("precisionator", (1868, 936, 36, 36))]
    point = choose_position(area, companions)
    assert (point.x(), point.y()) == (1868, 890)
    point = choose_position(QRect(-1280, 0, 1280, 720))
    assert -1280 <= point.x() < 0 and 0 <= point.y() <= 684


def test_top_edge_does_not_overlap_suite(app):
    point = choose_position(QRect(0, 0, 800, 600), [("precisionator", (760, 5, 36, 36))])
    assert not QRect(point.x(), point.y(), 36, 36).intersects(QRect(760, 5, 36, 36))


def test_pill_switch_mouse_and_keyboard(app):
    switch = Switch("Animation", animated=False)
    switch.show()
    QTest.mouseClick(switch, Qt.LeftButton)
    assert switch.isChecked()
    QTest.keyClick(switch, Qt.Key_Space)
    assert not switch.isChecked()
    switch.hide()


def test_simple_preferences_and_advanced_animation_sync(app):
    dialog = SettingsDialog(Config(animation="none"))
    dialog.animation.setCurrentIndex(dialog.animation.findData("normal"))
    assert dialog.motion.isChecked()
    dialog.motion.setChecked(False)
    assert dialog.animation.currentData() == "none"
    dialog.hide()


def test_chat_preserves_manual_edits_and_prior_bubbles(app):
    window = MainWindow(Config(animation="none"))
    window.editor.setPlainText("Écris un mail pour Madame Martin.")
    first = window.request()
    window.begin_turn(first)
    window.append_result("Bonjour Madame Martin.")
    window.complete_turn()
    window.set_busy(False)
    window.result.setPlainText("Bonjour Madame Martin, voici ma modification.")
    window.editor.setPlainText("Fais-le plus court.")
    second = window.request()
    assert second.history[-1] == ("assistant", "Bonjour Madame Martin, voici ma modification.")
    window.begin_turn(second)
    window.append_result("Bonjour Madame Martin !")
    window.complete_turn()
    window.set_busy(False)
    assert len(window.chat_history) == 4
    assert window.result.toPlainText() == "Bonjour Madame Martin !"
    window.reset_chat()
    assert not window.chat_history and not window.result.toPlainText()
    window.hide()


def test_chat_options_change_real_prompts(app):
    window = MainWindow(Config(animation="none"))
    window.editor.setPlainText("Demander un rendez-vous.")
    window.mail.setChecked(True)
    window.short.setChecked(True)
    window.professional.setChecked(True)
    request = window.request()
    assert request.style == "Professionnel" and not window.natural.isChecked()
    assert "mail" in request.instruction and "courte" in request.instruction
    window.select_action("correct")
    assert "mail" not in window.request().instruction
    window.hide()


def test_sms_bottom_input_enter_and_thinking(app):
    window = MainWindow(Config(animation="none"))
    assert window.width() == 460 and window.height() == 520
    assert window.chat.flow.count() == 0
    window.show()
    app.processEvents()
    assert window.chat.flow.count() == 0
    window.editor.setPlainText("Aide-moi à écrire : ")
    assert window.editor.toPlainText() == "Aide-moi à écrire : "
    sent = []
    window.generate_requested.connect(lambda: sent.append(True))
    window.set_engine(True, "Prêt")
    QTest.keyClick(window.editor, Qt.Key_Return)
    assert len(sent) == 1
    QTest.keyClick(window.editor, Qt.Key_Return, Qt.ShiftModifier)
    assert len(sent) == 1 and "\n" in window.editor.toPlainText()
    window.set_busy(True)
    assert window.chat.timer.isActive()
    window.set_busy(False)
    assert not window.chat.timer.isActive()
    assert window.mode.isHidden() and window.professional.isHidden()
    window.hide()


def test_sms_composer_stays_below_history_and_long_answer_has_no_inner_scroll(app):
    window = MainWindow(Config(animation="none"))
    window.show()
    window.editor.setPlainText("Une ligne entièrement visible.\n" * 30)
    for _ in range(4): app.processEvents()
    assert window.editor.height() < 10 * window.editor.fontMetrics().lineSpacing()
    assert window.editor.verticalScrollBar().maximum() > 0
    window.begin_turn(window.request())
    window.result.setPlainText("Une réponse longue sans défilement interne.\n" * 40)
    window.complete_turn()
    window.set_busy(False)
    for _ in range(4): app.processEvents()
    assert window.result.verticalScrollBar().maximum() == 0
    assert window.copy.isVisible()
    user_row = window.chat.flow.itemAt(0).widget()
    assistant_row = window.chat.flow.itemAt(1).widget()
    assert user_row.layout().itemAt(0).spacerItem() is not None
    assert assistant_row.layout().itemAt(0).widget() is not None
    assert assistant_row.layout().itemAt(1).spacerItem() is not None
    assert window.editor.mapTo(window.centralWidget(), window.editor.rect().topLeft()).y() > window.chat.mapTo(window.centralWidget(), window.chat.rect().topLeft()).y()
    assert window.generate.isVisible()
    initial_y = window.composer.y()
    window.editor.setPlainText("Et maintenant un deuxième message")
    window.begin_turn(window.request())
    window.append_result("Deuxième réponse")
    window.complete_turn()
    window.set_busy(False)
    for _ in range(4): app.processEvents()
    assert window.composer.y() == initial_y
    assert window.editor.hasFocus()
    for control in (window.new, window.regenerate, window.capture, window.cancel):
        assert control.isHidden()
    window.hide()


def test_autoscroll_follows_stream_after_layout_and_viewport_changes(app):
    window = MainWindow(Config(animation="none"))
    window.show()
    window.editor.setPlainText("Une réponse longue")
    window.begin_turn(window.request())
    bar = window.conversation.verticalScrollBar()
    for chunk in range(8):
        window.append_result((f"Paragraphe {chunk} : une ligne de réponse en cours.\n" * 5))
        for _ in range(6): app.processEvents()
        assert bar.value() == bar.maximum()
    assert bar.maximum() > 0
    bar.setValue(0)
    window.editor.setPlainText("Brouillon\n" * 7)
    for _ in range(6): app.processEvents()
    assert bar.value() == bar.maximum()
    window.complete_turn()
    window.set_busy(False)
    for _ in range(6): app.processEvents()
    assert bar.value() == bar.maximum()
    window.hide()
