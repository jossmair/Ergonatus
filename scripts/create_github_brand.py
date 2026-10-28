"""Deterministic vector branding, using the suite's existing application icons."""
from pathlib import Path
import os,base64,sys
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtGui import QGuiApplication,QImage,QPainter,QFontDatabase
from PySide6.QtSvg import QSvgRenderer
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/media';OUT.mkdir(parents=True,exist_ok=True)
app=QGuiApplication([])
for name in ('segoeui.ttf','seguisb.ttf','segoeuib.ttf'):
    assert QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)>=0,name
def icon(key,x,y,size):
    value=base64.b64encode((ROOT/'assets/orbs'/f'{key}.png').read_bytes()).decode()
    return f'<image x="{x}" y="{y}" width="{size}" height="{size}" href="data:image/png;base64,{value}"/>'
def export(name,svg,width,height,scale=1):
    svg=svg.replace('Segoe UI,Arial,sans-serif','Segoe UI')
    (OUT/(name+'.svg')).write_text(svg,encoding='utf-8');renderer=QSvgRenderer(svg.encode());assert renderer.isValid()
    image=QImage(width*scale,height*scale,QImage.Format_ARGB32_Premultiplied);image.fill(0);p=QPainter(image);renderer.render(p);p.end();assert image.save(str(OUT/(name+'.png')))
cards=''
for i,(key,title) in enumerate([('ecrinator','Écrinator'),('communicator','Communicator'),('corrector','Corrector'),('planinator','Planinator'),('explicator','Explicator'),('tablinator','Tablinator')]):
    x=724+(i%3)*158;y=152+(i//3)*159
    cards+=f'<rect x="{x}" y="{y+5}" width="140" height="140" rx="24" fill="#061426" opacity=".2"/><rect x="{x}" y="{y}" width="140" height="140" rx="24" fill="#FFFFFF" fill-opacity=".07" stroke="#FFFFFF" stroke-opacity=".18"/>'+icon(key,x+41,y+24,58)+f'<text x="{x+70}" y="{y+111}" text-anchor="middle" font-size="16" fill="#FFFFFF">{title}</text>'
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="600" viewBox="0 0 1280 600">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#12203A"/><stop offset=".6" stop-color="#142E42"/><stop offset="1" stop-color="#164B48"/></linearGradient></defs>
<rect width="1280" height="600" rx="28" fill="url(#bg)"/><circle cx="1220" cy="-30" r="300" fill="#70DCC2" opacity=".06"/><circle cx="800" cy="650" r="320" fill="#58A1D0" opacity=".06"/>
<g font-family="Segoe UI,Arial,sans-serif">{icon('ergonatus',58,43,54)}<text x="128" y="80" font-size="27" letter-spacing="3" font-weight="600" fill="#FFFFFF">ERGONATUS</text>
<text x="64" y="157" font-size="14" letter-spacing="3" fill="#A7DCCD">UNE SUITE POUR VOTRE QUOTIDIEN</text>
<text x="60" y="245" font-size="64" font-weight="600" fill="#FFFFFF">Vos outils.</text><text x="60" y="326" font-size="64" font-weight="600" fill="#A7E5D2">À votre rythme.</text>
<text x="64" y="386" font-size="23" fill="#D7E3EE">Apprendre, communiquer et s’organiser</text><text x="64" y="422" font-size="23" fill="#D7E3EE">avec une suite Windows locale.</text>
<rect x="64" y="479" width="132" height="43" rx="21" fill="#A7E5D2"/><text x="130" y="507" text-anchor="middle" font-size="17" font-weight="600" fill="#153A38">21 outils</text>
<rect x="210" y="479" width="146" height="43" rx="21" fill="#FFFFFF" fill-opacity=".07" stroke="#FFFFFF" stroke-opacity=".2"/><text x="283" y="507" text-anchor="middle" font-size="17" fill="#E4EDF4">Sur votre PC</text>
<rect x="370" y="479" width="184" height="43" rx="21" fill="#FFFFFF" fill-opacity=".07" stroke="#FFFFFF" stroke-opacity=".2"/><text x="462" y="507" text-anchor="middle" font-size="17" fill="#E4EDF4">À personnaliser</text>
{cards}<text x="952" y="509" text-anchor="middle" font-size="17" fill="#B9D6D6">Un hub. Des aides à portée de clic.</text></g></svg>'''
export('ergonatus-banner',svg,1280,600)
for name,label,background,foreground in [('download-installer','Installer la suite','#253B70','#FFFFFF'),('download-portable','Choisir le portable','#DDF4EB','#17463D')]:
    s=f'''<svg xmlns="http://www.w3.org/2000/svg" width="244" height="52" viewBox="0 0 244 52"><rect x="1" y="1" width="242" height="50" rx="12" fill="{background}"/><g stroke="{foreground}" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M27 15v16m-6-6 6 6 6-6M18 34v4h18v-4"/></g><text x="137" y="33" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-weight="600" font-size="17" fill="{foreground}">{label}</text></svg>'''
    export(name,s,244,52,2)
print('Brand banner and download buttons exported.')
