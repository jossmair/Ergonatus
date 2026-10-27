"""Original SVG presentation assets; supplied application captures stay unchanged."""
from pathlib import Path
from xml.etree import ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'release/assets'
OUT.mkdir(exist_ok=True)
logo = (ROOT/'assets/pdfinator.svg').read_text(encoding='utf-8')
inner = logo.split('>', 1)[1].rsplit('</svg>', 1)[0]
banner = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="360" viewBox="0 0 1280 360">
<defs>
 <linearGradient id="bg" x2="1" y2="1"><stop stop-color="#101a30"/><stop offset="1" stop-color="#23204c"/></linearGradient>
 <linearGradient id="edge"><stop stop-color="#5a8dff"/><stop offset="1" stop-color="#a885ff"/></linearGradient>
 <radialGradient id="glow"><stop stop-color="#7161ed" stop-opacity=".32"/><stop offset="1" stop-color="#7161ed" stop-opacity="0"/></radialGradient>
</defs>
<rect width="1280" height="360" rx="24" fill="url(#bg)"/>
<ellipse cx="1070" cy="160" rx="360" ry="290" fill="url(#glow)"/>
<path d="M0 322H1280" stroke="url(#edge)" stroke-opacity=".22"/>
<g opacity=".1" fill="none" stroke="#adbcff"><rect x="1000" y="-60" width="180" height="245" rx="22" transform="rotate(20 1090 65)"/><rect x="1080" y="160" width="180" height="245" rx="22" transform="rotate(20 1170 282)"/></g>
<g transform="translate(50 72) scale(.73)">{inner}</g>
<g font-family="Segoe UI,Arial,sans-serif">
 <text x="280" y="120" font-size="64" font-weight="750" fill="#ffffff">PDFinator</text>
 <text x="283" y="178" font-size="34" font-weight="600" fill="#c4d5ff">Lisez. Modifiez. Organisez.</text>
 <text x="284" y="222" font-size="21" fill="#aab6d0">Votre espace de travail PDF, sur Windows.</text>
 <rect x="284" y="252" width="98" height="33" rx="16" fill="#ffffff" fill-opacity=".08"/>
 <text x="333" y="274" text-anchor="middle" font-size="15" fill="#eff3ff">Gratuit</text>
 <rect x="393" y="252" width="110" height="33" rx="16" fill="#ffffff" fill-opacity=".08"/>
 <text x="448" y="274" text-anchor="middle" font-size="15" fill="#eff3ff">Hors ligne</text>
 <rect x="514" y="252" width="126" height="33" rx="16" fill="#ffffff" fill-opacity=".08"/>
 <text x="577" y="274" text-anchor="middle" font-size="15" fill="#eff3ff">Sans compte</text>
 <text x="1230" y="344" text-anchor="end" font-size="13" letter-spacing="2" fill="#94a3c9">WINDOWS 10 / 11 · V1.0</text>
</g></svg>'''
(OUT/'banniere.svg').write_text(banner, encoding='utf-8')
for name, title, detail, color in [
    ('installateur', 'Installer PDFinator', 'WINDOWS · EXE · 9,5 Mo', '#5061ed'),
    ('portable', 'Version portable', 'SANS INSTALLATION · ZIP · 10,7 Mo', '#192941'),
]:
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="620" height="144" viewBox="0 0 620 144">
<rect x="1" y="1" width="618" height="142" rx="20" fill="{color}" stroke="#8294ff" stroke-opacity=".35" stroke-width="2"/>
<rect x="24" y="31" width="78" height="78" rx="20" fill="#ffffff" fill-opacity=".1"/>
<path d="M63 48V80M49 66L63 80L77 66M44 87V95H82V87" fill="none" stroke="#ffffff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
<g font-family="Segoe UI,Arial,sans-serif" fill="#ffffff"><text x="124" y="68" font-size="30" font-weight="700">{title}</text><text x="126" y="103" font-size="17" letter-spacing="1" opacity=".8">{detail}</text></g>
</svg>'''
    (OUT/f'telecharger-{name}.svg').write_text(svg, encoding='utf-8')
for path in OUT.glob('*.svg'):
    ET.parse(path)
print('SVG presentation assets generated and XML-validated.')
