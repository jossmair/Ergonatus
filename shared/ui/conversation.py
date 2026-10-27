"""Native conversation bubbles; content stays in memory only."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget, QPushButton, QSizePolicy
class theme:
    @staticmethod
    def label(text,kind=None):
        item=QLabel(text);item.setTextFormat(Qt.PlainText);return item



class ChatPanel(QWidget):
    def __init__(self, result):
        super().__init__()
        self.setAccessibleName("Conversation")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.flow = QVBoxLayout(self)
        self.flow.setContentsMargins(0, 0, 3, 0)
        self.flow.setSpacing(9)
        self.flow.setAlignment(Qt.AlignTop)
        self.scroller = None
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self.scroll_to_bottom)
        self.composer_editor = None
        self.result = result
        self.current = None
        self.thinking = theme.label("", "Muted")
        self.thinking.hide()
        self.phase = 0
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.animate_thinking)
        self.result.hide()

    def bubble(self, role, text=None):
        row = QWidget()
        row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        align = QHBoxLayout(row)
        align.setContentsMargins(0, 0, 0, 0)
        frame = QFrame()
        frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        frame.setObjectName("UserBubble" if role == "Vous" else "AssistantBubble")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(13, 9, 13, 9)
        layout.setSpacing(5)

        if text is not None:
            label = theme.label(text)
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
            layout.addWidget(label)
        frame.setMaximumWidth(340)
        frame.setAccessibleName("Votre message" if role == "Vous" else "Réponse de l’assistant")
        if role == "Vous":
            align.addWidget(frame, 8)
            align.addStretch(1)
        else:
            align.addStretch(1)
            align.addWidget(frame, 8)
            from shared.apps.translator_chat import chat_icon
            from PySide6.QtWidgets import QApplication
            footer=QHBoxLayout();footer.addStretch();copy=QPushButton();copy.setIcon(chat_icon('copy'));copy.setFixedSize(28,28);copy.setObjectName('MessageCopy');copy.setAccessibleName('Copier cette réponse');copy.setToolTip('Copier cette réponse');copy.setStyleSheet('QPushButton#MessageCopy {padding:3px;min-height:0;background:transparent;border:none;border-radius:7px;} QPushButton#MessageCopy:hover {background:#E8F3EF;}');copy.clicked.connect(lambda checked=False,f=frame:QApplication.clipboard().setText(f.property('copy_text') or ''));footer.addWidget(copy);layout.addLayout(footer)
        self.flow.addWidget(row)
        return layout

    def begin(self, user_text, regenerate=False):
        if not regenerate:
            if self.current is not None:
                text = self.result.toPlainText()
                self.current.removeWidget(self.result)
                self.result.setParent(None)
                label = theme.label(text)
                label.setWordWrap(True)
                label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
                self.current.insertWidget(0,label)
            self.bubble("Vous", user_text)
            self.current = self.bubble("Redactor")
            self.current.insertWidget(0,self.result)
        self.flow.removeWidget(self.thinking)
        self.flow.addWidget(self.thinking)
        self.result.clear()
        self.result.show()
        self.resize_result()
        QTimer.singleShot(0,self.resize_result)
        self.scroll_latest()

    def resize_result(self):
        if self.current:self.current.parentWidget().setProperty('copy_text',self.result.toPlainText())
        self.result.fit_document()
        self.scroll_latest()

    def animate_thinking(self):
        self.phase = (self.phase + 1) % 4
        self.thinking.setText("Redactor réfléchit" + "·" * (self.phase + 1))

    def set_thinking(self, active):
        self.thinking.setVisible(active)
        if active:
            self.animate_thinking()
            self.timer.start()
        else:
            self.timer.stop()

    def scroll_latest(self):
        if self.scroller:
            self.scroll_timer.start(0)

    def scroll_to_bottom(self):
        if self.scroller:
            bar = self.scroller.verticalScrollBar()
            bar.setValue(bar.maximum())

    def reset(self):
        if self.current:
            self.current.removeWidget(self.result)
            self.result.setParent(None)
            self.result.hide()
        while self.flow.count():
            item = self.flow.takeAt(0)
            if item.widget() is self.thinking:
                continue
            if item.widget(): item.widget().deleteLater()
        self.set_thinking(False)
        self.current = None


def arrange_conversation(owner,source,result,send,actions,caption):
    from PySide6.QtCore import QSize,QObject,QEvent
    from PySide6.QtWidgets import QTextBrowser
    from PySide6.QtGui import QColor,QPainter,QIcon
    from shared.apps.translator_chat import chat_icon
    import types,math
    owner.content.removeWidget(source);owner.content.removeWidget(result);owner.content.removeItem(actions);actions.removeWidget(send)
    owner.chat=ChatPanel(result);owner.chat.composer_editor=source
    owner.chat_thread=QScrollArea();owner.chat_thread.setWidgetResizable(True);owner.chat_thread.setFrameShape(QFrame.NoFrame);owner.chat_thread.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(0,0,0,0);layout.addWidget(owner.chat);layout.addStretch();owner.chat_thread.setWidget(page);owner.chat.scroller=owner.chat_thread;owner.content.insertWidget(0,owner.chat_thread,1)
    def fit_document(editor):
        width=max(200,editor.viewport().width()-8);fm=editor.fontMetrics()
        if isinstance(editor,QTextBrowser):editor.document().setTextWidth(width);height=math.ceil(editor.document().size().height())+14
        else:height=sum(max(1,math.ceil(fm.horizontalAdvance(line)/width)) for line in editor.toPlainText().splitlines())*fm.lineSpacing()+12
        editor.setFixedHeight(min(1400,max(36,height)))
    result.fit_document=types.MethodType(fit_document,result);result.textChanged.connect(owner.chat.resize_result);result.textChanged.connect(lambda:QTimer.singleShot(0,owner.chat.resize_result));result.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff);result.setStyleSheet('QPlainTextEdit,QTextBrowser {background:transparent;border:none;padding:0;font-size:11pt;}')
    owner.composer=QFrame();owner.composer.setObjectName('Composer');owner.composer.setStyleSheet('QFrame#Composer {background:#F2F8F6;border:1px solid #AEC9C0;border-radius:17px;}');row=QHBoxLayout(owner.composer);row.setContentsMargins(12,8,8,8);source.setFixedHeight(78);source.setTextInteractionFlags(Qt.TextEditorInteraction);source.setStyleSheet('QPlainTextEdit {background:transparent;border:none;padding:2px;font-size:12pt;}');source.setPlaceholderText('Votre message…');row.addWidget(source,1)
    colour=QColor(owner.theme['accent'])
    while colour.lightness()>100:colour=colour.darker(110)
    icon=chat_icon('send').pixmap(36,36);p=QPainter(icon);p.setCompositionMode(QPainter.CompositionMode_SourceIn);p.fillRect(icon.rect(),QColor('white'));p.end();send.setIcon(QIcon(icon));send.setIconSize(QSize(23,23));send.setText('');send.setAccessibleName('Envoyer le message');send.setToolTip('Envoyer · Entrée');send.setFixedSize(38,38);send.setProperty('suitePrimary',True);send.setProperty('_suite_primary_styled',True);send.setStyleSheet('QPushButton[suitePrimary="true"] {background:'+colour.name()+';border:1px solid '+colour.name()+';border-radius:11px;padding:0;}');row.addWidget(send,0,Qt.AlignBottom);owner.content.addWidget(owner.composer)
    owner.content.addLayout(actions)
    for index in range(actions.count()):
        control=actions.itemAt(index).widget()
        if control is None:continue
        text=control.text();control.setToolTip(text);control.setAccessibleName(control.accessibleName() or text)
        if text=='Copier':control.setText('');control.setIcon(chat_icon('copy'));control.setFixedWidth(36);control.hide()
        elif 'Restaurer' in text:control.setText('↶');control.setFixedWidth(36)
        elif text=='Annuler':control.setText('■');control.setFixedWidth(36)
        control.setMaximumHeight(32)
    actions.addStretch(1)
    review=getattr(owner,'review_label',None)
    if review is not None:owner.content.removeWidget(review);owner.content.addWidget(review)
    class Submit(QObject):
        def eventFilter(self,watched,event):
            if event.type()==QEvent.KeyPress and event.key() in (Qt.Key_Return,Qt.Key_Enter) and not event.modifiers()&Qt.ShiftModifier:
                send.click();return True
            return False
    owner._composer_submit=Submit(source);source.installEventFilter(owner._composer_submit)
    owner.chat_thread.verticalScrollBar().rangeChanged.connect(lambda *_:owner.chat.scroll_latest())
