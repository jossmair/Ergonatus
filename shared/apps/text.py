from pathlib import Path
import uuid
import urllib.request
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QFont,QTextDocument,QTextCursor,QColor,QTextCharFormat
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import (QLabel,QComboBox,QLineEdit,QFileDialog,QMessageBox,QTextEdit,QSpinBox,QHBoxLayout,QPlainTextEdit,QFrame,QVBoxLayout,QSlider)
from shared.ui.components import ErgoOptions
from shared.apps.base import ApplicationWindow
from shared.documents import read_text,save_docx
from shared.domain import atomic_text

class TextApplication(ApplicationWindow):
    def __init__(self,app_id):
        super().__init__(app_id);self.target=None;self.transaction=None;self.job_id=None;self.generated_input=None
        if app_id=='ecrinator':self.build_writer();return
        if app_id=='scanator':self.build_scan();return
        self.input=self.editor('Texte original ou demande')
        if app_id=='lector':
            self.options=QFrame();self.options.setObjectName('Card');options=QVBoxLayout(self.options);options.setContentsMargins(14,12,14,12);options.setSpacing(10)
            self.setMinimumSize(440,360);self.resize(520,420)
            if not self.preferences.get('compact_lector_v1'):
                QTimer.singleShot(0,lambda:(self.resize(520,420),self.behavior.ensure_visible(),self.remember('compact_lector_v1',True)))
            self.layout.setContentsMargins(16,12,16,12);self.layout.setSpacing(8);self.content.setSpacing(8)
            self.input.setPlaceholderText('Collez votre texte ici…');self.input.setAccessibleName('Texte à lire')
            self.setStyleSheet(self.styleSheet()+"QPushButton {min-height:22px;padding:4px 10px;} QComboBox {min-height:22px;} QSlider {background:transparent;min-height:30px;}")
        else:self.options=ErgoOptions();options=self.options.content
        documents=QHBoxLayout();options.addLayout(documents)
        self.button('Ouvrir un document',self.open_text,documents)
        self.button('Copier le texte original',lambda:self.copy(self.input),documents)
        if app_id=='lector':
            from shared.reading_selection import SelectionPicker
            self.selection_picker=SelectionPicker(self);self.selection_picker.selected.connect(self.read_lector_selection);self.selection_picker.cancelled.connect(self.stop_lector)
            self.lector_active=False;self.lector_generation=0
            from shared.reading_capture import ReadingCapture
            self.lector_capture=ReadingCapture(self);self.capture_pending=False
            from shared.ui.reading_busy import ReadingBusy
            self.busy_indicator=ReadingBusy()
            self.orb.doubleActivated.connect(self.lector_capture.start)
            self.speech_segment.connect(lambda text:self.busy_indicator.finish() if text else None)
            self.orb.setAccessibleDescription('Clic gauche : lire une sélection. Double-clic : capturer une zone et lire son texte. Clic droit : menu. Glisser pour déplacer.')
            self.speech_segment.connect(self.highlight_sentence)
            self.voice_name=self.preferences.get('voice_name','');self.speech_rate=self.preferences.get('speech_rate',0)
            if not isinstance(self.voice_name,str):self.voice_name=''
            if type(self.speech_rate) is not int or not -5<=self.speech_rate<=5:self.speech_rate=0
            if not self.preferences.get('gentle_reading_migrated'):
                self.speech_rate=min(self.speech_rate,-1);self.remember('speech_rate',self.speech_rate);self.remember('gentle_reading_migrated',True)
            controls=QHBoxLayout();options.addLayout(controls)
            controls.addWidget(QLabel('Voix'))
            self.voice_choice=QComboBox();self.voice_choice.setAccessibleName('Voix de lecture')
            self.voice_choice.addItem('Femme','Femme · naturelle');self.voice_choice.addItem('Homme','Homme · naturelle');controls.addWidget(self.voice_choice,1)
            self.voice_choice.setCurrentIndex(1 if self.voice_name=='Homme · naturelle' else 0)
            self.voice_name=self.voice_choice.currentData();self.remember('voice_name',self.voice_name)
            def voice_changed(_):
                if getattr(self,'speaking',False):self.stop_lector()
                self.voice_name=self.voice_choice.currentData();self.remember('voice_name',self.voice_name);self.warm_lector_voice()
                self.tray.setContextMenu(self.create_orb_menu())
            self.voice_choice.currentIndexChanged.connect(voice_changed)
            speed=QHBoxLayout();options.addLayout(speed);speed.addWidget(QLabel('Vitesse'))
            speed.addWidget(QLabel('Douce'))
            self.rate_slider=QSlider(Qt.Horizontal);self.rate_slider.setRange(-5,5);self.rate_slider.setValue(self.speech_rate);self.rate_slider.setAccessibleName('Vitesse de lecture')
            speed.addWidget(self.rate_slider,1);speed.addWidget(QLabel('Rapide'))
            def rate_changed(value):self.speech_rate=value;self.remember('speech_rate',value)
            self.rate_slider.valueChanged.connect(rate_changed)
            self.warm_lector_voice();self.tray.setContextMenu(self.create_orb_menu())
            row=self.row()
            self.button('Lire',lambda:self.lector_speak(self.input.toPlainText()),row);self.button('Arrêter',self.stop_lector,row)
            self.status.setText('Orb : clic gauche, lire une sélection · double-clic, lire une zone de l’écran · clic droit, menu.')
        else:
            self.output=self.editor('Proposition à relire et modifier')
            self.language=QComboBox();self.language.addItems(['Français','English','Español','Deutsch','Italiano','Português','العربية','Українська']);self.language.setAccessibleName('Langue cible')
            if app_id=='traductor':
                language=self.preferences.get('language','English')
                self.language.setCurrentText(language if isinstance(language,str) and self.language.findText(language)>=0 else 'English')
                self.language.currentTextChanged.connect(lambda value:self.remember('language',value))
                self.content.addWidget(self.language)
            self.action=QComboBox();self.action.addItems(['Corriger','Reformuler','Résumer','Rédiger'])
            if app_id not in ('corrector','traductor'):self.content.addWidget(self.action)
            row=self.row();self.generate=self.button('Traduire' if app_id=='traductor' else 'Corriger',self.generate_text,row)
            from shared.ui.theme import accent_button_style
            self.generate.setStyleSheet(accent_button_style(self.theme['accent']))
            self.button('Annuler',self.cancel,row);self.button('Copier le résultat',lambda:self.copy(self.output),row)
            self.button('Écouter le résultat',lambda:self.speak(self.output.toPlainText()),options)
            if app_id=='corrector':
                row=self.row();self.replace_button=self.button('Remplacer la sélection après validation',self.replace_selection,row);self.replace_button.setEnabled(False)
                self.input.textChanged.connect(lambda:self.replace_button.setEnabled(False))
                self.button('Restaurer l’original',self.restore_selection,row)
                self.content.addWidget(QLabel('Le remplacement est disponible si la sélection peut être vérifiée. Sinon, utilisez Copier.'))
            else:self.button('Enregistrer le résultat',self.save_result,options)
        self.content.addWidget(self.options)

    def activate(self,*args):
        if self.app_id=='lector':
            if self.lector_active or getattr(self,'speaking',False):self.stop_lector()
            else:
                self.lector_active=True;self.lector_generation+=1;self.hide();self.selection_picker.start();self.state('Activée');self.orb.setToolTip('Lector · sélectionnez un texte · Orb ou Échap pour annuler.')
            return
        if self.app_id=='scanator':
            if not self.ocr_busy and not self.capture_pending:self.capture_region(direct=True)
            return
        if hasattr(self,'input') and self.app_id in ('corrector','traductor','lector'):
            try:
                from shared.text_target import TextTarget
                import win32gui,win32process,os
                if win32process.GetWindowThreadProcessId(win32gui.GetForegroundWindow())[1]!=os.getpid():
                    self.target_api=TextTarget();self.target=self.target_api.capture();self.input.setPlainText(self.target.selected)
                    self.status.setText('Sélection capturée sans modifier le presse-papiers.')
            except Exception as error:
                self.target=None
                from shared.selection_validation import read_uia_selection
                expected=win32gui.GetForegroundWindow()
                def captured(text):
                    self.input.setPlainText(text);self.status.setText('Sélection récupérée. Pour ce champ, copiez le résultat puis collez-le vous-même.');ApplicationWindow.activate(self)
                job=self.run(lambda:read_uia_selection(expected),captured)
                job.signals.error.connect(lambda _:ApplicationWindow.activate(self))
                return
        super().activate(*args)

    def orb_menu(self,point):
        super().orb_menu(point)

    def open_main_window(self):
        if self.app_id=='lector':self.open_lector_window()
        else:super().open_main_window()

    def open_lector_window(self,*_):
        self.stop_lector();ApplicationWindow.activate(self)

    def error(self,text):
        if getattr(self,'busy_indicator',None):self.busy_indicator.finish()
        super().error(text)

    def stop_lector(self):
        self.lector_active=False;self.lector_generation+=1;self.selection_picker.stop();self.speaker.cancel();self.speech_segment.emit('');self.state('Activée');self.status.setText('Lecture arrêtée.');self.orb.setToolTip('Lector · lecture arrêtée · cliquer pour sélectionner un texte.')
        self.lector_capture.cancel()
        self.busy_indicator.finish()

    def warm_lector_voice(self):
        import os
        if os.environ.get('ERGONATUS_BACKGROUND_START')=='1':return
        from ergoai.voice_models import VOICES
        if self.voice_name in VOICES:
            from shared.jobs import background
            from shared.neural_speech import warm
            background(self,lambda label=self.voice_name:warm(label),lambda _:None)

    def read_lector_selection(self,expected):
        if not self.lector_active:return
        from shared.reading_selection import read_selection
        from shared.jobs import background
        self.selection_picker.stop();generation=self.lector_generation;point=self.selection_picker.release_point
        self.busy_indicator.begin(self.orb.animations)
        def selected(text):
            if self.closing or not self.lector_active or generation!=self.lector_generation:return
            if not text.strip():failed('Sélectionnez un passage de texte.');return
            self.input.setPlainText(text);self.lector_speak(text)
        def failed(message):
            if self.closing or not self.lector_active or generation!=self.lector_generation:return
            self.busy_indicator.finish()
            self.status.setText('Sélectionnez un texte accessible ou ouvrez Lector pour le coller.');self.state('Attention');self.orb.setToolTip(str(message)+' · Orb pour annuler.');self.selection_picker.start()
        job=background(self,lambda:read_selection(expected,point=point),selected);job.signals.error.connect(failed)

    def lector_speak(self,text):
        if not text.strip():self.error('Sélectionnez ou saisissez un texte.');return
        if getattr(self,'speaking',False):self.status.setText('La lecture précédente se termine. Réessayez dans un instant.');return
        self.selection_picker.stop();self.lector_active=True;self.lector_generation+=1;generation=self.lector_generation
        self.busy_indicator.begin(self.orb.animations)
        job=self.speak(text)
        # Background completion is signalled by the shared speaker's worker.
        def finished():
            if not self.closing and generation==self.lector_generation:
                self.busy_indicator.finish()
                self.lector_active=False
                if self.orb.state!='Erreur':self.orb.setToolTip('Lector · lecture terminée · cliquer pour sélectionner un autre texte.')
        if job:job.signals.finished.connect(finished)

    def open_text(self):
        path,_=QFileDialog.getOpenFileName(self,'Ouvrir un document','','Documents (*.txt *.md *.pdf *.docx)')
        if path:self.run(lambda:read_text(path),lambda text:self.input.setPlainText(text))
    def save_result(self):
        path,_=QFileDialog.getSaveFileName(self,'Enregistrer le résultat','','Texte (*.txt)')
        if path:
            try:atomic_text(path,self.output.toPlainText());self.status.setText('Résultat enregistré.')
            except OSError as error:self.error(str(error))
    def generate_text(self):
        if self.job_id:self.error('Un traitement est déjà en cours.');return
        text=self.input.toPlainText().strip()
        source=self.input.toPlainText()
        if hasattr(self,'replace_button'):self.replace_button.setEnabled(False)
        if not text:self.error('Saisissez ou ouvrez un texte.');return
        self.job_id=uuid.uuid4().hex;identifier=self.job_id;self.generate.setEnabled(False)
        op='translate' if self.app_id=='traductor' else 'correct' if self.app_id=='corrector' else ['correct','rewrite','summarize','compose'][self.action.currentIndex()]
        language=self.language.currentText()
        from ergoai.client import infer
        # Documents are processed paragraph by paragraph to respect the real model context.
        parts=[];current=''
        for paragraph in text.splitlines():
            if len(current)+len(paragraph)>1800 and current:parts.append(current);current=''
            if len(paragraph)>1800:
                if current:parts.append(current);current=''
                parts.extend(paragraph[i:i+1800] for i in range(0,len(paragraph),1800))
            else:current+=paragraph+'\n'
        if current:parts.append(current)
        def work():
            output=[]
            for index,part in enumerate(parts):
                if self.job_id!=identifier:raise ValueError('Traitement annulé.')
                self.ai_current=identifier+'-'+str(index)
                result=infer(op,part,self.ai_current,language);output.append(result['text'])
            return '\n\n'.join(output)
        def proposal(result):
            if self.app_id=='corrector':
                prefix=source[:len(source)-len(source.lstrip())];suffix=source[len(source.rstrip()):]
                result=prefix+result.strip()+suffix
            self.output.setPlainText(result);self.generated_input=source
            if hasattr(self,'replace_button'):self.replace_button.setEnabled(self.target is not None and self.target.selected==source and self.input.toPlainText()==source)
        job=self.run(work,proposal)
        def finished():self.job_id=None;self.generate.setEnabled(True)
        job.signals.finished.connect(finished)
    def cancel(self):
        if self.job_id:
            from ergoai.client import cancel
            identifier=self.job_id;self.job_id=None
            # cancel requests are short but still run off the GUI thread.
            from shared.jobs import background
            background(self,lambda key=getattr(self,'ai_current',identifier+'-0'):cancel(key),lambda _:None)
    def cleanup(self):
        if self.app_id=='ecrinator':self.draft()
        if self.app_id=='lector':
            self.selection_picker.stop();self.lector_capture.cancel();self.busy_indicator.finish();self.busy_indicator.close()
    def replace_selection(self):
        if self.target is None:self.error('Aucune sélection protégée. Sélectionnez un passage puis cliquez sur l’Orb.');return
        if self.generated_input!=self.input.toPlainText() or self.target.selected!=self.generated_input:self.error('Le texte ou la sélection a changé. Recommencez la correction.');return
        text=self.output.toPlainText()
        if not text:self.error('Aucun résultat à insérer.');return
        if QMessageBox.question(self,'Valider le remplacement','Remplacer uniquement la sélection mémorisée par le texte affiché ?')!=QMessageBox.Yes:return
        try:
            wanted=self.target_api.replace(self.target,text);self.transaction=(self.target,wanted);self.target=None
            self.status.setText('Sélection remplacée. Restauration disponible tant que la cible reste inchangée.')
        except Exception as error:self.error(str(error))
    def restore_selection(self):
        if not self.transaction:self.error('Aucun remplacement à restaurer.');return
        try:self.target_api.restore(*self.transaction);self.transaction=None;self.status.setText('Original restauré.')
        except Exception as error:self.error(str(error))
    def web_page(self):
        url=self.url.text().strip()
        if not url.startswith('https://'):self.error('Entrez une adresse HTTPS.');return
        def load():
            with urllib.request.urlopen(url,timeout=15) as response:
                data=response.read(5*1024**2+1)
                if len(data)>5*1024**2:raise ValueError('Page trop volumineuse.')
                return data.decode(response.headers.get_content_charset() or 'utf-8',errors='replace')
        def show(markup):
            document=QTextDocument();document.setHtml(markup);self.input.setPlainText(document.toPlainText())
        self.run(load,show)

    def highlight_sentence(self,sentence):
        if not sentence:self.input.setExtraSelections([]);return
        cursor=self.input.document().find(sentence)
        if not cursor.isNull():
            item=QTextEdit.ExtraSelection();item.cursor=cursor;item.format.setBackground(QColor('#F4E29A'));item.format.setForeground(QColor('#182530'))
            self.input.setExtraSelections([item]);self.input.setTextCursor(cursor);self.input.ensureCursorVisible()

    def build_writer(self):
        from PySide6.QtGui import QFontDatabase
        from shared.catalog import suite_root
        identifier=QFontDatabase.addApplicationFont(str(suite_root()/'assets/fonts/OpenDyslexic-Regular.otf'))
        families=QFontDatabase.applicationFontFamilies(identifier) if identifier>=0 else []
        self.dyslexic_family=families[0] if families else 'OpenDyslexic'
        row=self.row();self.subject=QLineEdit();self.subject.setPlaceholderText('Matière · nom · date');row.addWidget(self.subject,1)
        self.fonts=QComboBox();self.fonts.addItems(['Arial','Cursive','OpenDyslexic']);row.addWidget(self.fonts)
        self.fonts.currentTextChanged.connect(self.set_font)
        self.input=QTextEdit();self.input.setAccessibleName('Document');self.content.addWidget(self.input,1);self.set_font('Arial')
        row=self.row()
        for label,format_name in [('Gras','bold'),('Italique','italic'),('Souligner','underline')]:self.button(label,lambda checked=False,kind=format_name:self.format_text(kind),row)
        self.button('Mathématiques',self.math_palette,row)
        row=self.row();self.button('Ouvrir',self.open_writer,row);self.button('Enregistrer DOCX',self.export_docx,row);self.button('Exporter PDF',self.export_pdf,row)
        self.autosave_timer=__import__('PySide6.QtCore',fromlist=['QTimer']).QTimer(self);self.autosave_timer.setInterval(30000)
        self.autosave_timer.timeout.connect(self.draft);self.autosave_timer.start()
        drafts=self.records.all('draft')
        if drafts:self.input.setHtml(drafts[-1][1]['html']);self.subject.setText(drafts[-1][1].get('subject',''))
    def set_font(self,name):
        from PySide6.QtGui import QFontDatabase
        actual=name
        if name=='OpenDyslexic':actual=self.dyslexic_family
        if name=='Cursive':actual='Segoe Print'
        if actual not in QFontDatabase.families():self.status.setText(name+' non installée ; Arial utilisée.');actual='Arial'
        self.input.setCurrentFont(QFont(actual,16))
    def format_text(self,kind):
        cursor=self.input.textCursor();fmt=QTextCharFormat()
        if kind=='bold':fmt.setFontWeight(QFont.Normal if cursor.charFormat().fontWeight()==QFont.Bold else QFont.Bold)
        elif kind=='italic':fmt.setFontItalic(not cursor.charFormat().fontItalic())
        else:fmt.setFontUnderline(not cursor.charFormat().fontUnderline())
        cursor.mergeCharFormat(fmt)
    def math_palette(self):
        from PySide6.QtWidgets import QInputDialog
        symbol,ok=QInputDialog.getItem(self,'Mathématiques','Insérer un symbole',['+','−','×','÷','=','≠','≤','≥','²','³','√','π','½','¼','¾'],0,False)
        if ok:self.input.insertPlainText(symbol)
    def draft(self):
        values=self.records.all('draft');data={'html':self.input.toHtml(),'subject':self.subject.text()}
        if values:self.records.update(values[0][0],'draft',data)
        else:self.records.add('draft',data)
    def open_writer(self):
        path,_=QFileDialog.getOpenFileName(self,'Ouvrir','','Documents (*.txt *.html *.docx)')
        if not path:return
        try:
            if Path(path).suffix.lower()=='.html':self.input.setHtml(Path(path).read_text(encoding='utf-8'))
            else:self.input.setPlainText(read_text(path))
        except Exception as error:self.error(str(error))
    def export_docx(self):
        path,_=QFileDialog.getSaveFileName(self,'Enregistrer un DOCX','','Word (*.docx)')
        if path:
            try:
                from shared.documents import save_rich_docx
                save_rich_docx(path,self.input.document(),self.subject.text());self.status.setText('DOCX enregistré avec sa mise en forme.')
            except Exception as error:self.error(str(error))
    def export_pdf(self):
        path,_=QFileDialog.getSaveFileName(self,'Exporter en PDF','','PDF (*.pdf)')
        if path:
            printer=QPrinter(QPrinter.HighResolution);printer.setOutputFormat(QPrinter.PdfFormat);printer.setOutputFileName(path);self.input.document().print_(printer);self.status.setText('PDF exporté.')

    def build_scan(self):
        self.setMinimumSize(560,440);self.resize(640,520)
        self.image=None;self.image_path=None;self.ocr_original='';self.ocr_formatted='';self.ocr_busy=False;self.capture_pending=False;self.scan_auto_copy=False
        self.status.setText('Ouvrez une image ou capturez une zone pour lire son texte.')
        def compact(text,callback,layout):
            button=self.button(text,callback,layout);button.setObjectName('CompactAction');button.setFixedHeight(34)
            from PySide6.QtWidgets import QSizePolicy
            button.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
            return button
        row=self.row();self.scan_open=compact('Ouvrir une image',self.open_image,row);self.scan_capture=compact('Capturer une zone',self.capture_region,row)
        self.preview_button=compact('Voir l’image',self.toggle_image_preview,row);self.preview_button.setCheckable(True);self.preview_button.setEnabled(False);row.addStretch()
        self.image_label=QLabel();self.image_label.setAlignment(Qt.AlignCenter);self.image_label.setMaximumHeight(100);self.content.addWidget(self.image_label);self.image_label.hide()
        row=self.row();row.addWidget(QLabel('Mise en page'))
        self.scan_layout=QComboBox();self.scan_layout.setAccessibleName('Mise en page du texte reconnu')
        for label,key in [('Paragraphes','paragraphs'),('Lignes d’origine','lines'),('Colonnes simples','columns')]:self.scan_layout.addItem(label,key)
        self.scan_layout.setCurrentIndex(max(0,self.scan_layout.findData(self.preferences.get('scan_layout','paragraphs'))))
        row.addWidget(self.scan_layout);row.addStretch()
        self.input=self.editor('Texte reconnu · modifiable')
        self.scan_layout.currentIndexChanged.connect(self.apply_scan_layout)
        row=self.row();self.scan_retry=compact('Relire l’image',self.ocr,row);self.scan_retry.setEnabled(False)
        row.addStretch();self.scan_copy=compact('Copier le texte',self.copy_scan_text,row);self.scan_copy.setEnabled(False)
        from shared.ui.theme import accent_button_style
        self.scan_copy.setStyleSheet(accent_button_style(self.theme['accent']))
        self.input.textChanged.connect(lambda:self.scan_copy.setEnabled(bool(self.input.toPlainText().strip())))

    def toggle_image_preview(self):
        visible=self.preview_button.isChecked();self.image_label.setVisible(visible)
        self.preview_button.setText('Masquer l’image' if visible else 'Voir l’image')

    def apply_scan_layout(self,*_):
        from shared.ocr import format_text
        current=self.input.toPlainText()
        if current!=self.ocr_formatted:self.ocr_original=current
        mode=self.scan_layout.currentData();formatted=format_text(self.ocr_original,mode)
        self.remember('scan_layout',mode)
        if formatted!=current:
            cursor=self.input.textCursor();cursor.beginEditBlock();cursor.select(QTextCursor.Document);cursor.insertText(formatted);cursor.endEditBlock()
        self.ocr_formatted=formatted
        self.input.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap if mode=='columns' else QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.input.setFont(QFont('Consolas' if mode=='columns' else 'Segoe UI',10))

    def scan_recognized(self,text):
        self.ocr_original=text;self.ocr_formatted=self.input.toPlainText();self.apply_scan_layout()
        self.status.setText('Texte prêt · vous pouvez le modifier puis le copier.')
        if self.scan_auto_copy:
            self.scan_auto_copy=False
            if not self.input.toPlainText().strip():self.state('Attention');self.status.setText('Aucun texte reconnu. Le presse-papiers est conservé.');self.orb.setToolTip('Aucun texte reconnu · clic droit pour ouvrir Scanator.')
            else:self.copy_scan_text()

    def write_scan_clipboard(self,text,html):
        from PySide6.QtCore import QMimeData
        from PySide6.QtWidgets import QApplication
        mime=QMimeData();mime.setText(text);mime.setHtml(html);QApplication.clipboard().setMimeData(mime)

    def copy_scan_text(self):
        from shared.ocr import clipboard_html
        text=self.input.toPlainText()
        if not text.strip():return
        self.write_scan_clipboard(text,clipboard_html(text,self.scan_layout.currentData()))
        self.status.setText('Texte mis en page et copié · prêt à coller.')
        self.state('Action réussie');self.orb.setToolTip(self.theme['name']+' · texte copié · prêt à coller. Clic droit pour ouvrir.')
    def open_image(self):
        path,_=QFileDialog.getOpenFileName(self,'Ouvrir une image','','Images (*.png *.jpg *.jpeg *.bmp *.tif *.webp)')
        if path:
            from PySide6.QtGui import QPixmap
            image=QPixmap(path)
            if image.isNull():self.error('Image illisible.');return
            self.set_image(image);self.image_path=path;self.ocr()
    def set_image(self,image):
        self.image=image;self.image_label.setPixmap(image.scaled(500,100,Qt.KeepAspectRatio,Qt.SmoothTransformation));self.preview_button.setEnabled(True);self.scan_retry.setEnabled(True);self.status.setText('Image prête.')
    def capture_region(self,checked=False,direct=False):
        if self.capture_pending or self.ocr_busy:return
        from shared.apps.overlays import CaptureOverlay
        self.capture_pending=True;self.capture_return_window=self.isVisible() and not direct;self.capture_return_orb=self.orb.isVisible()
        self.scan_auto_copy=self.app_id=='scanator'
        self.hide();self.orb.hide()
        from PySide6.QtCore import QTimer
        def capture():
            if self.closing:return
            try:
                self.capture_overlay=CaptureOverlay();self.capture_overlay.captured.connect(self.capture_done);self.capture_overlay.cancelled.connect(self.capture_cancelled);self.capture_overlay.show()
            except Exception as error:
                self.scan_auto_copy=False;self.restore_after_capture();self.error('Capture indisponible : '+str(error))
        QTimer.singleShot(250,capture)
    def restore_after_capture(self):
        self.capture_pending=False
        if getattr(self,'capture_overlay',None) is not None:self.capture_overlay.deleteLater()
        if self.capture_return_window:self.show()
        if self.capture_return_orb:self.orb.show()
    def capture_cancelled(self):
        self.scan_auto_copy=False;self.restore_after_capture();self.state('Activée')
    def capture_done(self,image):self.set_image(image);self.image_path=None;self.restore_after_capture();self.ocr()
    def ocr(self):
        if self.ocr_busy:return
        if self.image is None:self.error('Ouvrez ou capturez une image.');return
        from shared.ocr import recognize
        from shared.domain import app_data
        path=app_data(self.app_id)/('ocr-'+uuid.uuid4().hex+'.png');self.image.save(str(path))
        def work():
            try:return recognize(path)
            finally:path.unlink(missing_ok=True)
        self.ocr_busy=True
        for button in (self.scan_open,self.scan_capture,self.scan_retry):button.setEnabled(False)
        job=self.run(work,self.scan_recognized)
        def finished():
            self.ocr_busy=False
            if not self.closing:
                for button in (self.scan_open,self.scan_capture,self.scan_retry):button.setEnabled(True)
        job.signals.finished.connect(finished)
        def failed(message):
            self.scan_auto_copy=False;self.orb.setToolTip(self.theme['name']+' · '+str(message)[:250]+' · clic droit pour ouvrir.')
        job.signals.error.connect(failed)
