"""Original code-drawn coloured folder artwork and Windows folder decoration."""
from pathlib import Path
import os,shutil

def generate_icons(destination):
    from PySide6.QtCore import Qt,QRectF
    from PySide6.QtGui import QImage,QPainter,QPainterPath,QColor,QPen,QLinearGradient
    from shared.organizer import COLORS
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    for color in COLORS:
        image=QImage(256,256,QImage.Format_ARGB32_Premultiplied);image.fill(Qt.transparent)
        p=QPainter(image);p.setRenderHint(QPainter.Antialiasing);base=QColor(color)
        p.setPen(Qt.NoPen);p.setBrush(QColor(0,0,0,36));p.drawRoundedRect(QRectF(21,64,219,165),20,20)
        path=QPainterPath();path.moveTo(19,63);path.quadTo(19,49,35,49);path.lineTo(91,49);path.lineTo(112,68);path.lineTo(219,68);path.quadTo(235,68,235,84);path.lineTo(235,199);path.quadTo(235,218,216,218);path.lineTo(38,218);path.quadTo(19,218,19,200);path.closeSubpath()
        p.setBrush(base.darker(135));p.drawPath(path)
        p.setBrush(QColor('#F6F4EE'));p.drawRoundedRect(QRectF(40,80,169,90),8,8)
        gradient=QLinearGradient(30,94,225,218);gradient.setColorAt(0,base.lighter(112));gradient.setColorAt(1,base.darker(112))
        p.setBrush(gradient);p.setPen(QPen(base.lighter(140),2));p.drawRoundedRect(QRectF(18,101,220,118),17,17)
        p.setPen(QPen(QColor(255,255,255,100),3,Qt.SolidLine,Qt.RoundCap));p.drawLine(37,113,218,113)
        p.setPen(QPen(QColor(255,255,255,190),5,Qt.SolidLine,Qt.RoundCap));p.drawLine(48,176,91,176);p.end()
        stem='folder-'+color[1:].lower()
        if not image.save(str(destination/(stem+'.ico')),'ICO'):raise OSError('Création des icônes impossible.')
        image.save(str(destination/(stem+'.png')))

def install_icons(root,specs,assets):
    root=Path(root);icons=root/'.organisator/icons';icons.mkdir(exist_ok=True);warnings=[]
    for spec in specs:
        name='folder-'+spec['color'][1:].lower()+'.ico';source=assets/name;target=icons/name
        try:
            if not source.is_file():raise OSError('Icône absente')
            if not target.exists():shutil.copy2(source,target)
            folder=root/spec['path'];relative=os.path.relpath(target,folder).replace('/','\\')
            ini=folder/'desktop.ini'
            with ini.open('x',encoding='utf-16',newline='') as stream:stream.write('[.ShellClassInfo]\r\nIconResource='+relative+',0\r\n')
            if os.name=='nt':
                import ctypes
                kernel=ctypes.windll.kernel32
                kernel.GetFileAttributesW.argtypes=[ctypes.c_wchar_p];kernel.GetFileAttributesW.restype=ctypes.c_uint32
                kernel.SetFileAttributesW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32];kernel.SetFileAttributesW.restype=ctypes.c_int
                for path,bits in ((ini,2|4),(folder,1),(root/'.organisator',2)):
                    previous=kernel.GetFileAttributesW(str(path))
                    if previous==0xffffffff or not kernel.SetFileAttributesW(str(path),previous|bits):raise OSError('Attributs Windows non appliqués')
        except OSError as error:warnings.append(spec['path']+' : '+str(error))
    if os.name=='nt':
        import ctypes
        shell=ctypes.windll.shell32;shell.SHChangeNotify(0x08000000,0,None,None)
    return warnings
