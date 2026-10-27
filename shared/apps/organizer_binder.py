"""A read-only, animated binder over real Organisator files."""
from pathlib import Path
from dataclasses import dataclass
import os,re,json,math
from PySide6.QtCore import Qt,QTimer,QSize,QRect,QRectF,QPointF,QPropertyAnimation,Property,QEasingCurve,QUrl
from PySide6.QtGui import QPainter,QColor,QPen,QPixmap,QImage,QImageReader,QLinearGradient,QPolygonF,QTransform,QPainterPath,QIcon,QDesktopServices,QShortcut,QKeySequence
from PySide6.QtWidgets import QWidget,QMainWindow,QFrame,QLabel,QPushButton,QVBoxLayout,QHBoxLayout,QLineEdit,QComboBox,QListWidget,QListWidgetItem,QPlainTextEdit,QApplication,QStackedWidget,QSlider,QSizePolicy
from shared.catalog import suite_root
from shared.jobs import background
from shared.ui.components import ErgoWindow
from shared.ui.choices import ChoiceBox
from shared.organizer import inside,read_text,IMAGES,DOCUMENT_LOCK,folded,INBOX

@dataclass(frozen=True)
class BinderDocument:
    relative: str
    size: int
    modified: int

def list_documents(root,limit=10000):
    """Never follow links or inspect file contents while building the index."""
    root=inside(root,root);rows=[];truncated=False
    for base,folders,names in os.walk(root,followlinks=False):
        safe=[]
        for name in folders:
            if name.startswith('.'):continue
            try:inside(root,Path(base)/name);safe.append(name)
            except (OSError,ValueError):continue
        folders[:]=safe
        for name in names:
            if name.startswith(('.','~$')) or name.casefold()=='desktop.ini':continue
            try:
                p=inside(root,Path(base)/name,True);info=p.stat();rows.append(BinderDocument(p.relative_to(root).as_posix(),info.st_size,info.st_mtime_ns))
            except (OSError,ValueError):continue
            if len(rows)>=limit:truncated=True;break
        if truncated:break
    return sorted(rows,key=lambda d:folded(d.relative)),truncated

def text_pages(text,limit=1250):
    text=text.strip();pages=[]
    while len(text)>limit:
        split=text.rfind('\n',limit//2,limit)
        if split<0:split=text.rfind(' ',limit//2,limit)
        if split<0:split=limit
        pages.append(text[:split].rstrip());text=text[split:].lstrip()
    if text:pages.append(text)
    return pages or ['Ce document ne contient pas de texte lisible dans cet aperçu.']

def ecr_text(path):
    if path.stat().st_size>32*1024**2:return ''
    data=json.loads(path.read_text(encoding='utf-8'));parts=[]
    def visit(value):
        if isinstance(value,dict):
            if isinstance(value.get('text'),str):parts.append(value['text'])
            for key,child in value.items():
                if key not in ('text','assets','images','metadata','styles'):visit(child)
        elif isinstance(value,list):
            for child in value:visit(child)
    visit(data.get('document',data));return '\n'.join(parts)[:120000]

def preview_document(root,document,page=0):
    path=inside(root,Path(root)/document.relative,True);ext=path.suffix.lower()
    if ext=='.pdf':
        import pymupdf
        with DOCUMENT_LOCK,pymupdf.open(path) as pdf:
            if pdf.needs_pass:return dict(kind='PDF protégé',text='Ouvrez ce document dans son logiciel pour saisir son mot de passe.',page=0,pages=1,image=None)
            if not len(pdf):raise ValueError('Ce PDF ne contient aucune page.')
            index=len(pdf)-1 if page<0 else min(page,len(pdf)-1);leaf=pdf[index];scale=min(1400/max(1,leaf.rect.width),1800/max(1,leaf.rect.height),2)
            pix=leaf.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False)
            return dict(kind='PDF',image=QImage.fromData(pix.tobytes('png')),text='',page=index,pages=len(pdf))
    if ext in IMAGES:
        reader=QImageReader(str(path));size=reader.size()
        if not size.isValid() or size.width()*size.height()>80_000_000:raise ValueError('Cette image est trop grande pour l’aperçu.')
        reader.setAutoTransform(True);reader.setScaledSize(size.scaled(1400,1800,Qt.KeepAspectRatio));image=reader.read()
        if image.isNull():raise ValueError('L’image n’a pas pu être lue.')
        return dict(kind='Image',image=image,text='',page=0,pages=1)
    text,kind=(ecr_text(path),'Écrinator · aperçu texte') if ext=='.ecr' else read_text(path)
    if not text:return dict(kind=ext[1:].upper() or 'Document',image=None,text='Ce format se consulte dans son application.\n\nUtilisez « Ouvrir le document » pour le retrouver tel qu’il a été créé.',page=0,pages=1)
    leaves=text_pages(text);index=len(leaves)-1 if page<0 else min(page,len(leaves)-1)
    return dict(kind='Texte' if kind=='Texte' else 'Aperçu texte',image=None,text=leaves[index],page=index,pages=len(leaves))

def file_icon(suffix):
    pix=QPixmap(36,44);pix.fill(Qt.transparent);p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing)
    color=QColor({'pdf':'#BE5B52','docx':'#4B7BA9','odt':'#4B7BA9','ecr':'#4B7BA9','png':'#9B73AE','jpg':'#9B73AE','xlsx':'#488767'}.get(suffix,'#6B8278'))
    p.setPen(QPen(color,1));p.setBrush(QColor('#FFFFFF'));p.drawRoundedRect(QRectF(3,2,30,39),4,4)
    p.fillRect(QRectF(3,27,30,12),color);p.setPen(QColor('white'));f=p.font();f.setPixelSize(9);f.setBold(True);p.setFont(f);p.drawText(QRectF(3,27,30,12),Qt.AlignCenter,suffix[:4].upper() or 'DOC');p.end();return QIcon(pix)

