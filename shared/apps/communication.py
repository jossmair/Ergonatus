"""Voluntary communication board. No speech on card selection by default."""
import json
from PySide6.QtCore import Qt,QSize,QTimer,QPointF
from PySide6.QtGui import QIcon,QFont,QPainter,QPen,QColor,QPixmap
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QScrollArea,
    QPlainTextEdit,QLabel,QComboBox,QPushButton,QDialog,QDialogButtonBox,QLineEdit,
    QFormLayout,QFileDialog,QMessageBox,QListWidget,QCheckBox,QButtonGroup)
from shared.catalog import suite_root
from shared.domain import atomic_text
from shared.ui.components import ErgoButton

CATEGORIES=['Essentiels','École','Besoins','Ressentis','Échanges','Activités','Santé','Repas','Déplacements','Choisir','Autonomie','Questions','Mes cartes']
VOCABULARY={
 'Essentiels':[('👍','Oui'),('✋','Non'),('🙋','J’ai besoin d’aide'),('⏳','Attendez, s’il vous plaît'),('🛑','Stop'),('🙏','Merci'),('👋','Bonjour'),('❓','Je ne comprends pas')],
 'Besoins':[('💧','Je veux boire'),('🍽','J’ai faim'),('🚻','Je veux aller aux toilettes'),('😴','J’ai besoin de repos'),('🪑','Je veux m’asseoir'),('🏠','Je veux rentrer'),('🧥','J’ai froid'),('☀','J’ai chaud')],
 'Ressentis':[('🙂','Je vais bien'),('😣','J’ai mal'),('😟','J’ai peur'),('😢','Je suis triste'),('😠','Je suis en colère'),('😴','Je suis fatigué'),('😌','J’ai besoin de calme'),('❤️','Je suis content')],
 'Échanges':[('💬','Je voudrais'),('🙋','Je'),('👉','Tu'),('🤝','S’il vous plaît'),('🔁','Pouvez-vous répéter ?'),('🐢','Parlez plus lentement'),('👂','Écoutez-moi'),('👋','Au revoir')],
 'Activités':[('📖','Lire'),('🎵','Écouter de la musique'),('🚶','Sortir'),('🎲','Jouer'),('📺','Regarder une vidéo'),('✏','Écrire'),('👥','Voir quelqu’un'),('☕','Faire une pause')],
}

VOCABULARY.update({
 'Santé':[('😣','J’ai mal à la tête'),('🦷','J’ai mal aux dents'),('🤢','J’ai mal au ventre'),('🦵','J’ai mal à la jambe'),('🫁','J’ai du mal à respirer'),('🤕','Je me suis fait mal'),('💊','J’ai besoin de mon traitement'),('🩺','Je veux voir un médecin'),('📍','J’ai mal ici'),('🤒','Je me sens malade'),('🛏','Je veux m’allonger'),('🤝','Restez avec moi')],
 'Repas':[('🥤','Je voudrais de l’eau'),('🍎','Je voudrais un fruit'),('🍞','Je voudrais du pain'),('🍽','Je voudrais manger'),('✅','C’est bon'),('✋','Je n’en veux plus'),('♨','C’est trop chaud'),('🧊','C’est trop froid'),('🔪','Pouvez-vous couper ?'),('🥄','J’ai besoin d’aide pour manger'),('🚫','Je ne peux pas manger ça'),('🧻','Une serviette, s’il vous plaît')],
 'Déplacements':[('🏠','Je veux aller à la maison'),('🚻','Où sont les toilettes ?'),('🚌','Où est le bus ?'),('🛑','Je veux m’arrêter ici'),('♿','J’ai besoin d’un accès adapté'),('🚶','Allons plus doucement'),('📍','Je suis perdu'),('📞','Appelez mon accompagnant'),('🪑','J’ai besoin de m’asseoir'),('↩','Je veux revenir'),('🚪','Ouvrez la porte, s’il vous plaît'),('⏰','À quelle heure partons-nous ?')],
 'École':[('✏','J’ai besoin d’un crayon'),('📖','Je veux relire la consigne'),('🙋','J’ai une question'),('✅','J’ai terminé'),('❓','Je n’ai pas compris'),('🐢','J’ai besoin de plus de temps'),('🔁','Montrez-moi encore'),('🧩','Je veux essayer seul'),('🤝','Je voudrais travailler avec vous'),('☕','J’ai besoin d’une pause'),('🔇','Il y a trop de bruit'),('👀','Je ne vois pas bien')],
})
for category,extra in {
 'Essentiels':[('🤔','Je ne sais pas'),('⏱','Pas maintenant'),('👌','D’accord'),('🔁','Encore')],
 'Besoins':[('📱','Je veux mon téléphone'),('🧼','Je veux me laver'),('💡','Allumez la lumière'),('🔇','Moins de bruit, s’il vous plaît')],
 'Ressentis':[('😰','Je suis inquiet'),('😵','C’est trop pour moi'),('🤗','J’ai besoin d’être rassuré'),('💭','J’ai besoin d’être seul')],
 'Échanges':[('📝','Je vais l’écrire'),('👀','Regardez mon message'),('❔','Qui ?'),('📍','Où ?')],
 'Activités':[('🎨','Dessiner'),('🌳','Aller dehors'),('🛍','Faire des courses'),('💤','Dormir')],
}.items():VOCABULARY[category].extend(extra)

