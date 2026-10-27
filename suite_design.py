"""Shared clear surfaces inspired by Écrinator and PDFinator."""
import re
import unicodedata
from functools import lru_cache
from PySide6.QtCore import QObject,QEvent,Qt,QRectF,QPointF,QTimer
from PySide6.QtGui import QColor,QPalette,QPainter,QPen,QPainterPath,QFont,QLinearGradient,QIcon
from PySide6.QtWidgets import QWidget,QScrollArea,QPlainTextEdit,QTextEdit,QLineEdit,QGraphicsDropShadowEffect,QPushButton,QToolButton

INK='#1E3149';PAPER='#F6F9FD';LINE='#DCE3ED'

def tint(accent,amount):
    c=QColor(accent)
    return QColor(round(255*(1-amount)+c.red()*amount),round(255*(1-amount)+c.green()*amount),round(255*(1-amount)+c.blue()*amount)).name().upper()
ACCENTS={'ergonatus':'#253B70','claviernator':'#21866B','precisionator':'#9164E8','transcrinator':'#AD6826','transcri':'#AD6826','redactor':'#C84448','scanator':'#BA376D','ecrinator':'#0B57ED','organisator':'#368453','lector':'#597F2B','applinator':'#0080A1','temporator':'#BD4C37','concentrator':'#5758B8','pdfinator':'#5D49DF','calculinator':'#487DA1','communicator':'#94418D','memorinator':'#25806C','planinator':'#8F6426','traductor':'#187EAF','corrector':'#138352','dictionnator':'#326B9E','explicator':'#C07726','tablinator':'#218C83'}
def accent_for(app,widget=None):
    key=getattr(widget.window(),'app_id','') if widget is not None else ''
    name=key or app.applicationName()
    key=''.join(c for c in unicodedata.normalize('NFKD',name.casefold()) if not unicodedata.combining(c))
    return ACCENTS.get(key,'#253B70')
def _color(token,role):
    color=QColor(token)
    if not color.isValid():return token
    if role in ('color','selection-color'):
        if 145<color.lightness()<230 and color.saturation()<80:return '#64758B'
        return INK if color.lightness()>145 else color.name().upper()
    if role.startswith('border'):return LINE
    if color.lightness()>210:return color.name().upper()
    return '#FFFFFF'
@lru_cache(maxsize=256)
def lightify(css,accent='#3771F9'):
    protected=[]
    def protect(match):
        protected.append(match.group());return '@SUITEPRIMARY'+str(len(protected)-1)+'@'
    css=re.sub(r'QPushButton\[suitePrimary="true"\][^{}]*\{[^}]*\}',protect,css)
    def declaration(match):
        role,sep,value=match.groups()
        if role=='color' and value.strip().lower() in ('white','ivory','snow'):value=INK
        value=re.sub(r'#[0-9A-Fa-f]{6}(?![0-9A-Fa-f])',lambda m:_color(m.group(),role),value)
        if role.startswith('background'):
            value=re.sub(r'rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*([\d.]+)\s*\)',r'rgba(255,255,255,\1)',value)
        if role=='border':value=re.sub(r'^[234]px\b','1px',value)
        return role+sep+value
    result=re.sub(r'\b(background(?:-color)?|color|border(?:-color)?|selection-background-color|selection-color)(\s*:\s*)([^;{}]+)',declaration,css)
    def state_rule(match):
        selector,body=match.groups()
        color=accent if ':checked' in selector or 'sub-page' in selector or 'handle' in selector else '#DCE3ED'
        body=re.sub(r'\bbackground\s*:[^;]+;',f'background:{color};',body)
        return selector+'{'+body+'}'
    result=re.sub(r'((?:QCheckBox|QRadioButton)[^{]*::indicator:checked\s*|QSlider::(?:groove|sub-page|handle):horizontal\s*)\{([^}]+)\}',state_rule,result)
    result=re.sub(r'(QPushButton#Primary[^{}]*\{)([^}]+)(\})',lambda m:m[1]+re.sub(r'\b(?:background|color)\s*:[^;]+;','',m[2])+'background:'+accent+';color:#FFFFFF;'+m[3],result)
    def button_state(match):
        selector,body=match.groups()
        if '#Primary' in selector:return selector+'{'+body+'}'
        color=QColor(accent);amount=.24 if ':pressed' in selector else .16
        tint=QColor(round(255*(1-amount)+color.red()*amount),round(255*(1-amount)+color.green()*amount),round(255*(1-amount)+color.blue()*amount)).name().upper()
        body=re.sub(r'\b(?:background(?:-color)?|color|border)\s*:[^;]+;','',body)
        return selector+'{'+body+'background:'+tint+';color:#1E3149;border:1px solid '+accent+';}'
    result=re.sub(r'((?:QPushButton|QToolButton)[^{}]*(?::checked|:hover|:pressed)[^{}]*)\{([^}]+)\}',button_state,result)
    # Keep the primary rule stable on repeated Show/StyleChange events.
    result=result.replace('background:#3771F9;color:#FFFFFF;background:#3771F9;color:#FFFFFF;','background:#3771F9;color:#FFFFFF;')
    result=result.replace(PAPER,tint(accent,.045)).replace(LINE,tint(accent,.45))
    for index,rule in enumerate(protected):result=result.replace('@SUITEPRIMARY'+str(index)+'@',rule)
    return result

