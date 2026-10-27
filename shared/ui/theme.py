"""Stable identities; audited legacy accents take precedence over proposed palette."""
from pathlib import Path
import sys
APP_THEMES = {
    'ergonatus': dict(name='Ergonatus', accent='#253B70', icon='◎', description='Votre centre de contrôle', folder='Hub'),
    'claviernator': dict(name='Claviernator', accent='#81E2C6', icon='⌨', description='Clavier adapté et défilement', folder='Claviernator'),
    'precisionator': dict(name='Precisionator', accent='#9164E8', icon='⌕', description='Loupe dynamique et précision', folder='Precisionator'),
    'transcrinator': dict(name='Transcrinator', accent='#D5914E', icon='♩', description='Dictée vocale locale', folder='Transcrinator'),
    'redactor': dict(name='Redactor', accent='#C84448', icon='✎', description='Rédiger, reformuler ou résumer avec une IA locale.', folder='Redactor'),
    'scanator': dict(name='Scanator', accent='#D84C86', icon='▣', description='Capturer une zone de l’écran et récupérer son texte.', folder='Scanator'),
    'ecrinator': dict(name='Écrinator', accent='#0B57ED', icon='¶', description='Écrire et mettre en page ses cours.', folder='Ecrinator'),
    'organisator': dict(name='Organisator', accent='#368453', icon='▤', description='Classer ses fichiers et consulter son classeur.', folder='Organisator'),
    'lector': dict(name='Lector', accent='#6C9F36', icon='♫', description='Faire lire un texte à voix haute.', folder='Lector'),
    'applinator': dict(name='Applinator', accent='#008FB7', icon='▧', description='Lancer ses applications favorites.', folder='Applinator'),
    'temporator': dict(name='Temporator', accent='#DB6850', icon='◷', description='Voir le temps restant avec un minuteur.', folder='Temporator'),
    'concentrator': dict(name='Concentrator', accent='#5758B8', icon='⊙', description='Assombrir l’écran autour d’une zone de travail.', folder='Concentrator'),
    'pdfinator': dict(name='PDFinator', accent='#5D49DF', icon='▥', description='Lire, annoter et modifier les PDF.', folder='PDFinator'),
    'calculinator': dict(name='Calculinator', accent='#487DA1', icon='±', description='Calculer avec des fractions ou des expressions.', folder='Calculinator'),
    'communicator': dict(name='Communicator', accent='#AE4FA6', icon='☏', description='Exprimer ses besoins avec des cartes et une voix.', folder='Communicator'),
    'memorinator': dict(name='Memorinator', accent='#36A68B', icon='◇', description='Créer, déplacer et annoter ses notes.', folder='Memorinator'),
    'planinator': dict(name='Planinator', accent='#A77A38', icon='▦', description='Organiser ses journées, ses cours et ses devoirs.', folder='Planinator'),
    'traductor': dict(name='Traductor', accent='#249BCB', icon='⇄', description='Traduire des messages et écouter leur traduction.', folder='Traductor'),
    'corrector': dict(name='Corrector', accent='#159B64', icon='✓', description='Corriger l’orthographe et la grammaire d’un texte.', folder='Corrector'),
    'dictionnator': dict(name='Dictionnator', accent='#326B9E', icon='Aa', description='Trouver les définitions d’un mot, hors ligne et sans IA.', folder='Dictionnator'),
    'explicator': dict(name='Explicator', accent='#C07726', icon='?', description='Comprendre un exercice par indices, sans sa solution.', folder='Explicator'),
    'tablinator': dict(name='Tablinator', accent='#218C83', icon='×', description='Toutes les tables de 1 à 12 avec des cases à retourner.', folder='Tablinator'),
}

