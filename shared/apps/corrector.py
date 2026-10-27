"""Compact Corrector: voluntary selection, local correction and guarded replacement."""
import threading
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QColor,QTextCharFormat,QTextCursor
from PySide6.QtWidgets import QLabel,QTextEdit
from shared.apps.base import ApplicationWindow
from shared.jobs import background

class CorrectorWindow(ApplicationWindow):
    def __init__(self):
        super().__init__('corrector')
        self.setMinimumSize(480,440);self.resize(640,620)
        self.layout.setContentsMargins(16,12,16,12);self.content.setSpacing(6)
        self.setStyleSheet(self.styleSheet()+"QPushButton {min-height:22px;padding:4px 10px;} QPlainTextEdit {font-size:11pt;} QLabel#Section {color:#B0D8CA;font-size:10pt;}")
        if not self.preferences.get('corrector_sms_v1'):
            QTimer.singleShot(0,lambda:(self.resize(640,620),self.behavior.ensure_visible(),self.remember('corrector_sms_v1',True)))
        for label,name in [('Texte original','input'),('Texte corrigé','output')]:
            title=QLabel(label);title.setObjectName('Section');self.content.addWidget(title)
            setattr(self,name,self.editor('Collez votre texte ici…' if name=='input' else 'La correction apparaîtra ici.'))
        self.review_label=QLabel();self.review_label.setWordWrap(True);self.review_label.setStyleSheet('color:#F2D184;font-size:10pt;');self.review_label.hide();self.content.addWidget(self.review_label)
        row=self.row();self.correct_button=self.button('Corriger',self.correct_manual,row)
        self.button('Copier',lambda:self.copy(self.output),row)
        self.restore_button=self.button('↶ Restaurer',self.restore_original,row);self.restore_button.setEnabled(False)
        self.button('Annuler',self.cancel_correction,row)
        self.selection_button=self.button('Sélectionner un texte',self.activate,row)
        for label in self.findChildren(QLabel,'Section'):label.hide()
        from shared.ui.conversation import arrange_conversation
        arrange_conversation(self,self.input,self.output,self.correct_button,row,'Version corrigée')
        self.status.setText('Écrivez ici ou sélectionnez un texte dans une autre application.')
        from shared.reading_selection import SelectionPicker
        self.picker=SelectionPicker(self,kind='corrector');self.picker.selected.connect(self.selected_text);self.picker.cancelled.connect(self.cancel_correction)
        self.active=False;self.busy=False;self.generation=0;self.cancel_event=threading.Event();self.transaction=None
        from shared.ui.reading_busy import ReadingBusy
        self.busy_indicator=ReadingBusy('Corrector · correction en cours','Patientez, correction du texte en cours')
        self.orb.doubleActivated.connect(self.open_window)
        self.orb.setAccessibleDescription('Clic : sélectionner un texte et le corriger. Double-clic : ouvrir Corrector. Échap : annuler la sélection.')
    def activate(self,*_):
        if self.active or self.busy:self.cancel_correction();return
        self.active=True;self.generation+=1;self.hide();self.picker.start();self.state('Activée');self.orb.setToolTip('Corrector · sélectionnez le texte à corriger · Échap pour annuler.')
    def open_window(self,*_):self.cancel_correction();ApplicationWindow.activate(self)
    def open_main_window(self):self.hide_orb(False);self.open_window()
    def showEvent(self,event):
        if getattr(self,'active',False):self.cancel_correction()
        super().showEvent(event)
    def cancel_correction(self):
        self.generation+=1;self.cancel_event.set();self.picker.stop();self.active=False
        self.busy_indicator.finish()
        self.status.setText('Correction annulée.');self.state('Activée')
    def selected_text(self,expected):
        if not self.active or self.busy:return
        self.picker.stop();self.active=False
        def operation(cancel):
            from shared.corrector_target import CorrectionTarget
            from shared.reading_selection import read_selection
            from ergoai.correction import correct
            api=CorrectionTarget();target=None;reason=''
            try:
                try:target=api.capture(expected);text=target.selected
                except Exception as error:
                    reason=str(error);text=read_selection(expected,point=self.picker.release_point)
                from shared.text_target import Selection
                document=getattr(target,'document','');end=getattr(target,'end',len(document))
                following=document.encode('utf-16-le')[end*2:].decode('utf-16-le') if isinstance(target,Selection) else document[end:]
                result=correct(text,cancel,following=following);result.update(original=text,target=target,wanted=None,reason=reason)
                if cancel.is_set():raise ValueError('Correction annulée.')
                if target and result['text']!=text:
                    try:result['wanted']=api.replace(target,result['text'])
                    except Exception as error:result['reason']=str(error)
                return result
            finally:api.close()
        self.start_correction(operation,external=True)
    def correct_manual(self):
        if self.busy:return
        self.picker.stop();self.active=False;text=self.input.toPlainText()
        if not text.strip():self.input.setFocus();return
        self.chat.begin(text);self.input.clear()
        from ergoai.correction import correct
        self.start_correction(lambda cancel:dict(correct(text,cancel),original=text,target=None,wanted=None,reason=''))
    def start_correction(self,operation,external=False):
        self.generation+=1;generation=self.generation;self.cancel_event=threading.Event();cancel=self.cancel_event
        self.busy=True;self.correct_button.setEnabled(False);self.state('Traitement en cours');self.status.setText('Correction en cours…')
        self.busy_indicator.begin(self.orb.animations)
        def done(result):
            if self.closing or generation!=self.generation:return
            if external or self.chat.current is None:self.chat.begin(result['original'])
            self.output.setPlainText(result['text'])
            if result['wanted']:
                self.transaction=(result['target'],result['wanted']);self.restore_button.setEnabled(True)
                self.status.setText('Sélection corrigée et remplacée · original restaurable.');self.state('Action réussie')
            elif result['reason']:
                self.status.setText('Correction prête · remplacement non effectué : '+result['reason']);self.state('Attention');ApplicationWindow.activate(self)
            else:self.status.setText('Correction prête.' if result['changes'] else 'Aucune correction certaine détectée.');self.state('Action réussie')
            remaining=result.get('remaining',[]);highlights=[]
            for issue in remaining:
                item=QTextEdit.ExtraSelection();item.cursor=QTextCursor(self.output.document())
                raw=result['text'];start=len(raw[:issue['start']].encode('utf-16-le'))//2;end=len(raw[:issue['end']].encode('utf-16-le'))//2
                item.cursor.setPosition(start);item.cursor.setPosition(end,QTextCursor.KeepAnchor)
                item.format.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline);item.format.setUnderlineColor(QColor('#F2D184'));highlights.append(item)
            self.output.setExtraSelections(highlights);self.review_label.setVisible(bool(remaining))
            if remaining:
                words=', '.join(dict.fromkeys(issue['text'] for issue in remaining[:6]))
                self.review_label.setText('À vérifier : '+words)
                self.status.setText(f"{result['changes']} correction(s) · {len(remaining)} point(s) restent à vérifier.")
                self.state('Attention');ApplicationWindow.activate(self)
            if result.get('warning'):
                self.status.setText(result['warning']+(' '+str(len(remaining))+' point(s) à vérifier.' if remaining else ''))
                self.state('Attention')
            self.orb.setToolTip('Corrector · '+self.status.text())
        job=background(self,lambda:operation(cancel),done)
        def finished():
            self.busy_indicator.finish();self.busy=False;self.correct_button.setEnabled(True)
        job.signals.finished.connect(finished)
    def restore_original(self):
        if not self.transaction or self.busy:return
        target,wanted=self.transaction
        def work():
            from shared.corrector_target import CorrectionTarget
            api=CorrectionTarget()
            try:api.restore(target,wanted)
            finally:api.close()
        def restored(_):self.transaction=None;self.restore_button.setEnabled(False);self.status.setText('Texte original restauré.')
        background(self,work,restored)
    def cleanup(self):
        self.cancel_event.set();self.picker.stop();self.picker.cursor.close();self.busy_indicator.finish();self.busy_indicator.close()