class DividerTab(QPushButton):
    def __init__(self,name,color,index,callback,parent=None):
        super().__init__(name,parent);self.color=QColor(color);self.index=index;self.setCheckable(True);self.setStyleSheet('QPushButton {min-height:36px;max-height:36px;padding:0px;margin:0px;border:none;background:transparent;}');self.setFixedHeight(36);self.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed);self.setCursor(Qt.PointingHandCursor);self.setAccessibleName('Intercalaire '+name);self.setToolTip(name);self.clicked.connect(callback)
        self.art=QPixmap(str(suite_root()/'assets/binder/divider-tab-v1.png'))
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);r=QRectF(self.rect()).adjusted(0,1,-2 if self.isChecked() else -10,-2)
        c=self.color.lighter(112 if self.isChecked() else 125);gradient=QLinearGradient(0,0,0,self.height());gradient.setColorAt(0,c.lighter(112));gradient.setColorAt(1,c)
        shape=QPainterPath();shape.moveTo(r.left(),r.top());shape.lineTo(r.right()-7,r.top());shape.quadTo(r.right(),r.top(),r.right(),r.top()+7);shape.lineTo(r.right(),r.bottom()-7);shape.quadTo(r.right(),r.bottom(),r.right()-7,r.bottom());shape.lineTo(r.left(),r.bottom());shape.closeSubpath()
        p.setPen(QPen(self.color.darker(130),1.2 if self.isChecked() else .7));p.setBrush(gradient);p.drawPath(shape)
        if not self.art.isNull():p.setOpacity(.28);p.drawPixmap(r,self.art,QRectF(self.art.rect()));p.setOpacity(1)
        p.setPen(QColor('#243C32'));f=p.font();f.setPointSize(9);f.setBold(self.isChecked());p.setFont(f)
        short={'Tout le classeur':'Tous','Mathématiques':'Maths','Histoire-géographie':'Hist.-Géo','Physique-chimie':'Phys.-chim.','Questionner le monde':'Découvrir\nle monde','Documents école':'École','Ressources humaines':'Ressources\nhumaines','Arts plastiques':'Arts'}.get(self.text(),self.text())
        p.drawText(r.adjusted(7,2,-5,-2),Qt.AlignVCenter|Qt.AlignCenter|Qt.TextWordWrap,short)
        if self.isChecked():p.setPen(QPen(QColor('#FFFFFF'),2));p.drawLine(QPointF(5,9),QPointF(5,self.height()-9))
        if self.hasFocus():p.setPen(QPen(QColor('#244D3B'),1,Qt.DotLine));p.setBrush(Qt.NoBrush);p.drawRoundedRect(r.adjusted(2,2,-2,-2),7,7)
        p.end()