BASE='''
QWidget {font-family:"Segoe UI";font-size:10pt;color:#1E3149;}
QMainWindow,QDialog {background:#F6F9FD;}
QLabel {background:transparent;}
QSizeGrip {background:transparent;width:12px;height:12px;}
QPushButton,QToolButton {border-radius:9px;}
QPushButton:hover,QToolButton:hover {background:#E4EBF5;border:1px solid #68819E;}
QPushButton:pressed,QToolButton:pressed {background:#CCD9EB;border:1px solid #3A567A;}
QPushButton:focus,QToolButton:focus {border:1px solid #3A567A;}
QLineEdit,QPlainTextEdit,QTextEdit,QComboBox,QSpinBox,QDateTimeEdit {selection-background-color:#DCE9FF;selection-color:#1E3149;}
QToolTip {background:#FFFFFF;color:#1E3149;border:1px solid #DCE3ED;padding:6px;font:9pt "Segoe UI";}
'''
class SurfaceFilter(QObject):
    def __init__(self,app):super().__init__(app);self.app=app;self.applying=False;self.global_style_pending=False
    def normalize_global_style(self):
        self.global_style_pending=False
        css=self.app.styleSheet();converted=lightify(css,accent_for(self.app))
        if css==converted:return
        self.applying=True
        try:self.app.setStyleSheet(converted)
        finally:self.applying=False
    def paint_control(self,widget):
        kind=type(widget).__name__
        if widget.objectName()=='ModernScrollPanel' or (widget.objectName()=='qt_scrollarea_viewport' and isinstance(widget.parentWidget(),QScrollArea) and widget.window().windowType()!=Qt.Tool):
            p=QPainter(widget);p.fillRect(widget.rect(),QColor(tint(accent_for(self.app,widget),.035)));p.end();return True
        if kind in ('Shell','HudShell','ErgoBackdrop','FortSurface'):
            accent=accent_for(self.app,widget);p=QPainter(widget);p.setRenderHint(QPainter.Antialiasing)
            glass=QLinearGradient(0,0,widget.width()*.3,widget.height());glass.setColorAt(0,QColor('#FFFFFF'));glass.setColorAt(.35,QColor(tint(accent,.025)));glass.setColorAt(1,QColor(tint(accent,.055)))
            p.setPen(QPen(QColor(tint(accent,.4)),1));p.setBrush(glass)
            p.drawRoundedRect(QRectF(widget.rect()).adjusted(1,1,-1,-1),16,16);p.end();return True
        if kind not in ('Switch','Toggle','CheckChip','PreferencesCard','DictionaryButton','CaptionButton','PauseButton'):return False
        p=QPainter(widget);p.setRenderHint(QPainter.Antialiasing);accent=QColor(accent_for(self.app,widget));rect=QRectF(widget.rect()).adjusted(.75,.75,-.75,-.75)
        if not widget.isEnabled():p.setOpacity(.5)
        if kind=='CheckChip':
            p.setPen(QPen(accent if widget.isChecked() else QColor(LINE),1));p.setBrush(QColor('#F0F4F9' if widget.isChecked() else '#FFFFFF'));p.drawRoundedRect(rect,8,8)
            p.setBrush(accent if widget.isChecked() else QColor('white'));p.drawRoundedRect(QRectF(9,8,13,13),3,3)
            if widget.isChecked():
                p.setPen(QPen(QColor('white'),1.6));p.drawLine(QPointF(12,14),QPointF(15,17));p.drawLine(QPointF(15,17),QPointF(20,11))
            p.setPen(QColor(INK));p.setFont(widget.font());p.drawText(QRectF(29,0,widget.width()-32,widget.height()),Qt.AlignLeft|Qt.AlignVCenter,widget.text())
        elif kind in ('Switch','Toggle'):
            value=float(getattr(widget,'_position',1 if widget.isChecked() else 0));height=min(24.,widget.height()-4);top=(widget.height()-height)/2
            off=QColor('#DCE3ED');track=QColor(round(off.red()*(1-value)+accent.red()*value),round(off.green()*(1-value)+accent.green()*value),round(off.blue()*(1-value)+accent.blue()*value))
            p.setPen(Qt.NoPen);p.setBrush(track);p.drawRoundedRect(QRectF(2,top,44,height),height/2,height/2)
            p.setBrush(QColor('white'));p.drawEllipse(QRectF(5+20*value,top+3,height-6,height-6))
            if widget.text():p.setPen(QColor(INK));p.setFont(widget.font());p.drawText(QRectF(58,0,max(0,widget.width()-58),widget.height()),Qt.AlignLeft|Qt.AlignVCenter,widget.text())
        else:
            p.setPen(QPen(QColor(tint(accent,.35)),1));p.setBrush(QColor(tint(accent,.08) if widget.underMouse() and kind!='PreferencesCard' else '#FFFFFF'));p.drawRoundedRect(rect,12 if kind=='PreferencesCard' else 9,12 if kind=='PreferencesCard' else 9)
            p.setPen(QPen(accent if kind=='DictionaryButton' else QColor(INK),1.6,Qt.SolidLine,Qt.RoundCap))
            x,y=widget.width()/2,widget.height()/2
            if kind=='CaptionButton':
                if widget.close_icon:p.drawLine(QPointF(x-4,y-4),QPointF(x+4,y+4));p.drawLine(QPointF(x-4,y+4),QPointF(x+4,y-4))
                else:p.drawLine(QPointF(x-5,y),QPointF(x+5,y))
            elif kind=='DictionaryButton':
                p.drawRoundedRect(QRectF(14,y-8,20,16),2,2);p.drawLine(QPointF(24,y-8),QPointF(24,y+8));p.setFont(widget.font());p.drawText(QRectF(45,0,widget.width()-55,widget.height()),Qt.AlignLeft|Qt.AlignVCenter,widget.text())
            elif kind=='PauseButton':
                p.setFont(QFont('Segoe UI',9));p.drawText(QRectF(12,0,widget.width()-55,widget.height()),Qt.AlignVCenter|Qt.AlignLeft,widget.text());p.drawText(QRectF(widget.width()-42,0,35,widget.height()),Qt.AlignVCenter|Qt.AlignCenter,'F12')
        if widget.hasFocus():p.setPen(QPen(accent,1,Qt.DotLine));p.setBrush(Qt.NoBrush);p.drawRoundedRect(rect.adjusted(1,1,-1,-1),9,9)
        p.end();return True
    def eventFilter(self,watched,event):
        if self.applying or not isinstance(watched,QWidget) or getattr(watched,'_suite_clarity',False):return False
        if event.type() in (QEvent.Resize,QEvent.Show) and watched.isWindow() and watched.width()>300 and not getattr(watched,'_clean_hub_frame',False) and not watched.isFullScreen() and type(watched).__name__ not in ('QMenu','QComboBoxPrivateContainer','MemorinatorWindow'):
            if not hasattr(watched,'_identity_edge'):watched._identity_edge=IdentityEdge(watched,accent_for(self.app,watched))
            watched._identity_edge.setGeometry(watched.rect());watched._identity_edge.raise_();watched._identity_edge.show()
        if event.type()==QEvent.Paint:return self.paint_control(watched)
        if event.type() not in (QEvent.Show,QEvent.StyleChange,QEvent.FocusIn):return False
        if watched.objectName()=='DialControl':return False
        self.applying=True
        try:
            css=self.app.styleSheet();converted=lightify(css,accent_for(self.app))
            if css!=converted and not self.global_style_pending:
                # Re-polishing every widget during a native Focus/Show callback
                # can invalidate Qt editor internals. Apply at the next turn.
                self.global_style_pending=True;QTimer.singleShot(0,self,self.normalize_global_style)
            css=watched.styleSheet();converted=lightify(css,accent_for(self.app,watched))
            if css!=converted:watched.setStyleSheet(converted)
            if isinstance(watched,(QPushButton,QToolButton)):
                watched.setCursor(Qt.PointingHandCursor)
                primary=watched.text().strip().casefold() in ('corriger','définir','trouver','comprendre','lire','parler','montrer','m’aider à comprendre','démarrer le minuteur','créer sur le bureau','afficher mes raccourcis')
                if primary and not watched.property('_suite_primary_styled'):
                    colour=QColor(accent_for(self.app,watched))
                    while colour.lightness()>100:colour=colour.darker(110)
                    base=colour.name();hover=colour.lighter(115).name();pressed=colour.darker(115).name()
                    watched.setProperty('_suite_primary_styled',True);watched.setProperty('suitePrimary',True)
                    watched.setStyleSheet(watched.styleSheet()+' QPushButton[suitePrimary="true"] {background:'+base+';color:#FFFFFF;border:1px solid '+base+';} QPushButton[suitePrimary="true"]:hover {background:'+hover+';color:#FFFFFF;border:1px solid '+base+';} QPushButton[suitePrimary="true"]:pressed {background:'+pressed+';color:#FFFFFF;border:1px solid '+base+';} QPushButton[suitePrimary="true"]:disabled {background:#E4E9EF;color:#728093;border:1px solid #AAB8C8;}')
                    if not watched.icon().isNull():
                        icon=watched.icon().pixmap(watched.iconSize());painter=QPainter(icon);painter.setCompositionMode(QPainter.CompositionMode_SourceIn);painter.fillRect(icon.rect(),QColor('#FFFFFF'));painter.end();watched.setIcon(QIcon(icon))
            if isinstance(watched,(QPlainTextEdit,QTextEdit,QLineEdit)):
                # Effects on editable viewports cache their drawing and can hide
                # caret repaints. Keep shadows on their enclosing cards only.
                if isinstance(watched.graphicsEffect(),QGraphicsDropShadowEffect):watched.setGraphicsEffect(None)
                parent=watched.parentWidget()
                while parent is not None:
                    if parent.objectName() in ('Card','Composer') and isinstance(parent.graphicsEffect(),QGraphicsDropShadowEffect):parent.setGraphicsEffect(None)
                    parent=parent.parentWidget()
                palette=watched.palette();palette.setColor(QPalette.Text,QColor(INK));palette.setColor(QPalette.PlaceholderText,QColor('#64758B'));watched.setPalette(palette)
                editable=not watched.isReadOnly();watched.setCursor(Qt.IBeamCursor if editable else Qt.ArrowCursor)
                if isinstance(watched,(QPlainTextEdit,QTextEdit)):
                    watched.setCursorWidth(2);watched.viewport().setCursor(Qt.IBeamCursor if editable else Qt.ArrowCursor)
                if editable and watched.focusPolicy()==Qt.NoFocus:watched.setFocusPolicy(Qt.StrongFocus)
            elif watched.cursor().shape()==Qt.BlankCursor:watched.setCursor(Qt.ArrowCursor)
            if event.type()==QEvent.Show and watched.objectName() in ('Card','Composer') and watched.graphicsEffect() is None and not any(watched.findChildren(cls) for cls in (QPlainTextEdit,QTextEdit,QLineEdit)):
                shadow=QGraphicsDropShadowEffect(watched);shadow.setBlurRadius(14);shadow.setOffset(0,2)
                colour=QColor(accent_for(self.app,watched));colour.setAlpha(24);shadow.setColor(colour);watched.setGraphicsEffect(shadow)
            if watched.objectName() in ('UserBubble','AssistantBubble'):
                accent=QColor(accent_for(self.app,watched));bubble_tint=QColor(round(255*.92+accent.red()*.08),round(255*.92+accent.green()*.08),round(255*.92+accent.blue()*.08)).name()
                background=bubble_tint if watched.objectName()=='UserBubble' else '#FFFFFF'
                watched.setStyleSheet('QFrame#'+watched.objectName()+' {background:'+background+';border:1px solid '+LINE+';border-radius:16px;} QFrame#'+watched.objectName()+' QLabel {background:transparent;border:none;}')
            if event.type()==QEvent.Show and isinstance(watched,QScrollArea) and watched.window().windowType()!=Qt.Tool:
                surface=tint(accent_for(self.app,watched),.035)
                watched.viewport().setAttribute(Qt.WA_TranslucentBackground,False)
                watched.viewport().setAttribute(Qt.WA_NoSystemBackground,False)
                watched.viewport().setAutoFillBackground(True)
                palette=watched.viewport().palette();palette.setColor(QPalette.Window,QColor(surface));palette.setColor(QPalette.Base,QColor(surface));watched.viewport().setPalette(palette)
                watched.viewport().setStyleSheet('background:'+surface+';')
                panel=watched.widget()
                if panel:
                    panel.setAttribute(Qt.WA_TranslucentBackground,False);panel.setAttribute(Qt.WA_StyledBackground,True);panel.setAutoFillBackground(True)
                    panel.setAttribute(Qt.WA_NoSystemBackground,False)
                    palette=panel.palette();palette.setColor(QPalette.Window,QColor(surface));panel.setPalette(palette)
                    if not panel.objectName():panel.setObjectName('ModernScrollPanel')
                    rule='QWidget#'+panel.objectName()+' {background-color:'+surface+';}'
                    if rule not in panel.styleSheet():panel.setStyleSheet(panel.styleSheet()+'\n'+rule)
        finally:self.applying=False
        return False