# Full, immediately usable messages: agency, consent and conversational repair
# matter as much as naming objects. No card triggers speech automatically.
VOCABULARY['Échanges'] += [('💬','Je communique avec ce tableau'),('⏳','Laissez-moi le temps de répondre'),('👂','Écoutez mon message jusqu’au bout'),('🔁','Pouvez-vous répéter ?'),('🐢','Parlez plus lentement'),('☝','Une question à la fois, s’il vous plaît'),('❓','Je n’ai pas compris votre question'),('📝','Pouvez-vous l’écrire ?'),('👀','Montrez-moi ce que vous voulez dire'),('🧩','Je vais expliquer autrement'),('🙋','Je veux ajouter quelque chose'),('✅','Vous avez bien compris')]
VOCABULARY['Choisir']=[('👍','C’est ce que je veux'),('✋','Ce n’est pas ce que je veux'),('👉','Je préfère celui-ci'),('🔁','Montrez-moi un autre choix'),('🤔','J’hésite encore'),('⏳','J’ai besoin de réfléchir'),('➕','J’en veux encore'),('🛑','Je n’en veux plus'),('↩','Je voudrais changer d’avis'),('👥','Je veux choisir avec vous'),('🙋','Je veux choisir moi-même'),('✅','Ça me convient')]
VOCABULARY['Autonomie']=[('🙋','Adressez-vous à moi directement'),('💬','Ne parlez pas à ma place'),('✋','Je ne veux pas être touché'),('🤝','Demandez-moi avant de m’aider'),('🧩','Je veux essayer seul'),('👥','J’ai besoin d’être accompagné'),('🔒','Je veux parler en privé'),('🚪','J’ai besoin d’être seul un moment'),('⏸','Je veux faire une pause'),('🛑','Je ne suis pas d’accord'),('↩','Je veux arrêter cette activité'),('❤️','Respectez mon choix, s’il vous plaît')]
VOCABULARY['Questions']=[('❔','Qu’est-ce qui se passe ?'),('👤','Qui est cette personne ?'),('📍','Où allons-nous ?'),('⏰','Quand allons-nous partir ?'),('🔎','Pourquoi ?'),('🧭','Comment fait-on ?'),('⏱','Combien de temps cela va durer ?'),('📋','Qu’est-ce qu’on fait après ?'),('🤝','Qui peut m’aider ?'),('💬','Est-ce que je peux vous parler ?'),('📝','Pouvez-vous me montrer un exemple ?'),('✅','Est-ce que j’ai bien compris ?')]