class PaperImage(QLabel):
    def __init__(self):super().__init__();self.image=QImage();self.setAlignment(Qt.AlignCenter);self.setMinimumSize(40,40)
    def display(self,image):self.image=image;self.update_image()
    def update_image(self):
        if not self.image.isNull():
            ratio=self.devicePixelRatioF();target=QSize(max(1,round(self.width()*ratio)),max(1,round(self.height()*ratio)));pix=QPixmap.fromImage(self.image).scaled(target,Qt.KeepAspectRatio,Qt.SmoothTransformation);pix.setDevicePixelRatio(ratio);self.setPixmap(pix)
    def resizeEvent(self,event):super().resizeEvent(event);self.update_image()

class PageTurn(QWidget):
    def __init__(self,canvas):
        super().__init__(canvas);self.canvas=canvas;self.setAttribute(Qt.WA_TransparentForMouseEvents);self._progress=0.;self.hide()
        self.animation=QPropertyAnimation(self,b'progress',self);self.animation.setDuration(460);self.animation.setEasingCurve(QEasingCurve.InOutCubic);self.animation.finished.connect(self.hide)
    def get_progress(self):return self._progress
    def set_progress(self,value):self._progress=value;self.update()
    progress=Property(float,get_progress,set_progress)
    def start(self,before,after,direction):
        self.animation.stop();self.before=before;self.after=after;self.direction=direction;self.setGeometry(self.canvas.rect());self._progress=0.;self.show();self.raise_();self.animation.setStartValue(0.);self.animation.setEndValue(1.);self.animation.start()
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.drawPixmap(self.rect(),self.after)
        book=self.canvas.book_rect;spine=book.left()+book.width()*.5;top=book.top()+book.height()*.045;bottom=book.top()+book.height()*.925
        width=book.width()*.44;height=bottom-top;t=self._progress;cosine=math.cos(math.pi*t);bend=math.sin(math.pi*t)*height*.045
        reverse=self.direction<0
        if reverse:p.translate(spine*2,0);p.scale(-1,1)
        source=self.before if t<.5 else self.after
        source_rect=self.canvas.right_rect if (t<.5)!=reverse else self.canvas.left_rect
        ratio=source.devicePixelRatio();crop=source.copy(QRect(round(source_rect.x()*ratio),round(source_rect.y()*ratio),round(source_rect.width()*ratio),round(source_rect.height()*ratio)))
        target=QPolygonF([QPointF(spine,top),QPointF(spine+width*cosine,top+bend),QPointF(spine+width*cosine,bottom-bend),QPointF(spine,bottom)])
        origin=QPolygonF([QPointF(0,0),QPointF(width,0),QPointF(width,height),QPointF(0,height)])
        ok,transform=False,QTransform()
        # Qt's four-point homography preserves real text on the turning sheet.
        mapped=QTransform.quadToQuad(origin,target,transform)
        if mapped:
            p.save();p.setTransform(transform,True);p.drawPixmap(QRectF(0,0,width,height),crop,QRectF(crop.rect()));p.restore()
        shadow=QLinearGradient(spine,0,spine+width*cosine,0);shadow.setColorAt(0,QColor(14,37,24,int(85*math.sin(math.pi*t))));shadow.setColorAt(1,QColor(255,255,255,20))
        p.setPen(QPen(QColor(70,66,49,55),.7));p.setBrush(shadow);p.drawPolygon(target);p.end()