class IdentityEdge(QWidget):
    """A soft, colour-coded edge that never intercepts mouse or keyboard input."""
    def __init__(self,parent,accent):
        super().__init__(parent);self.accent=QColor(accent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents);self.setAttribute(Qt.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.NoFocus)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setBrush(Qt.NoBrush)
        rect=QRectF(self.rect()).adjusted(1.25,1.25,-1.25,-1.25)
        # A crisp coloured glass rim, a white bevel and a narrow recessed shadow.
        rim=QLinearGradient(0,0,self.width(),self.height())
        rim.setColorAt(0,QColor(tint(self.accent,.75)));rim.setColorAt(.28,QColor(tint(self.accent,.3)));rim.setColorAt(.62,QColor(tint(self.accent,.4)));rim.setColorAt(1,QColor(tint(self.accent,.8)))
        p.setPen(QPen(rim,1.8));p.drawRoundedRect(rect,16,16)
        bevel=QLinearGradient(0,0,0,self.height());bevel.setColorAt(0,QColor(255,255,255,245));bevel.setColorAt(.45,QColor(255,255,255,110));bevel.setColorAt(1,QColor(20,35,55,28))
        p.setPen(QPen(bevel,2));p.drawRoundedRect(rect.adjusted(2,2,-2,-2),14,14)
        c=QColor(self.accent);c.setAlpha(10);p.setPen(QPen(c,3));p.drawRoundedRect(rect.adjusted(4,4,-4,-4),12,12)
        p.end()
