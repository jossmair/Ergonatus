"""A non-activating, mouse-operated keyboard with a Unicode composition buffer."""
import unicodedata

from PySide6.QtCore import QEvent, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QApplication, QButtonGroup, QGridLayout, QHBoxLayout, QPlainTextEdit,
                              QLayout, QPushButton, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget)

from .desktop_target import protect_tool_window, reject_mouse_activation
from .keyboard_layout import CHARACTERS, LETTER_ROWS, NUMBER_KEYS, SPECIAL_KEYS, erase_character, unicode_character
from .theme import app_icon, label


def draw_key_skin(painter, target):
    """One continuous surface: no texture slices or seams, even on wide keys."""
    rect = target.adjusted(1, 1, -1, -2)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(0, 10, 15, 120))
    painter.drawRoundedRect(rect.translated(0, 2), 8, 8)
    surface = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    surface.setColorAt(0, QColor("#23494d"))
    surface.setColorAt(.35, QColor("#18393e"))
    surface.setColorAt(1, QColor("#102d34"))
    painter.setBrush(surface)
    rim = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    rim.setColorAt(0, QColor("#4e8b89"))
    rim.setColorAt(1, QColor("#254f55"))
    painter.setPen(QPen(rim, 1))
    painter.drawRoundedRect(rect, 8, 8)


class KeyboardHandle(QWidget):
    """Move the tool window directly, without starting an activating native move."""
    moved = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("KeyboardHandle")
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip("Faites glisser cette barre pour déplacer le clavier")
        self.setAccessibleName("Déplacer le clavier")
        self.origin = None
        self.dragged = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.origin = event.globalPosition().toPoint()
            self.start_position = self.window().pos()
            self.dragged = False
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        if self.origin is not None and event.buttons() & Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self.origin
            if self.dragged or delta.manhattanLength() >= QApplication.startDragDistance():
                self.dragged = True
                self.window().move(self.start_position + delta)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.origin is not None:
            moved = self.dragged
            self.origin = None
            self.dragged = False
            self.setCursor(Qt.OpenHandCursor)
            if moved:
                self.moved.emit()
            event.accept()


class KeyCap(QPushButton):
    def __init__(self, text, callback, parent=None, secondary="", checkable=False, height=40, minimum_width=32):
        super().__init__(text, parent)
        self.setObjectName("VirtualKey")
        self.setStyleSheet("QPushButton#VirtualKey {padding:0; border:none; background:transparent;"
                          f"min-width:{minimum_width}px; min-height:{height}px; max-height:{height}px;}}")
        self.secondary = secondary
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(checkable)
        self.setMinimumWidth(minimum_width)
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setAccessibleName(text)
        self.clicked.connect(callback)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if not self.isEnabled():
            painter.setOpacity(.35)
        rect = QRectF(self.rect()).adjusted(0, 0, 0, -1)
        if self.isDown():
            rect.translate(0, 1.5)
        draw_key_skin(painter, rect)
        if self.isChecked() or self.underMouse() or self.isDown():
            painter.setBrush(QColor(86, 221, 193, 65 if self.isChecked() else 26))
            painter.setPen(QPen(QColor("#9aefd9" if self.isChecked() else "#5bbaad"), 1))
            painter.drawRoundedRect(rect.adjusted(3.5, 3, -3.5, -4), 8, 8)
        painter.setPen(QColor("#ddfff4"))
        font = QFont("Segoe UI", 13 if len(self.text()) <= 2 else 9)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        text_rect = rect.adjusted(5, 1, -5, -4)
        if self.secondary:
            text_rect.adjust(0, 4, 0, 0)
        painter.drawText(text_rect, Qt.AlignCenter, self.text())
        if self.secondary:
            painter.setFont(QFont("Segoe UI", 7))
            painter.setPen(QColor("#83b8b5"))
            painter.drawText(rect.adjusted(6, 4, -7, -4), Qt.AlignTop | Qt.AlignRight, self.secondary)


def tool_button(text, callback, name="KeyboardTab"):
    item = QPushButton(text)
    item.setObjectName(name)
    item.setFocusPolicy(Qt.NoFocus)
    item.setCursor(Qt.PointingHandCursor)
    item.clicked.connect(callback)
    return item


