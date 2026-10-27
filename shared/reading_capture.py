"""User-drawn screen region -> local OCR -> speech, without clipboard writes."""
import uuid
from PySide6.QtCore import QObject,QTimer
from shared.domain import app_data

class ReadingCapture(QObject):
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.overlay=None;self.busy=False;self.return_orb=False

    def start(self,*_):
        owner=self.owner
        if self.busy:owner.stop_lector();return
        owner.stop_lector();owner.lector_active=True;owner.lector_generation+=1
        generation=owner.lector_generation;self.busy=True;self.return_orb=owner.orb.isVisible()
        owner.capture_pending=True;owner.hide();owner.orb.hide()
        owner.status.setText('Tracez une zone à lire · Échap pour annuler.')
        def capture():
            if owner.closing or not owner.lector_active or generation!=owner.lector_generation:return
            try:
                from shared.apps.overlays import CaptureOverlay
                self.overlay=CaptureOverlay()
                self.overlay.captured.connect(lambda image:self.captured(image,generation))
                self.overlay.cancelled.connect(owner.stop_lector)
                self.overlay.show();self.overlay.raise_();self.overlay.activateWindow()
            except Exception as error:
                self.cancel();owner.lector_active=False;owner.error('Capture indisponible : '+str(error))
        QTimer.singleShot(250,capture)

    def restore(self):
        self.owner.capture_pending=False
        if self.overlay is not None:
            self.overlay.close();self.overlay.deleteLater();self.overlay=None
        if self.return_orb and not self.owner.closing:self.owner.orb.show()

    def cancel(self):
        pending=getattr(self.owner,'capture_pending',False)
        self.restore()
        if pending:self.busy=False

    def captured(self,image,generation,double_page=False):
        owner=self.owner
        if owner.closing or not owner.lector_active or generation!=owner.lector_generation:self.cancel();return
        self.restore()
        path=app_data('lector')/('reading-'+uuid.uuid4().hex+'.png')
        if image.isNull() or not image.save(str(path)):
            self.busy=False;owner.lector_active=False;owner.error('La capture ne contient pas d’image lisible.');return
        from shared.jobs import background
        from shared.reading_layout import recognize_reading
        owner.busy_indicator.begin(owner.orb.animations)
        owner.state('Traitement en cours');owner.status.setText('Reconnaissance du texte · clic sur l’Orb pour annuler.')
        def current():return not owner.closing and owner.lector_active and generation==owner.lector_generation
        def work():
            try:return recognize_reading(path,double_page)
            finally:path.unlink(missing_ok=True)
        def done(text):
            if not current():return
            if not text.strip():
                owner.busy_indicator.finish()
                owner.lector_active=False;owner.state('Attention');owner.status.setText('Aucun texte reconnu. Sélectionnez une zone plus nette.');owner.orb.setToolTip('Lector · aucun texte reconnu · double-clic pour réessayer.');return
            owner.input.setPlainText(text);owner.lector_speak(text)
        job=background(owner,work,done)
        job.signals.finished.connect(lambda:setattr(self,'busy',False))
        def failed(message):
            if current():owner.busy_indicator.finish();owner.lector_active=False;owner.error(message);owner.orb.setToolTip('Lector · '+str(message)[:250]+' · double-clic pour réessayer.')
        job.signals.error.disconnect(owner.error)
        job.signals.error.connect(failed)
