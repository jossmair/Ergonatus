"""Explicit recovery through the tray, without a transcript panel or notification."""
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication


class RetainedTextAction(QAction):
    def __init__(self, controller, parent=None):
        super().__init__("Copier le texte non inséré", parent)
        self.controller = controller
        self.text_to_copy = ""
        self.setEnabled(False)
        controller.retained_changed.connect(self.update_text)
        self.triggered.connect(self.copy_text)

    def update_text(self, text):
        self.text_to_copy = text
        self.setEnabled(bool(text))

    def copy_text(self):
        if self.text_to_copy:
            QApplication.clipboard().setText(self.text_to_copy)
            self.text_to_copy = ""
            self.setEnabled(False)
            self.controller.request("clear_retained")