def stylesheet(dark=True, large=False, accent='#253B70'):
    def tint(base,amount):
        return '#'+''.join(f'{round(int(base[i:i+2],16)*(1-amount)+int(accent[i:i+2],16)*amount):02x}' for i in (1,3,5))
    bg, surface, text, muted, line = ('#0D1519','#17252B','#F0F5F7','#B4C4CB','#43545F') if dark else ('#F2F5F8','#FFFFFF','#182530','#485A68','#8294A1')
    if dark:bg=tint('#0B0D11',.05);surface=tint('#181A20',.12);line=tint('#34343D',.24)
    button=tint('#18242A',.25) if dark else surface
    if system_high_contrast():bg=surface='#000000';text=muted=line='#FFFFFF'
    root=Path(__file__).resolve().parents[2]
    if getattr(sys,'frozen',False):
        root=next((p for p in Path(sys.executable).resolve().parents if (p/'assets/orbs/ergonatus.png').exists()),root)
    check=(root/'assets/check.svg').as_posix()
    switch_on=(root/'assets/switch-on.svg').as_posix();switch_off=(root/'assets/switch-off.svg').as_posix()
    return f'''
    QWidget {{font: {12 if large else 10}pt 'Segoe UI'; color:{text};background:{bg};}}
    QMainWindow,QDialog {{background:{bg};}}
    QWidget#ErgoBackdrop {{background:transparent;}}
    QFrame#WindowHeader {{background:transparent;}}
    QWidget#ErgoBackdrop > QLabel {{color:#F0F5F7;}}
    QFrame#Card {{background:{surface};border:1px solid {line};border-radius:14px;}}
    QLabel {{background:transparent;border:none;}}
    QLabel#Muted {{color:{muted};}}
    QLabel#Title {{font-size:24pt;font-weight:600;}}
    QPushButton,QComboBox,QLineEdit,QSpinBox,QDateTimeEdit {{background:{surface};border:1px solid {line};border-radius:10px;padding:6px 10px;min-height:28px;}}
    QPushButton {{background:{button};}}
    QPushButton#CompactAction {{min-height:18px;padding:4px 10px;border-radius:9px;}}
    QPlainTextEdit,QTextEdit,QListWidget {{background:{surface};color:{text};border:1px solid {line};border-radius:14px;padding:10px;selection-background-color:{accent};}}
    QLineEdit#CalculatorDisplay {{font-size:18pt;padding:8px;}}
    QPushButton#CalculatorKey {{font-size:18pt;font-weight:600;}}
    QPushButton#CalculatorOperator {{font-size:20pt;color:{text};background:{button};border:1px solid {accent};}}
    QLabel#CalculatorResult {{font-size:26pt;font-weight:600;}}
    QPushButton:hover {{border-color:#78AFFF;}}
    QPushButton:focus,QComboBox:focus,QLineEdit:focus,QSpinBox:focus,QCheckBox:focus {{border:3px solid #3971C4;}}
    QPushButton:disabled {{color:{muted};}}
    QScrollArea {{border:none;background:transparent;}}
    QCheckBox {{spacing:10px;min-height:44px;background:transparent;}}
    QCheckBox::indicator {{width:44px;height:24px;background:{surface};border:1px solid {line};border-radius:12px;image:url('{switch_off}');}}
    QCheckBox::indicator:checked {{background:{button};border:1px solid {accent};image:url('{switch_on}');}}
    QCheckBox::indicator:disabled {{border-color:{line};}}
    QSlider::groove:horizontal {{height:8px;background:{line};border-radius:4px;}}
    QSlider::sub-page:horizontal {{background:{accent};border-radius:4px;}}
    QSlider::handle:horizontal {{width:24px;margin:-8px 0;background:{accent};border:1px solid {text};border-radius:12px;}}
    QSlider::groove:vertical {{width:8px;background:{line};border-radius:4px;}}
    QSlider::handle:vertical {{height:24px;margin:0 -8px;background:{text};border:2px solid {line};border-radius:12px;}}
    QSlider:focus {{border:3px solid #3971C4;border-radius:6px;}}
    QRadioButton {{spacing:10px;min-height:44px;}}
    QRadioButton::indicator {{width:24px;height:24px;border:2px solid {muted};border-radius:13px;background:{surface};}}
    QRadioButton::indicator:checked {{background:#649BEE;border:6px solid {surface};}}
    QRadioButton:focus {{border:3px solid #3971C4;}}
    QProgressBar {{min-height:20px;border:1px solid {line};border-radius:6px;text-align:center;background:{surface};}}
    QProgressBar::chunk {{background:#649BEE;border-radius:5px;}}
    QScrollBar:vertical {{width:16px;background:{bg};}}
    QScrollBar::handle:vertical {{background:{line};min-height:36px;border-radius:7px;}}
    QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {{background:{bg};border:none;}}
    QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{height:0px;border:none;}}
    QScrollBar:horizontal {{height:16px;background:{bg};}}
    QScrollBar::handle:horizontal {{background:{line};min-width:36px;border-radius:7px;}}
    QScrollBar::add-page:horizontal,QScrollBar::sub-page:horizontal {{background:{bg};border:none;}}
    QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal {{width:0px;border:none;}}
    QAbstractScrollArea::corner {{background:{bg};border:none;}}
    QListWidget::item {{min-height:44px;padding:4px;}}
    QTabWidget::pane {{border:1px solid {line};background:{bg};border-radius:10px;}}
    QTabBar::tab {{padding:12px 20px;background:{surface};color:{text};border:1px solid {line};}}
    QTabBar::tab:selected {{border-bottom:3px solid #649BEE;}}
    QToolTip {{background:{surface};color:{text};border:1px solid {line};padding:8px;}}
    QMenu {{background:{surface};color:{text};border:1px solid {line};border-radius:12px;padding:6px;}}
    QMenu::item {{padding:8px 16px;min-height:24px;border-radius:7px;}}
    QMenu::item:selected {{background:{button};color:{text};}}
    QMenu::separator {{height:1px;background:{line};margin:5px 10px;}}
    '''

def accent_button_style(accent):
    return 'QPushButton {border:2px solid '+accent+';} QPushButton:focus {border:3px solid #3971C4;}'

def system_high_contrast():
    if sys.platform!='win32':return False
    import ctypes
    from ctypes import wintypes
    class HighContrast(ctypes.Structure):
        _fields_=[('size',wintypes.UINT),('flags',wintypes.DWORD),('scheme',wintypes.LPWSTR)]
    info=HighContrast();info.size=ctypes.sizeof(info)
    return bool(ctypes.windll.user32.SystemParametersInfoW(0x42,info.size,ctypes.byref(info),0) and info.flags&1)