def speech_icon():
    pix=QPixmap(28,28);pix.fill(Qt.transparent);p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing);p.setPen(QPen(QColor('#64305F'),2,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
    points=[QPointF(4,11),QPointF(9,11),QPointF(15,6),QPointF(15,22),QPointF(9,17),QPointF(4,17),QPointF(4,11)]
    for left,right in zip(points,points[1:]):p.drawLine(left,right)
    p.drawArc(13,8,11,12,-60*16,120*16);p.drawArc(13,4,15,20,-60*16,120*16);p.end();return QIcon(pix)


def default_cards():
    return [dict(id=f'default-{category}-{i}',category=category,icon=icon,text=text)
            for category,items in VOCABULARY.items() for i,(icon,text) in enumerate(items)]

def validate_cards(data):
    if not isinstance(data,list) or len(data)>300:raise ValueError('Le tableau doit contenir au maximum 300 cartes.')
    result=[]
    for item in data:
        if not isinstance(item,dict):raise ValueError('Carte invalide.')
        text=item.get('text');icon=item.get('icon','💬');category=item.get('category','Mes cartes')
        if not isinstance(text,str) or not text.strip() or len(text)>200:raise ValueError('Chaque carte doit contenir un texte de 1 à 200 caractères.')
        if not isinstance(icon,str) or not 1<=len(icon)<=16 or category not in CATEGORIES:raise ValueError('Symbole ou catégorie invalide.')
        result.append(dict(text=text.strip(),icon=icon,category=category))
    return result

class CommunicationMixin:
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if getattr(self,'app_id','')=='communicator' and hasattr(self,'symbol_grid'):
            size=9 if self.height()<660 or self.width()<800 else 12
            if size!=getattr(self,'card_page_size',None):QTimer.singleShot(0,self.refresh_symbols)
    def communicator(self):
        self.setMinimumSize(720,620);self.resize(860,680)
        if not self.preferences.get('communication_board_v2'):
            QTimer.singleShot(0,lambda:(self.resize(860,680),self.behavior.ensure_visible(),self.remember('communication_board_v2',True)))
        self.layout.setContentsMargins(16,12,16,12)
        self.setStyleSheet(self.styleSheet()+"""
            QPushButton#CommunicationTile {font-size:11pt;min-height:64px;padding:0;border-radius:15px;background:#FFFFFF;border:1px solid #DCCDDD;}
            QPushButton#CommunicationTile:hover {background:#F8F1F8;border-color:#A2649B;}
            QPushButton#CommunicationTile:checked {background:#F1E5F0;border:2px solid #94418D;}
            QPushButton#QuickAnswer {min-height:29px;padding:3px 9px;border-radius:10px;font-weight:600;background:#FFFFFF;border:1px solid #DCCDDD;}
            QPushButton#CardFavorite {min-height:26px;max-height:26px;min-width:26px;max-width:26px;padding:0;border:none;background:transparent;font-size:16pt;color:#64305F;}
            QWidget#CommunicationBoard, QWidget#CommunicationTileContainer, QWidget#QuickEmotions {background:transparent;}
            QPlainTextEdit#CommunicationMessage {font-size:15pt;padding:7px;}
            QPushButton#MessageTool, QPushButton#MessageFullscreen {min-height:28px;max-height:28px;min-width:32px;padding:2px 5px;border-radius:8px;}
            QPushButton#MessageFullscreen {background:#F2D184;color:#241A2C;border:1px solid #FFE9B4;font-size:15pt;font-weight:700;} QPushButton#MessageFullscreen:hover {background:#FFE7A6;}
            QPushButton#Situation {min-height:25px;padding:3px 5px;border-radius:9px;font-size:10pt;background:#251E2C;}
            QPushButton#Situation:checked {background:#704466;border:1px solid #E3A6D9;}
            QPushButton#CompactAction {min-height:20px;padding:3px 8px;}
            QLineEdit#CardSearch {min-height:20px;padding:4px 9px;} QPushButton#CardSpeak {min-height:28px;max-height:28px;min-width:24px;max-width:24px;padding:3px;border-radius:8px;background:#49334F;} QPushButton#QuickEmotion {font-size:20pt;min-height:34px;max-height:34px;padding:1px 4px;border-radius:10px;background:#302538;}
        """)
        self.status.setText('Votre message, à votre rythme · la voix reste facultative.')
        self.message_history=[];self.reverting=False
        message_row=QHBoxLayout();message_row.setSpacing(6);self.content.addLayout(message_row)
        self.sentence=QPlainTextEdit();self.sentence.setObjectName('CommunicationMessage');self.sentence.setPlaceholderText('Écrire un message…');self.sentence.setAccessibleName('Message à montrer ou à prononcer');self.sentence.setStyleSheet('QPlainTextEdit#CommunicationMessage {font-size:19pt;font-weight:600;padding:10px;background:#FFF8FE;border:2px solid #AD6DA6;border-radius:15px;}');self.sentence.setFixedHeight(88);message_row.addWidget(self.sentence,1)
        self.sentence.textChanged.connect(self.track_message);self.last_message=''
        tools=QGridLayout();tools.setSpacing(4);message_row.addLayout(tools)
        def tool(label,name,callback,row,column):
            button=ErgoButton(label);button.setObjectName('MessageTool');button.setAccessibleName(name);button.setToolTip(name);button.clicked.connect(callback);tools.addWidget(button,row,column);return button
        self.say_button=tool('','Prononcer le message',self.say_message,0,0);self.say_button.setIcon(QIcon(str(suite_root()/'assets/communicator/speak.png')));self.say_button.setIconSize(QSize(24,24))
        self.say_button.setIcon(speech_icon());self.say_button.setText('Parler')
        self.stop_button=tool('■','Arrêter la voix',self.stop_communication,0,1)
        tool('↶','Annuler la dernière modification',self.undo_message,1,0);tool('×','Effacer le message',self.clear_message,1,1)
        self.fullscreen_button=tool('⛶','Montrer le message en grand',self.show_message,0,2);self.fullscreen_button.setObjectName('MessageFullscreen')
        self.fullscreen_button.setText('Montrer');self.fullscreen_button.setMinimumWidth(82)
        quick=QHBoxLayout();quick.setSpacing(6);self.content.addLayout(quick);self.quick_buttons={}
        for icon,text in [('👍','Oui'),('✋','Non'),('🙋','J’ai besoin d’aide'),('🛑','Stop')]:
            control=ErgoButton(icon+'  '+text);control.setObjectName('QuickAnswer');control.setAccessibleName(text);control.clicked.connect(lambda checked=False,t=text:self.select_card(dict(text=t,urgent=True)));quick.addWidget(control);self.quick_buttons[text]=control
        self.category=QComboBox(self);self.category.addItems(['Favoris']+CATEGORIES);self.category.setCurrentText('Essentiels');self.category.hide()
        self.situations=QButtonGroup(self);self.situations.setExclusive(True);self.situation_buttons={}
        navigation=QGridLayout();navigation.setSpacing(5);self.content.addLayout(navigation)
        for i,name in enumerate(['Essentiels','École','Besoins','Ressentis','Favoris','Santé','Repas','Déplacements','Échanges','Activités','Choisir','Autonomie','Questions','Mes cartes']):
            button=ErgoButton(name);button.setObjectName('Situation');button.setCheckable(True);button.setChecked(name=='Essentiels');button.clicked.connect(lambda checked=False,n=name:self.category.setCurrentText(n));self.situations.addButton(button);self.situation_buttons[name]=button;navigation.addWidget(button,i//7,i%7)
        self.cards=default_cards();self.custom_ids={}
        for key,data in self.records.all('symbol'):
            if data.get('hidden'):continue
            try:card=validate_cards([data])[0]
            except ValueError:continue
            card['id']=f'custom-{key}';self.custom_ids[card['id']]=key;self.cards.append(card)
        favorites=self.preferences.get('communication_favorites',[]);self.favorites=set(x for x in favorites if isinstance(x,str)) if isinstance(favorites,list) else set()
        self.board_widget=QWidget();self.board_widget.setMinimumHeight(292);self.board_widget.setObjectName('CommunicationBoard');self.symbol_grid=QGridLayout(self.board_widget);self.symbol_grid.setContentsMargins(0,0,0,0);self.symbol_grid.setSpacing(8);self.symbol_grid.setAlignment(Qt.AlignTop)
        self.card_page=0;self.page_category=None
        board_row=QHBoxLayout();board_row.setSpacing(8);self.content.addLayout(board_row,1);board_row.addWidget(self.board_widget,1)
        self.emotion_buttons=[]
        self.page_bar=QWidget();pages=QHBoxLayout(self.page_bar);pages.setContentsMargins(0,0,0,0)
        previous=ErgoButton('‹ Précédent');previous.clicked.connect(lambda:self.change_card_page(-1));pages.addWidget(previous)
        self.page_label=QLabel();self.page_label.setAlignment(Qt.AlignCenter);pages.addWidget(self.page_label,1)
        following=ErgoButton('Suivant ›');following.clicked.connect(lambda:self.change_card_page(1));pages.addWidget(following);self.content.addWidget(self.page_bar)
        self.category.currentTextChanged.connect(self.refresh_symbols)
        footer=QHBoxLayout();self.content.addLayout(footer)
        self.compose_button=ErgoButton('Assembler des messages');self.compose_button.setObjectName('CompactAction');self.compose_button.setCheckable(True);self.compose_button.setToolTip('Ajouter les cartes au message au lieu de le remplacer');footer.addWidget(self.compose_button)
        footer.addStretch();self.create_card_button=ErgoButton('＋ Ma carte');self.create_card_button.setObjectName('CompactAction');self.create_card_button.clicked.connect(lambda:self.card_editor());footer.addWidget(self.create_card_button)
        self.voice_name=self.preferences.get('voice_name','Femme · naturelle')
        if self.voice_name not in ('Femme · naturelle','Homme · naturelle'):self.voice_name='Femme · naturelle'
        self.refresh_symbols()

    def track_message(self):
        text=self.sentence.toPlainText()
        if not self.reverting and text!=self.last_message:
            self.message_history.append(self.last_message);self.message_history=self.message_history[-50:]
        self.last_message=text
    def undo_message(self):
        if self.message_history:
            self.reverting=True;self.sentence.setPlainText(self.message_history.pop());self.reverting=False
    def clear_message(self):self.sentence.clear()
    def select_card(self,card):
        text=card['text'];previous=self.sentence.toPlainText().strip()
        if hasattr(self,'compose_button') and self.compose_button.isChecked() and previous and not card.get('urgent'):
            text=previous+(' ' if previous[-1:] in '.!?…' else '. ')+text
        self.sentence.setPlainText(text)
        for button,visible in zip(self.card_buttons,self.visible_cards):button.setChecked(visible.get('id')==card.get('id') and 'id' in card)
        self.status.setText('Message prêt · montrez-le ou utilisez le haut-parleur.')
    def quick_emotion(self,text):
        self.sentence.setPlainText(text);self.status.setText('Message prêt · montrez-le ou utilisez le haut-parleur.')
    def say_message(self):self.speak(self.sentence.toPlainText())
    def stop_communication(self):self.speaker.cancel();self.status.setText('Voix arrêtée.')
    def show_message(self):
        text=self.sentence.toPlainText().strip()
        if not text:self.status.setText('Choisissez une carte ou écrivez un message.');return
        dialog=QDialog(self);dialog.setWindowTitle('Mon message');layout=QVBoxLayout(dialog)
        area=QScrollArea();area.setWidgetResizable(True);label=QLabel(text);label.setTextFormat(Qt.PlainText);label.setWordWrap(True);label.setAlignment(Qt.AlignCenter);label.setStyleSheet('font-size:36pt;padding:24px;');area.setWidget(label);layout.addWidget(area)
        close=ErgoButton('Revenir');close.clicked.connect(dialog.accept);layout.addWidget(close);dialog.setModal(True);dialog.showMaximized();self.message_dialog=dialog
    def refresh_symbols(self,*_):
        while self.symbol_grid.count():
            item=self.symbol_grid.takeAt(0)
            if item.widget():item.widget().deleteLater()
        category=self.category.currentText()
        if category!=self.page_category:self.card_page=0;self.page_category=category
        cards=[c for c in self.cards if (c['id'] in self.favorites if category=='Favoris' else c['category']==category)]
        self.card_page_size=9 if self.height()<660 or self.width()<800 else 12
        self.board_widget.setMinimumHeight(220 if self.card_page_size==9 else 292)
        page_count=max(1,(len(cards)+self.card_page_size-1)//self.card_page_size);self.card_page=min(self.card_page,page_count-1)
        self.page_bar.setVisible(page_count>1);self.page_label.setText(f'{self.card_page+1} / {page_count}')
        cards=cards[self.card_page*self.card_page_size:(self.card_page+1)*self.card_page_size]
        if category in self.situation_buttons:self.situation_buttons[category].setChecked(True)
        self.visible_cards=cards;self.card_buttons=[];self.card_speak_buttons=[]
        for i,card in enumerate(cards):
            tile=QWidget();tile.setObjectName('CommunicationTileContainer');row=QHBoxLayout(tile);row.setContentsMargins(0,0,0,0);row.setSpacing(3)
            button=ErgoButton('');button.setObjectName('CommunicationTile');button.setMinimumHeight(64);button.setCheckable(True);button.setAccessibleName(card['text'])
            face=QVBoxLayout(button);face.setContentsMargins(7,5,7,5);face.setSpacing(2)
            audio=ErgoButton('');audio.setObjectName('CardSpeak');audio.setIcon(speech_icon());audio.setIconSize(QSize(20,20));audio.setAccessibleName('Écouter : '+card['text']);audio.setToolTip('Écouter cette carte');audio.clicked.connect(lambda checked=False,text=card['text']:self.speak(text));self.card_speak_buttons.append(audio)
            icon_row=QHBoxLayout();icon_row.setContentsMargins(0,0,0,0);face.addLayout(icon_row)
            star=ErgoButton('★' if card['id'] in self.favorites else '☆');star.setObjectName('CardFavorite');star.setAccessibleName('Favori : '+card['text']);star.setToolTip('Retirer des favoris' if card['id'] in self.favorites else 'Garder dans mes favoris');star.clicked.connect(lambda checked=False,k=card['id']:self.toggle_favorite(k,k not in self.favorites));icon_row.addWidget(star)
            symbol=QLabel(card['icon']);symbol.setTextFormat(Qt.PlainText);symbol.setAlignment(Qt.AlignCenter);symbol.setStyleSheet('font-size:21pt;background:transparent;');symbol.setAttribute(Qt.WA_TransparentForMouseEvents);icon_row.addStretch();icon_row.addWidget(symbol);icon_row.addStretch();icon_row.addWidget(audio)
            caption=QLabel(card['text']);caption.setTextFormat(Qt.PlainText);caption.setWordWrap(True);caption.setAlignment(Qt.AlignCenter);caption.setStyleSheet('background:transparent;');caption.setAttribute(Qt.WA_TransparentForMouseEvents);face.addWidget(caption)
            button.clicked.connect(lambda checked=False,c=card:self.select_card(c));row.addWidget(button,1);self.card_buttons.append(button)
            self.symbol_grid.addWidget(tile,i//3,i%3)
        if not cards:
            hint=QLabel('Ajoutez vos favoris avec ☆.' if category=='Favoris' else 'Personnaliser → Mes cartes pour ajouter un message.');hint.setWordWrap(True);self.symbol_grid.addWidget(hint,0,0,1,2)
        self.symbol_grid.setColumnStretch(0,1);self.symbol_grid.setColumnStretch(1,1);self.symbol_grid.setColumnStretch(2,1)
    def change_card_page(self,step):
        self.card_page=max(0,self.card_page+step);self.refresh_symbols()
    def toggle_favorite(self,key,enabled):
        if enabled:self.favorites.add(key)
        else:self.favorites.discard(key)
        self.remember('communication_favorites',sorted(self.favorites))
        QTimer.singleShot(0,self.refresh_symbols)

    def card_editor(self,card=None):
        dialog=QDialog(self);dialog.setWindowTitle('Modifier ma carte' if card else 'Nouvelle carte');layout=QVBoxLayout(dialog);form=QFormLayout();layout.addLayout(form)
        text=QLineEdit(card['text'] if card else '');text.setMaxLength(200);form.addRow('Message',text)
        icon=QLineEdit(card['icon'] if card else '💬');icon.setMaxLength(16);form.addRow('Symbole',icon)
        category=QComboBox();category.addItems(CATEGORIES);category.setCurrentText(card['category'] if card else 'Mes cartes');form.addRow('Catégorie',category)
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);buttons.button(QDialogButtonBox.Save).setText('Enregistrer');buttons.button(QDialogButtonBox.Cancel).setText('Annuler');buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        if dialog.exec()!=QDialog.Accepted:return
        try:data=validate_cards([dict(text=text.text(),icon=icon.text(),category=category.currentText())])[0]
        except ValueError as error:self.error(str(error));return
        if card:
            self.records.update(self.custom_ids[card['id']],'symbol',data);card.update(data)
        else:
            key=self.records.add('symbol',data);data['id']=f'custom-{key}';self.custom_ids[data['id']]=key;self.cards.append(data)
        self.refresh_symbols()
    def manage_cards(self):
        dialog=QDialog(self);dialog.setWindowTitle('Mes cartes');dialog.resize(460,420);layout=QVBoxLayout(dialog);listing=QListWidget();layout.addWidget(listing)
        def refresh():
            listing.clear();dialog.cards=[c for c in self.cards if c['id'] in self.custom_ids]
            for card in dialog.cards:listing.addItem(card['icon']+' '+card['text'])
        def selected():return dialog.cards[listing.currentRow()] if 0<=listing.currentRow()<len(dialog.cards) else None
        def add():self.card_editor();refresh()
        def edit():
            card=selected()
            if card:self.card_editor(card);refresh()
        def remove():
            card=selected()
            if card and QMessageBox.question(dialog,'Retirer la carte','Retirer « '+card['text']+' » ?')==QMessageBox.Yes:
                self.records.update(self.custom_ids[card['id']],'symbol',dict(card,hidden=True));self.cards.remove(card);self.refresh_symbols();refresh()
        row=QHBoxLayout();layout.addLayout(row)
        for label,callback in [('Ajouter',add),('Modifier',edit),('Retirer',remove),('Fermer',dialog.accept)]:
            button=ErgoButton(label);button.clicked.connect(callback);row.addWidget(button)
        refresh();dialog.exec()
    def export_cards(self):
        path,_=QFileDialog.getSaveFileName(self,'Exporter mes cartes','','Tableau (*.json)')
        if path:
            try:atomic_text(path,json.dumps(dict(version=1,cards=validate_cards([c for c in self.cards if c['id'] in self.custom_ids])),ensure_ascii=False,indent=2));self.status.setText('Cartes exportées.')
            except (ValueError,OSError) as error:self.error(str(error))
    def import_cards(self):
        path,_=QFileDialog.getOpenFileName(self,'Importer des cartes','','Tableau (*.json)')
        if not path:return
        try:
            from pathlib import Path
            if Path(path).stat().st_size>1024*1024:raise ValueError('Fichier trop volumineux.')
            data=json.loads(Path(path).read_text(encoding='utf-8'))
            if not isinstance(data,dict) or data.get('version')!=1:raise ValueError('Format de tableau non reconnu.')
            cards=validate_cards(data.get('cards'))
            if len(self.custom_ids)+len(cards)>300:raise ValueError('Limite de 300 cartes personnelles atteinte.')
            if QMessageBox.question(self,'Ajouter les cartes',f'Ajouter {len(cards)} cartes sans remplacer les cartes existantes ?')!=QMessageBox.Yes:return
            for card in cards:
                key=self.records.add('symbol',card);card['id']=f'custom-{key}';self.custom_ids[card['id']]=key;self.cards.append(card)
            self.refresh_symbols();self.status.setText('Cartes ajoutées.')
        except (ValueError,OSError,TypeError) as error:self.error(str(error))
