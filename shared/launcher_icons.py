"""Original scalable pictograms for apps without a usable native Windows icon."""
from PySide6.QtCore import Qt,QRectF,QByteArray
from PySide6.QtGui import QPixmap,QPainter,QIcon
from PySide6.QtSvg import QSvgRenderer

def native_app_icon(path):
    """Ask Windows for the application artwork without shortcut-arrow overlays."""
    import ctypes,os
    from ctypes import wintypes
    from PySide6.QtGui import QImage
    if os.name!='nt':return QIcon()
    class FileInfo(ctypes.Structure):
        _fields_=[('icon',wintypes.HICON),('index',ctypes.c_int),('attributes',wintypes.DWORD),('name',wintypes.WCHAR*260),('type',wintypes.WCHAR*80)]
    shell=ctypes.windll.shell32;user=ctypes.windll.user32
    shell.SHGetFileInfoW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,ctypes.POINTER(FileInfo),ctypes.c_uint,ctypes.c_uint];shell.SHGetFileInfoW.restype=ctypes.c_size_t
    user.DestroyIcon.argtypes=[wintypes.HICON];user.DestroyIcon.restype=wintypes.BOOL
    info=FileInfo()
    if not shell.SHGetFileInfoW(str(path),0,ctypes.byref(info),ctypes.sizeof(info),0x100) or not info.icon:return QIcon()
    try:return QIcon(QPixmap.fromImage(QImage.fromHICON(int(info.icon))))
    finally:user.DestroyIcon(info.icon)

def app_pictogram(name,category=''):
    name=name.casefold()
    designs=[
        (('calcul','calculator'), '#3F82BA','<rect x="5" y="2" width="14" height="20" rx="3"/><path d="M8 6h8M8 11h1m6 0h1m-8 4h1m6 0h1m-8 4h1m6 0h1"/>'),
        (('music','musique','vocal','enregistreur'), '#A963B7','<path d="M10 17V5l10-3v12M10 8l10-3"/><ellipse cx="6.5" cy="18" rx="3.5" ry="3"/><ellipse cx="16.5" cy="15" rx="3.5" ry="3"/>'),
        (('photo','camera','caméra','paint'), '#3D9B90','<rect x="2" y="4" width="20" height="16" rx="3"/><circle cx="8" cy="9" r="2"/><path d="m3 18 5-5 4 3 4-6 5 7"/>'),
        (('video','vidéo','media','média','clipchamp','vlc'), '#C8774B','<rect x="2" y="4" width="20" height="16" rx="4"/><path d="m10 8 6 4-6 4z"/>'),
        (('mail','courrier','outlook'), '#457FBE','<rect x="2" y="4" width="20" height="16" rx="3"/><path d="m3 6 9 7 9-7"/>'),
        (('calendrier','horloge','calendar'), '#BA7059','<rect x="3" y="4" width="18" height="18" rx="3"/><path d="M3 10h18M8 2v5m8-5v5m-9 7h2m5 0h2m-9 4h2m5 0h2"/>'),
        (('note','word','writer','to do'), '#688CC5','<path d="M6 2h9l4 4v16H6zM14 2v6h5M9 12h7m-7 4h7"/>'),
        (('edge','chrome','firefox','internet'), '#388FA6','<circle cx="12" cy="12" r="10"/><ellipse cx="12" cy="12" rx="4" ry="10"/><path d="M2 12h20M4 6h16M4 18h16"/>'),
        (('chat','teams','whatsapp','skype','communication'), '#756CB5','<path d="M5 3h14a3 3 0 0 1 3 3v9a3 3 0 0 1-3 3h-8l-6 4v-4a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3zM7 9h10m-10 4h6"/>'),
        (('excel','calc','tableur'), '#428B72','<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M3 9h18M9 3v18M3 15h18m6-6h12"/>'),
        (('store','appareils','fichier','explorer'), '#478CA1','<path d="M3 7h7l2 3h9v10H3zM4 7V4h7l2 3h7v3"/>'),
        (('jeu','games','xbox','solitaire'), '#778E4B','<path d="M6 7h12l4 10c1 4-4 5-6 0H8c-2 5-7 4-6 0zM6 10v5m-2-2h4m8-2h1m2 3h1"/>'),
    ]
    _,color,paths=next((d for d in designs if any(word in name+' '+category.casefold() for word in d[0])),((), '#4F88A0','<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>'))
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 80 80"><rect x="2" y="2" width="76" height="76" rx="22" fill="{color}"/><rect x="3" y="3" width="74" height="74" rx="21" fill="none" stroke="#FFFFFF" stroke-opacity=".2"/><g transform="translate(20 20) scale(1.66)" fill="none" stroke="#FFFFFF" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{paths}</g></svg>'
    image=QPixmap(96,96);image.fill(Qt.transparent);painter=QPainter(image);painter.setRenderHint(QPainter.Antialiasing);QSvgRenderer(QByteArray(svg.encode())).render(painter,QRectF(0,0,96,96));painter.end();return QIcon(image)
