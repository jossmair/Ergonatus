from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QTableWidgetItem

from app.core.settings import Settings
from app.core.text_options import TextPostprocessor, normalize_vocabulary
from app.ui.preferences import ChoiceBox
from app.ui.vocabulary_dialog import VocabularyDialog
from scripts.import_vocabulary import merge_entries


def test_categories_and_display_order_survive_settings_and_imports(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    entries = [{"name": "Saint-Brieuc", "aliases": ["saint brieu"], "category": "city"},
               {"name": "maçonnerie", "aliases": [], "category": "technical"},
               {"name": "Josselin", "aliases": ["Jocelyn"]}]
    settings = Settings(vocabulary=entries)
    settings.configure_automatic()
    assert Settings.load().vocabulary == entries
    merged = merge_entries(entries, [{"name": "Saint-Brieuc", "aliases": [], "category": "product"}])
    assert merged == entries
    assert TextPostprocessor(entries).apply("Jocelyn à saint brieu") == "Josselin à Saint-Brieuc"
    malformed = [{"name": "A", "category": ["invalid"]}, {"name": "B", "category": "invalid"}]
    assert normalize_vocabulary(malformed) == [{"name": "A", "aliases": []}, {"name": "B", "aliases": []}]


def test_filtered_addition_is_first_and_saves_hidden_entries():
    app = QApplication.instance() or QApplication([])
    previous = [{"name": "Ancien", "aliases": []},
                {"name": "Produit Alpha", "aliases": [], "category": "product"}]
    dialog = VocabularyDialog(previous)
    dialog.set_filter("city")
    assert all(dialog.table.isRowHidden(row) for row in range(2))
    dialog.add_row("Saint-Brieuc", "saint brieu")
    assert dialog.table.item(0, 0).text() == "Saint-Brieuc"
    assert dialog.table.item(0, 2).data(Qt.UserRole) == "city"
    assert not dialog.table.isRowHidden(0)
    dialog.save_entries()
    assert dialog.entries == [{"name": "Saint-Brieuc", "aliases": ["saint brieu"], "category": "city"}, *previous]
    reopened = VocabularyDialog(dialog.entries)
    assert reopened.table.item(0, 0).text() == "Saint-Brieuc"
    reopened.set_filter("product")
    assert not reopened.table.isRowHidden(2) and reopened.table.isRowHidden(0)
    for window in (dialog, reopened):
        window.hide()
        window.deleteLater()
    app.processEvents()


def test_category_editor_commits_and_added_word_receives_focus():
    app = QApplication.instance() or QApplication([])
    dialog = VocabularyDialog([{"name": "Ancien", "aliases": []}])
    dialog.show()
    app.processEvents()
    dialog.set_filter("proper_name")
    QTest.mouseClick(dialog.add_button, Qt.LeftButton)
    QTest.keyClicks(dialog.table.focusWidget(), "Nouveau")
    QTest.keyClick(dialog.table.focusWidget(), Qt.Key_Tab)
    app.processEvents()
    assert dialog.table.item(0, 0).text() == "Nouveau"
    cell = dialog.table.item(0, 2)
    QTest.mouseClick(dialog.table.viewport(), Qt.LeftButton, pos=dialog.table.visualItemRect(cell).center())
    app.processEvents()
    editor = dialog.table.findChild(ChoiceBox)
    assert editor is not None
    editor.showPopup()
    QTest.keyClick(editor, Qt.Key_End)
    QTest.keyClick(editor, Qt.Key_Enter)
    app.processEvents()
    assert dialog.table.isRowHidden(0)
    dialog.table.setItem(0, 1, QTableWidgetItem("Nouveaux"))
    dialog.save_entries()
    assert dialog.entries[0] == {"name": "Nouveau", "aliases": ["Nouveaux"], "category": "technical"}
    dialog.hide()
    dialog.deleteLater()
    app.processEvents()
