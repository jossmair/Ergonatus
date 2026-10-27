"""Code-native SVG Orb family: large semantic glyphs, original identity colors."""
from pathlib import Path
import shutil
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter,QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import Qt
from shared.ui.theme import APP_THEMES
app=QApplication([])
OUT=ROOT/'assets/orbs/clear';OUT.mkdir(exist_ok=True)
GLYPHS={
'ergonatus':'<rect x="19" y="19" width="11" height="11" rx="2" fill="white"/><rect x="35" y="19" width="11" height="11" rx="2" fill="white"/><rect x="19" y="35" width="11" height="11" rx="2" fill="white"/><rect x="35" y="35" width="11" height="11" rx="2" fill="white"/>',
'claviernator':'<rect x="14" y="21" width="36" height="24" rx="4"/><path d="M21 28h2m8 0h2m8 0h2M21 34h2m8 0h2m8 0h2M24 40h16"/>',
'precisionator':'<circle cx="28" cy="27" r="12"/><path d="m37 37 12 12M22 27h12m-6-6v12"/>',
'transcrinator':'<rect x="26" y="14" width="12" height="24" rx="6" fill="white"/><path d="M20 30v2a12 12 0 0 0 24 0v-2M32 44v7m-8 0h16"/>',
'redactor':'<path d="m17 42-2 10 10-3 24-24-8-8zM36 22l8 8M15 53h34"/>',
'scanator':'<path d="M14 25V14h11m14 0h11v11m0 14v11H39m-14 0H14V39M23 25h18M23 32h18M23 39h12"/>',
'ecrinator':'<path d="M32 21c-6-6-15-6-21-3v30c8-3 15-2 21 3 6-5 13-6 21-3V18c-6-3-15-3-21 3zM32 21v30M17 26h9m-9 7h9m12-7h9m-9 7h9"/>',
'organisator':'<path d="M13 23v-6h15l5 6h18v26H13z"/><path d="M20 34h24m-24 8h17"/>',
'lector':'<path d="M16 27h8l11-10v30L24 37h-8z" fill="white"/><path d="M42 25a12 12 0 0 1 0 14m5-20a20 20 0 0 1 0 26"/>',
'applinator':'<path d="M18 20h28v27H18zM15 15h34M26 27l14 7-14 7z"/>',
'temporator':'<circle cx="32" cy="35" r="17"/><path d="M32 35V24m0 11 9 6M26 11h12m-6 0v6m16 1 4 4"/>',
'concentrator':'<circle cx="32" cy="32" r="19"/><circle cx="32" cy="32" r="10"/><circle cx="32" cy="32" r="3" fill="white"/>',
'pdfinator':'<path d="M19 12h18l10 10v30H19zM37 12v12h10"/><text x="32" y="43" fill="white" stroke="none" text-anchor="middle" font-family="Segoe UI" font-size="13" font-weight="bold">PDF</text>',
'calculinator':'<rect x="18" y="12" width="29" height="41" rx="4"/><path d="M24 20h17M25 30h2m11 0h2m-15 8h2m11 0h2m-15 8h2m11 0h2"/>',
'communicator':'<path d="M13 16h38v26H30L19 51v-9h-6z"/><path d="M23 29h1m8 0h1m8 0h1" stroke-width="5"/>',
'memorinator':'<path d="M16 14h32v25L35 52H16zM35 52V39h13M23 24h18M23 31h13"/>',
'planinator':'<rect x="14" y="18" width="36" height="32" rx="4"/><path d="M14 28h36M23 13v11m18-11v11M24 36h2m11 0h2m-15 8h2m11 0h2"/>',
'traductor':'<path d="M12 21h23m-11-7v7m-8 1c3 11 9 17 18 20m-4-20c-3 10-8 16-17 20M38 49l8-24 8 24m-13-8h10"/>',
'corrector':'<path d="M16 32l11 12 22-26" stroke-width="6"/><path d="M16 52h32"/>'}
GLYPHS.update({
'dictionnator':'<path d="M14 17h16c5 0 8 3 8 7v26c-3-3-6-4-10-4H14zM38 24c0-4 4-7 12-7v29c-5 0-9 1-12 4M20 26h9m-9 8h9"/>',
'explicator':'<path d="M23 39c0-5-7-7-7-16a16 16 0 0 1 32 0c0 9-7 11-7 16zM24 46h16m-13 6h10M28 24a5 5 0 1 1 7 5c-3 2-3 3-3 5"/><circle cx="32" cy="38" r="1" fill="white"/>',
 'tablinator':'<rect x="13" y="13" width="38" height="38" rx="6"/><path d="M13 32h38M32 13v38M20 20l6 6m0-6-6 6M39 22h5m-23 18h5m13 0h5m-5 5h5"/>'})
selected=set(sys.argv[1:])
for key,theme in APP_THEMES.items():
    if selected and key not in selected:continue
    color=QColor(theme['accent']);dark=color.darker(145).name();bright=color.lighter(110).name()
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 64 64"><defs><linearGradient id="orb" x1="0" y1="0" x2="0.7" y2="1"><stop stop-color="{bright}"/><stop offset="1" stop-color="{dark}"/></linearGradient></defs><circle cx="32" cy="32" r="30" fill="url(#orb)" stroke="{theme["accent"]}" stroke-width="2"/><path d="M12 20a25 25 0 0 1 40 0" fill="none" stroke="white" stroke-opacity=".18" stroke-width="2"/><g fill="none" stroke="white" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round">{GLYPHS[key]}</g></svg>'
    (OUT/(key+'.svg')).write_text(svg,encoding='utf-8');image=QImage(256,256,QImage.Format_ARGB32_Premultiplied);image.fill(Qt.transparent);p=QPainter(image);QSvgRenderer(svg.encode()).render(p);p.end();assert image.save(str(OUT/(key+'.png')));assert image.save(str(OUT/(key+'.ico')),'ICO')
(OUT/'README.txt').write_text('Orbs vectorielles Ergonatus, 24 octobre 2026. Sources SVG + PNG/ICO dérivés. Glyphes simplifiés pour 36 px ; les couleurs APP_THEMES sont conservées. Aucun modèle génératif nécessaire pour ces symboles déterministes.\n',encoding='utf-8')
for asset in OUT.iterdir():
    if selected and asset.stem not in selected:continue
    if asset.suffix in ('.png','.ico'):shutil.copy2(asset,ROOT/'assets/orbs'/asset.name)
shutil.copy2(OUT/'ergonatus.png',ROOT/'assets/orbs/ergonatus-orb.png')
print(str(len(selected) if selected else len(APP_THEMES))+' Orbs claires exportées')