class BinderCanvas(QWidget):
    def __init__(self):
        super().__init__();self.setObjectName('BinderCanvas');self.setMinimumSize(700,450);self.setAutoFillBackground(False);art=suite_root()/'assets/binder/pages-a4-v3.png';self.art=QPixmap(str(art if art.exists() else art.with_name('pages-open-v2.png')))
        self.left=QFrame(self);self.left.setObjectName('BinderPaper');self.right=QFrame(self);self.right.setObjectName('BinderPaper');self.tabs=QWidget(self);self.tabs.setObjectName('BinderTabs');self.turn=PageTurn(self)
        self.book_rect=QRectF();self.left_rect=QRectF();self.right_rect=QRectF()
    def resizeEvent(self,event):
        super().resizeEvent(event);available=max(1,self.width()-130);height=min(self.height()-18,available/1.44);width=height*1.44
        x=max(0,(self.width()-width-86)/2);y=(self.height()-height)/2;self.book_rect=QRectF(x,y,width,height)
        self.left_rect=QRectF(x+width*.062,y+height*.07,width*.395,height*.82);self.right_rect=QRectF(x+width*.543,y+height*.07,width*.389,height*.82)
        self.left.setGeometry(self.left_rect.toRect());self.right.setGeometry(self.right_rect.toRect());self.tabs.setGeometry(QRect(round(x+width*.945),round(y+height*.07),86,round(height*.84)))
        self.position_arrows()
        self.turn.setGeometry(self.rect());self.update()
    def position_arrows(self):
        for name,fraction in [('previous_arrow',.015),('next_arrow',.95)]:
            button=getattr(self,name,None)
            if button is not None:button.setGeometry(round(self.book_rect.x()+self.book_rect.width()*fraction),round(self.book_rect.y()+self.book_rect.height()*.935),38,38);button.raise_()
    def paintEvent(self,event):
        p=QPainter(self)
        if not self.art.isNull():p.drawPixmap(self.book_rect,self.art,QRectF(self.art.rect()))
        else:p.fillRect(self.book_rect,QColor('#F7F4EC'))
        p.end()

