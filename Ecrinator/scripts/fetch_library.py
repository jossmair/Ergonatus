"""Reproducible development-only Commons downloads; nothing is fetched by the app."""
from pathlib import Path
import hashlib, html, json, re, time, urllib.parse, urllib.request
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/library'
OUT.mkdir(parents=True, exist_ok=True)
UA = 'Ecrinator/0.8 (offline educational image library; source and license preserved)'
def get(url):
    if urllib.parse.urlparse(url).hostname not in {'commons.wikimedia.org','upload.wikimedia.org','thumb.wikimedia.org'}:
        raise ValueError('Unexpected download host')
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':UA}),timeout=45) as r:
                data=r.read(16*1024*1024+1)
                if len(data)>16*1024*1024: raise ValueError('Image too large')
                return data
        except Exception as e:
            print(type(e).__name__,str(e)[:160],flush=True)
            if attempt==3: raise
            time.sleep(8*(attempt+1))
def clean(s): return html.unescape(re.sub('<[^>]+>','',s)).strip()
known = [
 ('monde','Planisphère muet','Cartes','BlankMap-World-Equirectangular.svg','monde continents carte muette'),
 ('france-regions','France · régions et départements (2016)','Cartes','France location map-Regions and departements-2016.svg','france régions départements carte muette'),
 ('europe','Europe · carte muette','Cartes','Blank Europe Map.svg','europe pays carte muette'),
 ('afrique','Afrique · carte muette','Cartes','Africa Blank Map.svg','afrique pays carte muette'),
 ('asie','Asie · carte de situation','Cartes','Blank Map-Asia-Locator.svg','asie continents carte muette'),
 ('relief-monde','Relief mondial (2021)','Cartes','Physical Map of the World (2021).svg','relief océans montagnes monde'),
 ('pyrenees','Les Pyrénées · relief','Cartes','Pyrenees topographic map-fr.svg','relief france pyrénées montagnes'),
 ('cellule-animale','Cellule animale · à légender','SVT','Animal Cell Unannotated.svg','cellule animale organites sans légende'),
 ('cellule-vegetale','Cellule végétale','SVT','Plant cell structure-fr.png','cellule végétale chloroplaste français'),
 ('bacterie','Cellule procaryote · à légender','SVT','Prokaryote cell diagram.svg','bactérie cellule procaryote'),
 ('coeur','Le cœur humain','SVT','Diagram of the human heart (cropped)-fr.svg','cœur circulation sang français'),
 ('respiration','Appareil respiratoire','SVT','Respiratory system complete fr.svg','respiration poumon français'),
 ('adn','Structure de l’ADN','SVT','DNA Structure+Key+Labelled.pn NoBB.png','adn génétique'),
 ('fleur','Structure d’une fleur','SVT','Mature flower diagram-fr.svg','fleur reproduction végétal français'),
 ('eau','Molécule d’eau','Physique-chimie','Water-2D-flat.svg','eau molécule chimie H2O'),
 ('atome','Modèle de l’atome','Physique-chimie','Helium atom QM.svg','atome hélium électron noyau'),
 ('prisme','Décomposition de la lumière','Physique-chimie','Prism rainbow schema.svg','optique prisme spectre lumière'),
 ('lentille','Lentille convergente · rayons','Physique-chimie','Lens1.svg','optique lentille convergente rayons'),
 ('circuit-serie','Circuit électrique en série','Physique-chimie','Series circuit.svg','électricité circuit série'),
 ('circuit-parallele','Circuit électrique en dérivation','Physique-chimie','Parallel circuit.svg','électricité circuit dérivation parallèle'),
 ('etats-matiere','États de la matière','Physique-chimie','States of matter En.svg','solide liquide gaz états matière anglais'),
]
catalog=[]
for slug,title,category,filename,tags in known:
    try:
        query={'action':'query','format':'json','prop':'imageinfo','iiprop':'url|extmetadata|size|timestamp','titles':'File:'+filename,'iiurlwidth':1200}
        data=json.loads(get('https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode(query)))
        info=next(iter(data['query']['pages'].values())).get('imageinfo',[{}])[0]
        meta=info.get('extmetadata',{})
        val=lambda k:clean(meta.get(k,{}).get('value',''))
        license=val('LicenseShortName')
        if license not in {'Public domain','CC0','CC BY 4.0','CC BY-SA 4.0','CC BY 3.0','CC BY-SA 3.0'}:
            print('Skip missing/unsupported:',filename,license,flush=True);continue
        url=info.get('thumburl',info['url'])
        ext='.png' if url.split('?')[0].lower().endswith('.png') else '.jpg'
        target=OUT/(slug+ext)
        if not target.exists(): target.write_bytes(get(url))
        with Image.open(target) as img:
            img.verify()
        with Image.open(target) as img: w,h=img.size
        if w*h>12_000_000: raise ValueError('Oversized image')
        entry=dict(id=slug,title=title,category=category,tags=tags,filename=target.name,
            author=val('Artist'),license=license,license_url=val('LicenseUrl'),source_url=info['descriptionurl'],
            download_url=url,source_timestamp=info.get('timestamp',''),retrieved='2026-10-24',
            changes='Vignette PNG/JPEG fournie par Wikimedia Commons, sans autre modification.',
            width=w,height=h,sha256=hashlib.sha256(target.read_bytes()).hexdigest())
        catalog.append(entry)
        (OUT/(slug+'.source.json')).write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
        (OUT/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
        print('OK',slug,license,w,h,flush=True)
    except Exception as e: print('SKIP',filename,type(e).__name__,str(e)[:160],flush=True)
    time.sleep(3)
print('TOTAL',len(catalog),flush=True)