class VirtualKeyboard(QWidget):
    insert_requested = Signal(str)
    key_requested = Signal(list)
    hidden = Signal()
    emergency_requested = Signal()
    moved = Signal()
    fit_requested = Signal()
    target_pick_requested = Signal()

    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.setWindowTitle("Claviernator · Clavier virtuel")
        self.setWindowIcon(app_icon())
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.setMinimumSize(820, 320)
        self.setMaximumSize(900, 320)
        self.resize(900, 320)
        self.text = ""
        self.shift = self.caps = self.altgr = False
        self.unicode_code = "20AC"
        self.character_buttons = []
        self.modifier_buttons = {0xA2: [], 0xA4: [], 0x5B: []}
        self.modifiers = set()
        self.setStyleSheet("""
            QPushButton#KeyboardTab {background:transparent; border:1px solid transparent; color:#8ab8b6;
                border-radius:9px; padding:5px 12px; min-height:20px; font:600 9pt 'Segoe UI';}
            QPushButton#KeyboardTab:hover {background:#193b3c; color:#d6fff2;}
            QPushButton#KeyboardTab:checked {background:#1c4644; border-color:#3e8075; color:#c6ffeb;}
            QPushButton#KeyboardInsert {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #8debd4,stop:1 #4fc5b7);
                color:#092e2d; border:1px solid #b8f7e4; border-radius:12px;
                padding:6px 22px; min-height:24px; font:600 11pt 'Segoe UI';}
            QPushButton#KeyboardInsert:hover {background:#a4f6df;}
            QPushButton#KeyboardInsert:disabled {background:#254442; color:#7b9b94; border-color:#385954;}
            QPushButton#KeyboardPick, QPushButton#KeyboardErase {background:#123337; color:#b3eee0; border:1px solid #38746e;
                border-radius:12px; padding:6px 14px; min-height:24px; font:600 10pt 'Segoe UI';}
            QPushButton#KeyboardPick:hover, QPushButton#KeyboardErase:hover {background:#1a4847; border-color:#7edbc6; color:#e4fff6;}
            QPushButton#KeyboardErase:disabled {color:#648c85; border-color:#294e4d;}
            QPlainTextEdit#Composition {background:#091b20; color:#e0fff4; border:1px solid #305b5c;
                border-radius:11px; padding:8px 12px; font:12pt 'Segoe UI';}
            QLabel#KeyboardDestination {color:#83a9a7; font:8pt 'Segoe UI';}
            QLabel#KeyboardError {color:#efd3a6; font:9pt 'Segoe UI';}
        """)
        root = QVBoxLayout(self)
        root.setSizeConstraint(QLayout.SetNoConstraint)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(4)
        self.handle = KeyboardHandle(self)
        self.handle.moved.connect(self.moved)
        header = QHBoxLayout(self.handle)
        header.setContentsMargins(0, 0, 0, 0)
        grip = label("⠿")
        grip.setStyleSheet("color:#71aaa5; font:18pt 'Segoe UI';")
        grip.setAttribute(Qt.WA_TransparentForMouseEvents)
        header.addWidget(grip)
        title = label("Clavier", "CardTitle")
        title.setStyleSheet("font:600 16pt 'Segoe UI'; color:#e3fff5;")
        title.setAttribute(Qt.WA_TransparentForMouseEvents)
        header.addWidget(title)
        self.destination = label("Cliquez dans le champ où écrire.", "KeyboardDestination")
        self.destination.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.destination.setAttribute(Qt.WA_TransparentForMouseEvents)
        header.addWidget(self.destination, 1)
        hide = tool_button("×", self.hide_keyboard)
        hide.setFixedSize(32, 32)
        hide.setAccessibleName("Masquer le clavier virtuel")
        hide.setToolTip("Masquer le clavier")
        header.addWidget(hide)
        root.addWidget(self.handle)
        self.preview = QPlainTextEdit()
        self.preview.setObjectName("Composition")
        self.preview.setReadOnly(True)
        self.preview.setFocusPolicy(Qt.NoFocus)
        self.preview.setFixedHeight(44)
        self.preview.setPlaceholderText("Votre texte… puis Insérer")
        self.preview.setAccessibleName("Texte à insérer")
        root.addWidget(self.preview)
        body = QHBoxLayout()
        body.setSpacing(10)
        tabs = QVBoxLayout()
        tabs.setSpacing(5)
        self.tabs = QButtonGroup(self)
        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        for index, caption in enumerate(("Clavier", "Caractères", "Touches")):
            item = tool_button(caption, lambda checked=False, i=index: self.stack.setCurrentIndex(i))
            item.setCheckable(True)
            self.tabs.addButton(item, index)
            item.setFixedWidth(88)
            tabs.addWidget(item)
        self.tabs.button(0).setChecked(True)
        self.stack.currentChanged.connect(lambda index: self.tabs.button(index).setChecked(True))
        self.clear_button = KeyCap("Vider", self.clear_text, height=40)
        self.clear_button.setFixedWidth(88)
        self.clear_button.setToolTip("Effacer le texte préparé")
        tabs.addStretch()
        tabs.addWidget(self.clear_button)
        left_rail = QWidget()
        left_rail.setLayout(tabs)
        tabs.setContentsMargins(0, 0, 0, 0)
        left_rail.setFixedSize(88, 216)
        body.addWidget(left_rail, 0, Qt.AlignTop)
        self.stack.addWidget(self.letters_page())
        self.stack.addWidget(self.characters_page())
        self.stack.addWidget(self.special_page())
        body.addWidget(self.stack, 1)
        footer = QVBoxLayout()
        footer.setSpacing(8)
        self.erase_button = tool_button("Effacer", lambda: self.send_shortcut([0x08]), "KeyboardErase")
        self.erase_button.setToolTip("Effacer le caractère avant le curseur dans le champ sélectionné")
        self.erase_button.setEnabled(False)
        footer.addWidget(self.erase_button)
        self.error = label("", "KeyboardError")
        self.error.setWordWrap(True)
        self.error.setMaximumWidth(124)
        self.error.hide()
        footer.addWidget(self.error)
        self.pick_button = tool_button("Choisir où écrire", lambda: self.target_pick_requested.emit(), "KeyboardPick")
        self.pick_button.setToolTip("Masquer le clavier, cliquer dans le champ souhaité, puis retrouver le clavier et votre texte")
        self.pick_button.setText("Choisir où\nécrire")
        self.pick_button.setAccessibleName("Choisir où écrire")
        footer.addStretch()
        footer.addWidget(self.pick_button)
        footer.addStretch()
        self.insert_button = tool_button("Insérer  →", lambda: self.insert_requested.emit(self.text), "KeyboardInsert")
        self.insert_button.setAccessibleName("Insérer dans la zone de saisie précédente")
        self.insert_button.setEnabled(False)
        self.insert_button.setFixedHeight(40)
        footer.addWidget(self.insert_button)
        for button in (self.erase_button, self.pick_button, self.insert_button):
            button.setFixedWidth(124)
        right_rail = QWidget()
        right_rail.setLayout(footer)
        footer.setContentsMargins(0, 0, 0, 0)
        right_rail.setFixedSize(124, 216)
        body.addWidget(right_rail, 0, Qt.AlignTop)
        root.addLayout(body, 1)

    def nativeEvent(self, event_type, message):
        handled, result = reject_mouse_activation(message)
        return (handled, result) if handled else super().nativeEvent(event_type, message)

    def event(self, event):
        result = super().event(event)
        if event.type() == QEvent.DevicePixelRatioChange:
            self.fit_requested.emit()
        return result

    def reveal(self):
        protect_tool_window(self)
        self.show()
        self.raise_()

    def hide_keyboard(self):
        self.hide()
        self.clear_modifiers()
        self.hidden.emit()

    def set_target(self, target):
        name = target.title if target else "Cliquez dans le champ où écrire."
        self.destination.setText(("Vers : " if target else "") + (name if len(name) <= 52 else name[:49] + "…"))
        self.destination.setToolTip(name)
        self.erase_button.setEnabled(target is not None)
        self.error.setText("")
        self.error.hide()

    def show_error(self, message):
        self.error.setText(message)
        self.error.setVisible(bool(message))

    def refresh_text(self):
        self.preview.setPlainText(self.text)
        self.preview.moveCursor(self.preview.textCursor().MoveOperation.End)
        self.insert_button.setEnabled(bool(self.text))
        self.clear_button.setEnabled(bool(self.text))
        self.error.setText("")
        self.error.hide()

    def append_text(self, value):
        if len(self.text) + len(value) > 10000:
            self.show_error("Insérez ce texte avant de continuer.")
            return
        self.text += value
        self.refresh_text()

    def clear_text(self):
        self.text = ""
        self.refresh_text()

    def backspace(self):
        self.text = erase_character(self.text)
        self.refresh_text()

    def new_row(self, layout):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2)
        layout.addLayout(row)
        return row

    def add_character_key(self, row, base, shifted=None, alt="", vk=None, stretch=1):
        data = (base, shifted if shifted is not None else base.upper(), alt, vk or ord(base.upper()))
        item = KeyCap(base, lambda checked=False, value=data: self.type_character(value), secondary=shifted or "")
        row.addWidget(item, stretch)
        self.character_buttons.append((item, data))
        return item

    def letters_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        row = self.new_row(layout)
        for data in NUMBER_KEYS:
            self.add_character_key(row, *data)
        row = self.new_row(layout)
        for char in LETTER_ROWS[0]:
            self.add_character_key(row, char.lower())
        self.add_character_key(row, "^", "¨", "", 0xDD)
        self.add_character_key(row, "$", "£", "€", 0xBA)
        row = self.new_row(layout)
        self.caps_button = KeyCap("Verr. Maj", self.toggle_caps, checkable=True)
        row.addWidget(self.caps_button, 2)
        for char in LETTER_ROWS[1]:
            self.add_character_key(row, char.lower())
        self.add_character_key(row, "ù", "%", "", 0xC0)
        row = self.new_row(layout)
        self.shift_button = KeyCap("Maj", self.toggle_shift, checkable=True)
        row.addWidget(self.shift_button, 2)
        for char in LETTER_ROWS[2]:
            self.add_character_key(row, char.lower())
        for data in [("é", "É", "", 0x32), ("è", "È", "", 0x37), (",", "?", "", 0xBC), (".", ";", "", 0xBE)]:
            self.add_character_key(row, *data)
        row.addWidget(KeyCap("⌫", self.backspace), 2)
        row = self.new_row(layout)
        self.add_modifiers(row)
        self.altgr_button = KeyCap("AltGr", self.toggle_altgr, checkable=True)
        row.addWidget(self.altgr_button, 1)
        row.addWidget(KeyCap("Espace", lambda: self.compose_or_send(" ", 0x20)), 4)
        row.addWidget(KeyCap("Tab", lambda: self.compose_or_send("\t", 9)), 1)
        row.addWidget(KeyCap("Entrée", lambda: self.compose_or_send("\n", 13)), 2)
        layout.addStretch()
        return page

    def add_modifiers(self, row):
        for caption, key in [("Ctrl", 0xA2), ("Alt", 0xA4), ("Win", 0x5B)]:
            item = KeyCap(caption, lambda checked, k=key: self.toggle_modifier(k, checked), checkable=True)
            self.modifier_buttons[key].append(item)
            row.addWidget(item, 1)

    def characters_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        categories = QHBoxLayout()
        group = QButtonGroup(page)
        self.characters_stack = QStackedWidget()
        for index, caption in enumerate([*CHARACTERS, "Unicode"]):
            item = tool_button(caption, lambda checked=False, i=index: self.characters_stack.setCurrentIndex(i))
            item.setCheckable(True)
            group.addButton(item, index)
            categories.addWidget(item)
        group.button(0).setChecked(True)
        self.characters_stack.currentChanged.connect(lambda index: group.button(index).setChecked(True))
        categories.addStretch()
        layout.addLayout(categories)
        for values in CHARACTERS.values():
            grid_page = QWidget()
            grid = QGridLayout(grid_page)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(2)
            for index, value in enumerate(values):
                item = KeyCap(value, lambda checked=False, char=value: self.append_text(char))
                item.setToolTip(unicodedata.name(value[0], value))
                grid.addWidget(item, index // 12, index % 12)
            for col in range(12):
                grid.setColumnStretch(col, 1)
            grid.setRowStretch(5, 1)
            self.characters_stack.addWidget(grid_page)
        self.characters_stack.addWidget(self.unicode_page())
        layout.addWidget(self.characters_stack, 1)
        return page

    def unicode_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        grid = QGridLayout()
        grid.setSpacing(1)
        for index, value in enumerate("0123456789ABCDEF"):
            grid.addWidget(KeyCap(value, lambda checked=False, char=value: self.enter_hex(char)), index // 4, index % 4)
        layout.addLayout(grid, 1)
        details = QVBoxLayout()
        details.setContentsMargins(18, 4, 4, 4)
        details.addWidget(label("Tous les caractères Unicode", "CardTitle"))
        self.code_label = label("U+20AC", "Subtitle")
        details.addWidget(self.code_label)
        self.code_preview = label("€")
        self.code_preview.setStyleSheet("font:32pt 'Segoe UI'; color:#c3ffe8;")
        details.addWidget(self.code_preview, 1)
        controls = QHBoxLayout()
        controls.addWidget(tool_button("Effacer le code", self.clear_hex))
        controls.addWidget(tool_button("⌫", self.erase_hex))
        details.addLayout(controls)
        self.add_unicode = tool_button("Ajouter ce caractère", self.commit_unicode)
        details.addWidget(self.add_unicode)
        layout.addLayout(details, 2)
        return page

    def enter_hex(self, value):
        if len(self.unicode_code) >= 6:
            return
        self.unicode_code += value
        self.refresh_hex()

    def clear_hex(self):
        self.unicode_code = ""
        self.refresh_hex()

    def erase_hex(self):
        self.unicode_code = self.unicode_code[:-1]
        self.refresh_hex()

    def refresh_hex(self):
        self.code_label.setText("U+" + (self.unicode_code or "…"))
        try:
            char = unicode_character(self.unicode_code)
        except ValueError:
            char = ""
        self.code_preview.setText(char or "—")
        self.add_unicode.setEnabled(bool(char))

    def commit_unicode(self):
        try:
            self.append_text(unicode_character(self.unicode_code))
        except ValueError as exc:
            self.show_error(str(exc))

    def special_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        category_row = QHBoxLayout()
        categories = QButtonGroup(page)
        pages = QStackedWidget()
        sections = {
            "Navigation": SPECIAL_KEYS[1:],
            "F1–F24": [[(f"F{i}", 0x6F + i) for i in range(start, start + 12)] for start in (1, 13)],
            "Pavé numérique": [[("Verr. Num", 0x90), ("/", 0x6F), ("×", 0x6A), ("−", 0x6D)],
                               [("7", 0x67), ("8", 0x68), ("9", 0x69), ("+", 0x6B)],
                               [("4", 0x64), ("5", 0x65), ("6", 0x66)],
                               [("1", 0x61), ("2", 0x62), ("3", 0x63), ("0", 0x60), ("Décimale", 0x6E)]],
            "Média": [[("Muet", 0xAD), ("Volume −", 0xAE), ("Volume +", 0xAF)],
                      [("Précédent", 0xB1), ("Lecture / pause", 0xB3), ("Suivant", 0xB0), ("Arrêter", 0xB2)],
                      [("Menu", 0x5D), ("Verr. défil.", 0x91), ("Pause", 0x13)]],
        }
        for index, (caption, rows) in enumerate(sections.items()):
            category = tool_button(caption, lambda checked=False, i=index: pages.setCurrentIndex(i))
            category.setCheckable(True)
            categories.addButton(category, index)
            category_row.addWidget(category)
            section = QWidget()
            section_layout = QVBoxLayout(section)
            section_layout.setContentsMargins(0, 0, 0, 0)
            section_layout.setSpacing(2)
            for values in rows:
                row = self.new_row(section_layout)
                for caption, key in values:
                    item = KeyCap(caption, lambda checked=False, vk=key: self.send_special(vk))
                    if key == 0x7B:
                        item.setToolTip("F12 met les adaptations en pause.")
                    row.addWidget(item, 1)
            section_layout.addStretch()
            pages.addWidget(section)
        categories.button(0).setChecked(True)
        pages.currentChanged.connect(lambda index: categories.button(index).setChecked(True))
        layout.addLayout(category_row)
        layout.addWidget(pages, 1)
        row = self.new_row(layout)
        self.add_modifiers(row)
        row.addWidget(KeyCap("Copier", lambda: self.send_shortcut([0xA2, 67])), 2)
        row.addWidget(KeyCap("Coller", lambda: self.send_shortcut([0xA2, 86])), 2)
        row.addWidget(KeyCap("Annuler", lambda: self.send_shortcut([0xA2, 90])), 2)
        layout.addWidget(label("Ces touches agissent directement dans votre document.", "KeyboardDestination"))
        return page

    def toggle_caps(self, checked):
        self.caps = checked
        self.refresh_characters()

    def toggle_shift(self, checked):
        self.shift = checked
        self.refresh_characters()

    def toggle_altgr(self, checked):
        self.altgr = checked
        self.refresh_characters()

    def toggle_modifier(self, key, checked):
        self.modifiers.add(key) if checked else self.modifiers.discard(key)
        for item in self.modifier_buttons[key]:
            item.setChecked(checked)
        self.preview.setPlaceholderText("Raccourci : choisissez la prochaine touche." if self.modifiers else "Votre texte… puis Insérer")

    def character_value(self, data):
        base, shifted, alt, _ = data
        if self.altgr and alt:
            return alt
        if base.isalpha():
            return base.upper() if self.caps != self.shift else base.lower()
        return shifted if self.shift else base

    def refresh_characters(self):
        for item, data in self.character_buttons:
            item.setText(self.character_value(data))
            item.setAccessibleName(item.text())
            item.update()

    def consume_shift(self):
        if self.shift:
            self.shift = False
            self.shift_button.setChecked(False)
        self.refresh_characters()

    def clear_modifiers(self):
        for key in list(self.modifiers):
            self.toggle_modifier(key, False)
        self.shift = self.altgr = False
        self.shift_button.setChecked(False)
        self.altgr_button.setChecked(False)
        self.refresh_characters()

    def type_character(self, data):
        if self.modifiers:
            self.send_shortcut([*sorted(self.modifiers), *([0xA0] if self.shift else []), data[3]])
        else:
            self.append_text(self.character_value(data))
            self.consume_shift()

    def compose_or_send(self, text, key):
        if self.modifiers:
            self.send_shortcut([*sorted(self.modifiers), *([0xA0] if self.shift else []), key])
        else:
            self.append_text(text)
            self.consume_shift()

    def send_shortcut(self, keys):
        self.key_requested.emit(keys)
        self.clear_modifiers()

    def send_special(self, key):
        if key == 0x7B:
            self.clear_modifiers()
            self.emergency_requested.emit()
        else:
            self.send_shortcut([*sorted(self.modifiers), *([0xA0] if self.shift else []), key])

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        outline = QPainterPath()
        outline.addRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 20, 20)
        painter.setClipPath(outline)
        # Paint alpha directly: an opaque wallpaper underneath would hide the desktop.
        surface = QLinearGradient(0, 0, self.width(), self.height())
        surface.setColorAt(0, QColor(7, 30, 35, 202))
        surface.setColorAt(1, QColor(3, 19, 25, 190))
        painter.fillPath(outline, surface)
        glow = QLinearGradient(0, 0, self.width(), 0)
        glow.setColorAt(0, QColor(90, 220, 194, 25))
        glow.setColorAt(1, QColor(31, 84, 96, 8))
        painter.fillRect(QRectF(0, 0, self.width(), 70), glow)
        painter.setClipping(False)
        painter.setPen(QPen(QColor("#528b83"), 1))
        painter.drawPath(outline)

    def closeEvent(self, event):
        self.hide_keyboard()
        event.ignore()