class BinderWindow(ErgoWindow):
    def __init__(self,owner):
        super().__init__(owner);self.setWindowFlags(Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint);self.setAttribute(Qt.WA_TranslucentBackground);self.owner=owner;self.app_id='organisator';self.pending=set();self.closing=False;self.root=None;self.documents=[];self.visible_documents=[];self.current=None;self.page=0;self.pages=1;self.token=0;self.reload_token=0;self.section='';self.section_page=0;self.sections=[];self.background_opacity=max(0,min(100,int(owner.preferences.get('organizer_binder_opacity',88))))
        self.setWindowTitle('Organisator · Mon classeur');self.resize(1120,720);self.setMinimumSize(820,580)
        self.setStyleSheet('''QWidget {font-family:'Segoe UI';color:#253E32;font-size:10pt;} QMainWindow,QWidget#BinderRoot {background:transparent;} QFrame#BinderHeader,QFrame#BinderFooter {background:#FAFCF9;border:1px solid #C5D4C3;border-radius:12px;} QWidget#BinderCanvas,QFrame#BinderPaper,QWidget#BinderTabs,QLabel {background:transparent;border:none;} QPushButton {background:#FAFCF9;border:1px solid #B9CDBD;border-radius:9px;padding:6px 10px;min-height:24px;color:#244C36;} QPushButton:hover {background:#E6F0E6;} QPushButton#BinderOpen {background:#28734F;color:#FFFFFF;border:1px solid #28734F;font-weight:600;} QComboBox,QLineEdit {background:#FFFFFF;border:1px solid #CDD7C8;border-radius:8px;padding:6px;color:#253E32;} QListWidget {background:transparent;border:none;outline:none;} QListWidget::item {background:transparent;border-bottom:1px solid #DDDCCF;padding:8px 3px;min-height:42px;} QListWidget::item:selected {background:#E6EEE1;color:#20392A;border-radius:8px;} QPlainTextEdit {background:transparent;border:none;padding:0px;font-size:11pt;color:#26392E;} QScrollBar:vertical {width:6px;background:transparent;} QScrollBar::handle:vertical {background:#B9C9B5;border-radius:3px;min-height:20px;} QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0px;} QSlider::groove:horizontal {height:5px;background:#D3DED1;border-radius:2px;} QSlider::sub-page:horizontal {background:#51885F;border-radius:2px;} QSlider::handle:horizontal {width:16px;margin:-6px 0;background:#2C7047;border:1px solid #FFFFFF;border-radius:8px;}''')
        root=QWidget();root.setObjectName('BinderRoot');self.setCentralWidget(root);layout=QVBoxLayout(root);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        header_frame=QFrame();header_frame.setObjectName('BinderHeader');header=QHBoxLayout(header_frame);header.setContentsMargins(12,8,12,8);brand=QLabel('MON CLASSEUR');header.addWidget(brand);self.new_binder=self.button('＋ Nouveau classeur',owner.open_main_window);self.new_binder.setAccessibleName('Créer un nouveau classeur');header.addWidget(self.new_binder);self.spaces=ChoiceBox();self.spaces.setAccessibleName('Choisir mon classeur');self.spaces.setMinimumWidth(190);self.spaces.currentIndexChanged.connect(self.switch_space);header.addWidget(self.spaces)
        header.addWidget(QLabel('Fond'));self.opacity_slider=QSlider(Qt.Horizontal);self.opacity_slider.setRange(0,100);self.opacity_slider.setValue(self.background_opacity);self.opacity_slider.setFixedWidth(110);self.opacity_slider.setAccessibleName('Opacité du fond autour du classeur');self.opacity_slider.valueChanged.connect(self.set_background_opacity);header.addWidget(self.opacity_slider);self.opacity_label=QLabel(str(self.background_opacity)+' %');self.opacity_label.setFixedWidth(42);header.addWidget(self.opacity_label)
        self.manage=self.button('⚙',owner.open_main_window);self.manage.setToolTip('Ouvrir Organisator');self.manage.setAccessibleName('Ouvrir Organisator');header.addWidget(self.manage);header.addWidget(self.button('×',self.hide));brand.hide();self.header=header_frame;header_frame.setParent(root)
        self.canvas=BinderCanvas();layout.addWidget(self.canvas,1)
        left=QVBoxLayout(self.canvas.left);left.setContentsMargins(7,0,9,0);left.setSpacing(7)
        self.eyebrow=QLabel('');self.eyebrow.hide()
        self.section_title=QLabel('Mes documents');self.section_title.setWordWrap(True);self.section_title.setStyleSheet('font-size:18pt;font-weight:600;color:#264633;');left.addWidget(self.section_title)
        self.count=QLabel();self.count.hide()
        self.search=QLineEdit();self.search.setPlaceholderText('Rechercher…');self.search.setStyleSheet('QLineEdit {background:transparent;border:none;border-bottom:1px solid #CCD5C4;border-radius:0px;padding:5px 0px;}');self.search.setAccessibleName('Rechercher un document dans cet intercalaire');self.search.textChanged.connect(self.filter_documents);left.addWidget(self.search)
        self.folder=ChoiceBox();self.folder.setAccessibleName('Sous-dossier de l’intercalaire');self.folder.currentIndexChanged.connect(self.filter_documents);left.addWidget(self.folder)
        self.list=QListWidget();self.list.setIconSize(QSize(32,40));self.list.setWordWrap(True);self.list.setAccessibleName('Documents de mon classeur');self.list.currentRowChanged.connect(self.select_row);left.addWidget(self.list,1)
        self.path_hint=QLabel();self.path_hint.hide()
        self.folder_button=self.button('Voir le dossier',self.open_section_folder);self.folder_button.hide()
        right=QVBoxLayout(self.canvas.right);right.setContentsMargins(12,0,10,0);right.setSpacing(5)
        self.document_title=QLabel('');self.document_title.setWordWrap(True);self.document_title.setStyleSheet('font-size:15pt;font-weight:600;');right.addWidget(self.document_title)
        self.kind=QLabel();self.kind.hide()
        self.preview=QStackedWidget();self.preview.setStyleSheet('background:transparent;');self.image=PaperImage();self.text=QPlainTextEdit();self.text.setReadOnly(True);self.preview.addWidget(self.image);self.preview.addWidget(self.text);right.addWidget(self.preview,1)
        leaf_footer=QHBoxLayout();self.position=QLabel();self.position.setStyleSheet('font-size:9pt;color:#70806D;');leaf_footer.addWidget(self.position,1);self.open_button=self.button('Ouvrir  ↗',self.open_document);self.open_button.setObjectName('Primary');self.open_button.setMaximumWidth(160);self.open_button.setEnabled(False);leaf_footer.addWidget(self.open_button);right.addLayout(leaf_footer)
        tab_layout=QVBoxLayout(self.canvas.tabs);tab_layout.setContentsMargins(0,0,0,0);tab_layout.setSpacing(1);self.tabs_layout=QVBoxLayout();self.tabs_layout.setSpacing(1);tab_layout.addLayout(self.tabs_layout);tab_layout.addStretch()
        tab_pager=QFrame();tab_pager.setStyleSheet('QFrame {background:#FAFCF9;border-radius:10px;}');tab_pages=QHBoxLayout(tab_pager);tab_pages.setContentsMargins(3,3,3,3);tab_pages.setSpacing(3);self.tabs_previous=self.button('‹',lambda:self.change_tab_page(-1));self.tabs_next=self.button('›',lambda:self.change_tab_page(1));self.tabs_label=QLabel();self.tabs_label.setAlignment(Qt.AlignCenter);tab_pages.addWidget(self.tabs_previous);tab_pages.addWidget(self.tabs_label,1);tab_pages.addWidget(self.tabs_next);tab_layout.addWidget(tab_pager)
        self.previous=self.button('‹',lambda:self.step(-1));self.next=self.button('›',lambda:self.step(1));self.previous.setAccessibleName('Feuille précédente');self.next.setAccessibleName('Feuille suivante');self.previous.setToolTip('Feuille précédente');self.next.setToolTip('Feuille suivante')
        for button in (self.previous,self.next):button.setParent(self.canvas);button.setStyleSheet('QPushButton {font-size:19pt;padding:0px;min-height:32px;border-radius:19px;background:#FFFFFF;border:1px solid #C4D3C0;}')
        self.canvas.previous_arrow=self.previous;self.canvas.next_arrow=self.next;self.canvas.position_arrows()
        self.status=QLabel(root);self.status.setAlignment(Qt.AlignCenter);self.status.setStyleSheet('font-size:10pt;color:#526A56;background:#FFFFFF;border:1px solid #C4D3C0;border-radius:10px;padding:12px;');self.status.hide()
        QShortcut(QKeySequence('Escape'),self,activated=self.hide);QShortcut(QKeySequence('Right'),self,activated=lambda:self.step(1));QShortcut(QKeySequence('Left'),self,activated=lambda:self.step(-1));self.rebuild_spaces();self.show_empty()
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'header'):
            size=self.header.sizeHint();self.header.setGeometry(max(8,self.width()-size.width()-10),8,size.width(),size.height());self.header.raise_()
        if hasattr(self,'status'):self.status.setGeometry(max(10,(self.width()-550)//2),70,min(550,self.width()-20),70)
    def button(self,text,callback):
        b=QPushButton(text);b.setCursor(Qt.PointingHandCursor);b.setAccessibleName(text);b.clicked.connect(callback);return b
    def rebuild_spaces(self):
        self.spaces.blockSignals(True);self.spaces.clear();entries=self.owner.preferences.get('organizer_spaces',[])
        for entry in entries if isinstance(entries,list) else []:
            if isinstance(entry,dict) and isinstance(entry.get('path'),str):self.spaces.addItem(entry.get('name',Path(entry['path']).name),entry['path'])
        if self.owner.root:
            index=self.spaces.findData(str(self.owner.root))
            if index<0:self.spaces.addItem(self.owner.root.name,str(self.owner.root));index=self.spaces.count()-1
            self.spaces.setCurrentIndex(index)
        self.spaces.setVisible(self.spaces.count()>0);self.spaces.blockSignals(False)
    def switch_space(self,index):
        if index<0:return
        from shared.organizer import load_space
        try:self.owner.use_space(*load_space(self.spaces.itemData(index)));self.reload()
        except (OSError,ValueError,KeyError):self.rebuild_spaces();self.error('Ce classeur est introuvable. Retrouvez-le dans « Gérer ».')
    def reveal(self):
        self.rebuild_spaces();screen=self.owner.screen() or QApplication.primaryScreen();self.setGeometry(screen.geometry());self.showFullScreen();self.clearMask();self.header.show();self.header.raise_();self.raise_();self.activateWindow();self.reload()
    def set_background_opacity(self,value):
        self.background_opacity=value;self.opacity_label.setText(str(value)+' %');self.owner.remember('organizer_binder_opacity',value);self.update()
    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor(21,38,29,round(self.background_opacity*2.55)));p.end()
    def mousePressEvent(self,event):
        point=self.canvas.mapFromGlobal(event.globalPosition().toPoint())
        if event.button()==Qt.LeftButton and self.canvas.rect().contains(point) and not self.canvas.book_rect.contains(point) and not self.canvas.tabs.geometry().contains(point):self.hide()
        else:super().mousePressEvent(event)
    def show_empty(self):
        self.open_button.hide()
        self.section_title.setText('Mes documents');self.eyebrow.setText('');self.path_hint.clear();self.status.hide()
        self.documents=[];self.current=None;self.list.clear();self.search.hide();self.folder.hide();self.folder_button.hide();self.document_title.setText('Votre classeur A4');self.document_title.show();self.text.clear();self.preview.setCurrentWidget(self.text);self.previous.setEnabled(False);self.next.setEnabled(False);self.position.clear();self.sections=[];self.render_tabs()
    def reload(self):
        self.token+=1;self.reload_token+=1;token=self.reload_token;self.root=self.owner.root
        if not self.root:self.show_empty();return
        root=self.root;self.open_button.show();self.open_button.setText('Ouvrir  ↗');self.status.setText('Ouverture du classeur…');self.rebuild_spaces()
        def done(result):
            if self.closing or token!=self.reload_token:return
            self.documents,truncated=result;config=self.owner.config or {};specs=[s for s in config.get('folders',[]) if '/' not in s['path']]
            known={s['path'] for s in specs};extra=sorted({Path(d.relative).parts[0] for d in self.documents if len(Path(d.relative).parts)>1}-known)
            self.sections=[dict(path='',name='Tout le classeur',color='#B4CEB4')]+[dict(path=s['path'],name=s['path'],color=s['color']) for s in specs]+[dict(path=s,name=s,color='#C9C9BA') for s in extra]
            wanted=self.owner.preferences.get('organizer_binder_section','')
            self.set_section(wanted if any(s['path']==wanted for s in self.sections) else '',animate=False)
            self.status.setText('Intercalaire → document → ouvrir : chaque fichier garde sa place.' if not truncated else 'Les 10 000 premiers documents sont affichés. Affinez le classement dans Gérer.')
        background(self,lambda:list_documents(root),done)
    def render_tabs(self):
        while self.tabs_layout.count():
            w=self.tabs_layout.takeAt(0).widget()
            if w:w.hide();w.deleteLater()
        self.tab_buttons={};self.tabs_per_page=16;pages=max(1,(len(self.sections)+15)//16);self.section_page=min(max(0,self.section_page),pages-1)
        for i,s in enumerate(self.sections[self.section_page*16:(self.section_page+1)*16],self.section_page*16):
            b=DividerTab(s['name'],s['color'],i+1,lambda checked=False,path=s['path']:self.set_section(path));b.setChecked(s['path']==self.section);self.tabs_layout.addWidget(b);self.tab_buttons[s['path']]=b
        self.tabs_label.setText(str(self.section_page+1)+' / '+str(pages));self.tabs_previous.parentWidget().setVisible(pages>1);self.tabs_previous.setEnabled(self.section_page>0);self.tabs_next.setEnabled(self.section_page+1<pages)
    def change_tab_page(self,step):self.section_page+=step;self.render_tabs()
    def set_section(self,path,animate=True):
        self.section=path;self.section_page=next((i//16 for i,s in enumerate(self.sections) if s['path']==path),0);self.render_tabs();self.owner.remember('organizer_binder_section',path)
        self.section_title.setText(path or 'Tout le classeur');self.eyebrow.setText((self.owner.config or {}).get('profile','MON CLASSEUR').upper());self.search.show();self.search.blockSignals(True);self.search.clear();self.search.blockSignals(False)
        self.folder.blockSignals(True);self.folder.clear();self.folder.addItem('Tout l’intercalaire','')
        subfolders=sorted({Path(d.relative).parts[1] for d in self.documents if path and Path(d.relative).parts[0]==path and len(Path(d.relative).parts)>2})
        for name in subfolders:self.folder.addItem(name,name)
        self.folder.hide();self.folder.blockSignals(False);self.folder_button.hide();self.filter_documents(animate=animate)
    def filter_documents(self,*args,animate=True):
        query=folded(self.search.text());sub=self.folder.currentData() or ''
        self.visible_documents=[d for d in self.documents if (not self.section or d.relative.startswith(self.section+'/')) and (not sub or d.relative.startswith(self.section+'/'+sub+'/')) and (not query or query in folded(d.relative))]
        self.list.blockSignals(True);self.list.clear()
        for document in self.visible_documents:
            path=Path(document.relative);item=QListWidgetItem(file_icon(path.suffix[1:].lower()),path.stem);item.setData(Qt.UserRole,document);item.setToolTip(document.relative);self.list.addItem(item)
        wanted=self.owner.preferences.get('organizer_binder_document','');index=next((i for i,d in enumerate(self.visible_documents) if d.relative==wanted),0)
        self.list.setCurrentRow(index if self.visible_documents else -1);self.list.blockSignals(False);self.count.setText(str(len(self.visible_documents))+' document'+('s' if len(self.visible_documents)!=1 else ''))
        if self.visible_documents:self.select_row(index,animate=animate)
        else:
            self.token+=1;self.current=None;self.document_title.setText('Aucun document');self.text.clear();self.preview.setCurrentWidget(self.text);self.open_button.setEnabled(False);self.previous.setEnabled(False);self.next.setEnabled(False);self.position.clear();self.path_hint.setText(self.section or self.root.name)
    def select_row(self,index,page=0,animate=True):
        if not 0<=index<len(self.visible_documents):return
        self.canvas.turn.animation.stop();self.canvas.turn.hide();before=self.canvas.grab() if animate and self.isVisible() else None;self.token+=1;token=self.token;document=self.visible_documents[index];root=self.root;direction=-1 if page<0 or (self.current and index<getattr(self,'document_index',0)) or (self.current==document and page<self.page) else 1
        self.current=document;self.document_index=index;self.open_button.setEnabled(False);self.previous.setEnabled(False);self.next.setEnabled(False);self.status.setText('Préparation de la feuille…')
        def done(result):
            if self.closing or token!=self.token:return
            self.status.hide();self.page=result['page'];self.pages=result['pages'];self.document_title.setText(Path(document.relative).stem);self.document_title.setToolTip(document.relative);self.kind.setText(result['kind']);self.path_hint.setText(document.relative.replace('/',' › '));self.open_button.setText('Ouvrir  ↗');self.open_button.setEnabled(True)
            if result['image'] is not None:self.document_title.hide();self.image.display(result['image']);self.preview.setCurrentWidget(self.image)
            else:self.document_title.show();self.text.setPlainText(result['text']);self.text.verticalScrollBar().setValue(0);self.preview.setCurrentWidget(self.text)
            self.position.setText(str(self.page+1)+' / '+str(self.pages));self.previous.setEnabled(self.page>0 or index>0);self.next.setEnabled(self.page+1<self.pages or index+1<len(self.visible_documents));self.owner.remember('organizer_binder_document',document.relative)
            if before is not None and self.owner.orb.animations:
                self.canvas.left.layout().activate();self.canvas.right.layout().activate();after=self.canvas.grab();self.canvas.turn.start(before,after,direction)
        def prepare():
            try:return preview_document(root,document,page)
            except Exception as error:return dict(image=None,text='L’aperçu n’est pas disponible.\n\n'+str(error),kind='Aperçu indisponible',page=0,pages=1)
        background(self,prepare,done)
    def step(self,direction):
        if not self.current:return
        page=self.page+direction;index=self.document_index
        if page<0:index-=1;page=-1
        elif page>=self.pages:index+=1;page=0
        if not 0<=index<len(self.visible_documents):return
        self.list.blockSignals(True);self.list.setCurrentRow(index);self.list.blockSignals(False);self.select_row(index,page)
    def open_document(self):
        if self.root is None:self.owner.open_main_window();return
        if not self.current:return
        try:
            path=inside(self.root,self.root/self.current.relative,True)
            if path.suffix.lower() in ('.exe','.com','.bat','.cmd','.ps1','.vbs','.msi','.lnk','.url','.scr'):raise ValueError('Ce fichier se consulte depuis son dossier, pas dans le classeur.')
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):raise ValueError('Aucune application n’a pu ouvrir ce document.')
        except (OSError,ValueError) as error:self.error(str(error))
    def open_section_folder(self):
        if self.root:
            try:QDesktopServices.openUrl(QUrl.fromLocalFile(str(inside(self.root,self.root/self.section))))
            except (OSError,ValueError) as error:self.error(str(error))
    def error(self,message):
        if not self.closing:self.status.setText(str(message));self.status.show();self.status.raise_()
    def closeEvent(self,event):event.ignore();self.hide()
    def shutdown(self):self.closing=True;self.token+=1;self.reload_token+=1;self.canvas.turn.animation.stop();self.hide()
