from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QDialog, QHBoxLayout, QHeaderView,
                               QPushButton, QStyledItemDelegate, QTableWidget, QTableWidgetItem, QVBoxLayout)

from app.core.text_options import CATEGORY_LABELS, VOCABULARY_CATEGORIES, Vocabulary, normalize_vocabulary
from app.ui.caption_button import CaptionButton
from app.ui.preferences import ChoiceBox
from app.ui.premium import Chrome, HudShell, label


class CategoryDelegate(QStyledItemDelegate):
    """Create the category selector only while editing a cell, even for large dictionaries."""
    def createEditor(self, parent, option, index):
        editor = ChoiceBox(parent)
        editor.setAccessibleName("Catégorie du mot")
        editor.addItem("À classer", "")
        for identity, name in VOCABULARY_CATEGORIES:
            editor.addItem(name, identity)
        editor.activated.connect(lambda: self.commitData.emit(editor))
        return editor

    def setEditorData(self, editor, index):
        editor.setCurrentIndex(max(0, editor.findData(index.data(Qt.UserRole) or "")))

    def setModelData(self, editor, model, index):
        identity = editor.currentData()
        model.setData(index, CATEGORY_LABELS.get(identity, "À classer"), Qt.EditRole)
        model.setData(index, identity, Qt.UserRole)

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        painter.save()
        painter.setPen(QPen(QColor("#bd8c5f"), 1.2, Qt.SolidLine, Qt.RoundCap))
        x, y = option.rect.right() - 13, option.rect.center().y()
        painter.drawLine(x - 3, y - 1, x, y + 2)
        painter.drawLine(x, y + 2, x + 3, y - 1)
        painter.restore()


class VocabularyDialog(QDialog):
    def __init__(self, entries, parent=None, save_callback=None):
        super().__init__(parent, Qt.FramelessWindowHint)
        self.setWindowTitle("Dictionnaire — Transcrinator")
        self.setAttribute(Qt.WA_TranslucentBackground)
        area = self.screen().availableGeometry()
        self.setMinimumSize(720, 400)
        self.resize(min(860, area.width() - 40), min(540, area.height() - 40))
        self.entries = normalize_vocabulary(entries)
        self.save_callback = save_callback
        self.active_category = ""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        shell = HudShell()
        outer.addWidget(shell)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(24, 18, 24, 22)
        layout.setSpacing(12)
        chrome = Chrome()
        title = QHBoxLayout(chrome)
        title.setContentsMargins(0, 0, 0, 0)
        title.addWidget(label("Dictionnaire", "PageTitle"))
        title.addStretch()
        close = self.close_button = CaptionButton(close=True)
        close.setAccessibleName("Fermer le dictionnaire")
        close.setToolTip(close.accessibleName())
        close.setAutoDefault(False)
        close.clicked.connect(self.reject)
        title.addWidget(close)
        layout.addWidget(chrome)
        filters = QHBoxLayout()
        filters.setSpacing(7)
        self.filter_group = QButtonGroup(self)
        self.filter_buttons = {}
        for identity, name in (("", "Tous"), *VOCABULARY_CATEGORIES):
            button = QPushButton(name)
            button.setObjectName("CategoryFilter")
            button.setCheckable(True)
            button.setChecked(not identity)
            button.clicked.connect(lambda checked, category=identity: self.set_filter(category))
            self.filter_group.addButton(button)
            self.filter_buttons[identity] = button
            filters.addWidget(button)
        filters.addStretch()
        layout.addLayout(filters)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Mot ou nom correct", "Erreurs habituelles", "Catégorie"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 168)
        self.table.horizontalHeaderItem(1).setToolTip("Séparez les erreurs habituelles par des virgules.")
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setItemDelegateForColumn(2, CategoryDelegate(self.table))
        self.table.clicked.connect(self.edit_category)
        for entry in self.entries:
            self.add_row(entry["name"], ", ".join(entry["aliases"]), entry.get("category", ""), first=False)
        if not self.entries:
            self.add_row()
        self.table.itemChanged.connect(self.apply_filter)
        layout.addWidget(self.table, 1)
        layout.addWidget(label("Erreurs habituelles : Pouzauge, Pousauges → Pouzauges. Séparez les variantes par des virgules.", "DictionaryHint"))
        self.notice = label("", "Notice")
        self.notice.hide()
        layout.addWidget(self.notice)
        actions = QHBoxLayout()
        self.add_button = QPushButton("Ajouter un mot")
        self.add_button.clicked.connect(lambda: self.add_row(edit=True))
        actions.addWidget(self.add_button)
        remove = QPushButton("Supprimer")
        remove.clicked.connect(self.remove_rows)
        actions.addWidget(remove)
        actions.addStretch()
        save = QPushButton("Enregistrer")
        save.setObjectName("Primary")
        save.clicked.connect(self.save_entries)
        actions.addWidget(save)
        layout.addLayout(actions)

    def add_row(self, name="", aliases="", category=None, *, first=True, edit=False):
        if category is None:
            category = self.active_category or "proper_name"
        row = 0 if first else self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(name))
        self.table.setItem(row, 1, QTableWidgetItem(aliases))
        category_item = QTableWidgetItem(CATEGORY_LABELS.get(category, "À classer"))
        category_item.setData(Qt.UserRole, category)
        category_item.setForeground(QColor("#e4b17c"))
        category_item.setToolTip("Cliquez pour choisir une catégorie.")
        self.table.setItem(row, 2, category_item)
        if first or self.active_category:
            self.apply_filter()
        if edit:
            self.table.clearSelection()
            self.table.setCurrentCell(row, 0)
            self.table.scrollToItem(self.table.item(row, 0), QAbstractItemView.PositionAtTop)
            self.table.editItem(self.table.item(row, 0))

    def edit_category(self, index):
        if index.column() == 2:
            self.table.edit(index)

    def set_filter(self, category):
        self.active_category = category
        self.filter_buttons[category].setChecked(True)
        self.table.clearSelection()
        self.apply_filter()

    def apply_filter(self, *_):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 2)
            category = item.data(Qt.UserRole) if item else ""
            self.table.setRowHidden(row, bool(self.active_category and category != self.active_category))

    def remove_rows(self):
        for row in sorted({item.row() for item in self.table.selectedIndexes()}, reverse=True):
            self.table.removeRow(row)

    def save_entries(self):
        entries = []
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text().strip()
            aliases = self.table.item(row, 1).text().strip()
            if aliases and not name:
                self.notice.setText("Indiquez le mot ou nom correct pour cette ligne.")
                self.notice.show()
                return
            if name:
                entry = {"name": name, "aliases": [part.strip() for part in aliases.split(",") if part.strip()],
                         "category": self.table.item(row, 2).data(Qt.UserRole)}
                entries.append(entry)
        entries = normalize_vocabulary(entries)
        if Vocabulary(entries).ambiguous:
            self.notice.setText("Une même erreur correspond à plusieurs mots. Modifiez les lignes concernées.")
            self.notice.show()
            return
        if self.save_callback is not None and not self.save_callback(entries):
            self.notice.setText("Enregistrement impossible. Vos modifications restent ici ; réessayez.")
            self.notice.show()
            return
        self.entries = entries
        self.accept()