def install(app):
    if getattr(app,'_ergonatus_surface_filter',None):return
    app.setStyle('Fusion');app.setCursorFlashTime(1000);palette=app.palette()
    for role,value in [(QPalette.Window,PAPER),(QPalette.Base,'#FFFFFF'),(QPalette.AlternateBase,'#EEF3FA'),(QPalette.WindowText,INK),(QPalette.Text,INK),(QPalette.Button,'#FFFFFF'),(QPalette.ButtonText,INK),(QPalette.Highlight,'#DCE9FF'),(QPalette.HighlightedText,INK)]:palette.setColor(role,QColor(value))
    app.setPalette(palette);app.setStyleSheet(lightify(app.styleSheet()+BASE,accent_for(app)))
    app._ergonatus_surface_filter=SurfaceFilter(app);app.installEventFilter(app._ergonatus_surface_filter)

    # Load the live interaction layer for every independently packaged Qt app.
    import importlib.util
    from pathlib import Path
    import sys
    root=next((p for p in Path(sys.executable).resolve().parents if (p/'suite_interactions.py').is_file() and (p/'assets/orbs/ergonatus.png').is_file()),Path(__file__).resolve().parent)
    path=root/'suite_interactions.py'
    if path.is_file():
        spec=importlib.util.spec_from_file_location('ergonatus_live_interactions',path);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);module.install(app)
