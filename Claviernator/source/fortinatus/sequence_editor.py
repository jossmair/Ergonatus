"""Ordered keyboard steps, composed without holding several keys at once."""
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QPushButton, QSpinBox, QVBoxLayout, QWidget
from .keys import combo_name
from .theme import label, trash_icon
from .widgets import Switch


class SequenceEditor(QWidget):
    def __init__(self, mapping, key_combo):
        super().__init__()
        self.steps = [step[:] for step in mapping.sequence]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(label("Un appui lance les étapes dans l’ordre.", "Muted"))
        self.list = QListWidget()
        self.list.setAccessibleName("Étapes de la suite de touches")
        self.list.setMinimumHeight(112)
        self.list.setMaximumHeight(160)
        self.list.currentRowChanged.connect(self.select_step)
        layout.addWidget(self.list)
        self.checks = []
        row = QHBoxLayout()
        for text, vk, group in [("Ctrl", 0xA2, {0xA2, 0xA3}), ("Alt", 0xA4, {0xA4, 0xA5}),
                                 ("Maj", 0xA0, {0xA0, 0xA1}), ("Win", 0x5B, {0x5B, 0x5C})]:
            switch = Switch(text)
            self.checks.append((switch, vk, group))
            row.addWidget(switch)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.target = key_combo()
        self.target.setCurrentIndex(self.target.findData(9))
        self.target.setAccessibleName("Touche de l’étape")
        row.addWidget(self.target, 1)
        self.add_button = QPushButton("+ Ajouter")
        self.add_button.clicked.connect(lambda: self.add_step(self.selected_keys()))
        row.addWidget(self.add_button)
        self.replace_button = QPushButton("Remplacer")
        self.replace_button.clicked.connect(self.replace_step)
        row.addWidget(self.replace_button)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.up = QPushButton("↑")
        self.up.setAccessibleName("Monter l’étape")
        self.up.clicked.connect(lambda: self.move_step(-1))
        self.down = QPushButton("↓")
        self.down.setAccessibleName("Descendre l’étape")
        self.down.clicked.connect(lambda: self.move_step(1))
        self.delete = QPushButton()
        self.delete.setObjectName("Delete")
        self.delete.setIcon(trash_icon())
        self.delete.setFixedSize(40, 40)
        self.delete.setAccessibleName("Supprimer l’étape")
        self.delete.setToolTip("Supprimer l’étape")
        self.delete.clicked.connect(self.remove_step)
        for control in (self.up, self.down, self.delete):
            row.addWidget(control)
        row.addStretch()
        row.addWidget(label("Délai", "Muted"))
        self.interval = QSpinBox()
        self.interval.setRange(20, 2000)
        self.interval.setSingleStep(20)
        self.interval.setSuffix(" ms")
        self.interval.setValue(mapping.interval_ms)
        self.interval.setAccessibleName("Délai entre les étapes")
        row.addWidget(self.interval)
        layout.addLayout(row)
        self.refresh(0)

    def selected_keys(self):
        keys = [vk for control, vk, group in self.checks if control.isChecked()]
        if self.target.currentData() not in keys:
            keys.append(self.target.currentData())
        return keys

    def select_step(self, row):
        selected = 0 <= row < len(self.steps)
        self.replace_button.setEnabled(selected)
        self.delete.setEnabled(selected)
        self.up.setEnabled(selected and row > 0)
        self.down.setEnabled(selected and row < len(self.steps) - 1)
        if selected:
            keys = self.steps[row]
            for control, vk, group in self.checks:
                control.setChecked(len(keys) > 1 and bool(set(keys) & group))
            self.target.setCurrentIndex(self.target.findData(keys[-1]))

    def refresh(self, row):
        self.list.blockSignals(True)
        self.list.clear()
        for index, step in enumerate(self.steps, 1):
            self.list.addItem(f"{index:02d}   {combo_name(step)}")
        self.list.setCurrentRow(min(row, len(self.steps) - 1))
        self.list.blockSignals(False)
        self.select_step(self.list.currentRow())
        self.add_button.setEnabled(len(self.steps) < 50)

    def add_step(self, keys):
        if keys and len(self.steps) < 50:
            self.steps.append(list(keys))
            self.refresh(len(self.steps) - 1)

    def replace_step(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.steps):
            self.steps[row] = self.selected_keys()
            self.refresh(row)

    def remove_step(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.steps):
            self.steps.pop(row)
            self.refresh(row)

    def move_step(self, offset):
        row = self.list.currentRow()
        other = row + offset
        if 0 <= row < len(self.steps) and 0 <= other < len(self.steps):
            self.steps[row], self.steps[other] = self.steps[other], self.steps[row]
            self.refresh(other)
