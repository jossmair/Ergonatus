"""Development-only curation of an offline, licensed school image collection.
Downloads original files with polite backoff. Does not run inside Écrinator.
SVGs are rasterised locally with external references disabled.
"""
from pathlib import Path
from io import BytesIO
import concurrent.futures, hashlib, html, itertools, json, re, threading, time, unicodedata, urllib.parse, urllib.request
from PIL import Image
import cairosvg
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/library'
SOURCES=ROOT/'test-output/library-originals'
SOURCES.mkdir(parents=True,exist_ok=True)
(OUT/'sources').mkdir(exist_ok=True)
(OUT/'thumbs').mkdir(exist_ok=True)
UA='Ecrinator/0.9 offline-school-catalog (local educational curation, user requested)'
LICENSES={'Public domain','CC0','CC BY 4.0','CC BY-SA 4.0','CC BY 3.0','CC BY-SA 3.0','CC BY 2.5','CC BY-SA 2.5','CC BY 2.0','CC BY-SA 2.0'}
TARGET=800
CAPS={'Cartes':200,'SVT':240,'Physique-chimie':240,'Mathématiques':120,'Technologie':60}
TOPICS={
'Cartes':[
('Monde','world blank map'),('Continents','continent map blank'),('France','France map regions departments'),('Europe','Europe countries map blank'),('Afrique','Africa map blank'),('Asie','Asia map blank'),('Amériques','America map blank'),('Océanie','Oceania map blank'),('Relief','France topographic map'),('Climats','world climate map'),('Pays','country location map'),('Projections','world map projection'),('France','France relief map'),('Hydrographie','world rivers map'),('Population','world population map'),('Pays','country blank map')],
'SVT':[
('Cellules','cell diagram'),('Cellules végétales','plant cell diagram'),('Cœur et circulation','human heart diagram'),('Respiration','respiratory system diagram'),('Digestion','digestive system diagram'),('Squelette','human skeleton diagram'),('Muscles','muscle tissue diagram'),('Cerveau','human brain diagram'),('Neurones','neuron diagram'),('Photosynthèse','photosynthesis diagram'),('Fleurs','flower anatomy diagram'),('Feuilles','leaf anatomy diagram'),('ADN','DNA structure diagram'),('Génétique','chromosome diagram'),('Écosystèmes','ecosystem diagram'),('Réseaux alimentaires','food chain diagram'),('Volcans','volcano diagram'),('Tectonique','plate tectonics diagram'),('Cycle de l’eau','water cycle diagram'),('Bactéries','bacteria structure diagram'),('Biodiversité','animal classification diagram'),('Roches','rock cycle diagram'),('Division cellulaire','mitosis diagram'),('Nutrition','plant root structure diagram')],
'Physique-chimie':[
('Circuits électriques','simple electric circuit diagram'),('Symboles électriques','electrical circuit symbols'),('Forces','force diagram mechanics'),('Lentilles','lens ray diagram'),('Réflexion et réfraction','light refraction reflection diagram'),('Lumière et couleurs','prism spectrum diagram'),('Magnétisme','magnetic field diagram'),('Atomes','electron shell diagram'),('Molécules','molecule water diagram'),('États de la matière','states of matter diagram'),('Énergie','energy conversion diagram'),('Ondes','wave diagram'),('Son','sound wave diagram'),('Pression','pressure diagram'),('Température','thermometer diagram'),('Mesures','measurement instrument diagram'),('Éléments chimiques','periodic table elements'),('Liaisons chimiques','chemical bonding diagram'),('Circuits électriques','series parallel circuit diagram'),('Mécanique','lever pulley diagram'),('Électricité','electric current voltage diagram'),('Énergie solaire','solar energy diagram')],
'Mathématiques':[
('Fractions','fraction diagram'),('Triangles','triangle geometry diagram'),('Quadrilatères','quadrilateral geometry diagram'),('Angles','angle geometry diagram'),('Cercles','circle geometry diagram'),('Solides','geometric solid net diagram'),('Symétrie','reflection symmetry geometry'),('Diagrammes','pie chart diagram'),('Repérage','coordinate plane diagram'),('Pythagore','Pythagorean theorem diagram'),('Volumes','volume geometry diagram'),('Droites','parallel perpendicular lines diagram')],
'Technologie':[
('Engrenages','gear mechanism diagram'),('Transmission','pulley belt mechanism diagram'),('Robotique','robot diagram'),('Algorithmes','simple flowchart diagram'),('Énergie solaire','solar panel diagram'),('Informatique','computer hardware diagram'),('Mécanismes','mechanical linkage diagram'),('Électronique','breadboard simple diagram')]
}
lock=threading.Lock();last_request=0.
def get(url):
    global last_request
    host=urllib.parse.urlparse(url).hostname
    if host not in {'commons.wikimedia.org','upload.wikimedia.org','thumb.wikimedia.org'}:raise ValueError('Unexpected host')
    for attempt in range(5):
        with lock:
            pause=1.2-(time.monotonic()-last_request)
            if pause>0:time.sleep(pause)
            last_request=time.monotonic()
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':UA}),timeout=45)as r:
                if urllib.parse.urlparse(r.geturl()).hostname not in {'commons.wikimedia.org','upload.wikimedia.org','thumb.wikimedia.org'}:raise ValueError('Unexpected redirect')
                data=r.read(12*1024*1024+1)
                if len(data)>12*1024*1024:raise ValueError('Source too large')
                return data
        except urllib.error.HTTPError as e:
            if e.code not in (429,500,502,503,504) or attempt==4:raise
            delay=max(int(e.headers.get('Retry-After','0')or'0'),15*(attempt+1))
            print('Backoff',e.code,delay,flush=True);time.sleep(min(delay,120))
        except (TimeoutError,urllib.error.URLError):
            if attempt==4:raise
            time.sleep(5*(attempt+1))
def clean(s):return html.unescape(re.sub('<[^>]+>',' ',s)).strip()
def val(info,key):return clean(info.get('extmetadata',{}).get(key,{}).get('value',''))
def allowed(title,info):
    name=title[5:].lower()
    if not name.endswith(('.svg','.png','.jpg','.jpeg')):return False
    if re.search(r'[-_ ](?:ar|fa|ru|zh|ja|ko|hi|bn|ta|uk|sr|he|el|pl|cs|de|es|pt|it|nl|tr)(?:[-_ .]|$)',name):return False
    if sum(ord(c)>0x2ff for c in name)>2:return False
    if any(k in name for k in ['feynman','relativity','tensor','quantum field','autopsy','cadaver','porn','penis','vagina','vulva','testicle','fetus dissection','higher derivative','manifold','kerr black']):return False
    if val(info,'LicenseShortName')not in LICENSES:return False
    if not val(info,'Artist') and val(info,'LicenseShortName')not in {'CC0','Public domain'}:return False
    w,h=info.get('width',0),info.get('height',0)
    return w>15 and h>15 and max(w/h,h/w)<7
def denied_reference(url,resource_type):
    if str(url).startswith('data:') and len(str(url))<8_000_000:
        from cairosvg.url import fetch
        return fetch(url,resource_type)
    raise ValueError('External SVG references are disabled')
def fetch_one(page,category,topic):
    title=page['title'];info=page['imageinfo'][0];pid=str(page['pageid']);ident='commons-'+pid
    filename=ident+'.png';target=OUT/filename
    try:
        original=SOURCES/(ident+Path(title[5:]).suffix.lower())
        if not original.exists():original.write_bytes(get(info['url']))
        data=original.read_bytes();w,h=info['width'],info['height']
        if title.lower().endswith('.svg'):
            if b'<script' in data.lower() or b'<foreignobject' in data.lower():raise ValueError('Unsupported SVG content')
            scale=1200/max(w,h)
            png=cairosvg.surface.PNGSurface.convert(bytestring=data,output_width=max(1,round(w*scale)),output_height=max(1,round(h*scale)),url_fetcher=denied_reference)
            image=Image.open(BytesIO(png)).convert('RGBA')
        else:
            image=Image.open(BytesIO(data));image.seek(0);image=image.convert('RGBA');image.thumbnail((1400,1400))
        if image.width<80 or image.height<60:raise ValueError('Insufficient image size')
        output=BytesIO();image.save(output,format='PNG',compress_level=6);png=output.getvalue();target.write_bytes(png)
        thumbnail=image.copy();thumbnail.thumbnail((340,220));thumb=BytesIO();thumbnail.save(thumb,format='PNG',compress_level=6);thumb_data=thumb.getvalue();(OUT/'thumbs'/filename).write_bytes(thumb_data)
        description=re.sub(r'\.(?:svg|png|jpe?g)$','',title[5:],flags=re.I).replace('_',' ')
        description=re.sub(r'^\d{3,5}\s+','',description)
        entry=dict(id=ident,title=f'{topic} — {description}',category=category,topic=topic,tags=f'{topic} {category} {description}',filename=filename,
            author=val(info,'Artist') or 'Auteur non renseigné sur la fiche source',license=val(info,'LicenseShortName'),license_url=val(info,'LicenseUrl'),source_url=info['descriptionurl'],
            source_timestamp=info.get('timestamp',''),retrieved='2026-10-24',changes='Conversion technique du fichier source en PNG et miniature ; références externes SVG désactivées.',
            width=image.width,height=image.height,sha256=hashlib.sha256(png).hexdigest(),source_sha256=hashlib.sha256(data).hexdigest(),thumbnail_sha256=hashlib.sha256(thumb_data).hexdigest(),embedded=False,source_title=title)
        (OUT/'sources'/(ident+'.json')).write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
        return entry
    except Exception as e:print('SKIP',title,type(e).__name__,str(e)[:110],flush=True);return None
catalog=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'))
seen_titles={e.get('source_title')or urllib.parse.unquote(e['source_url']).split('/wiki/')[-1].replace('_',' ') for e in catalog}
seen_hashes={e['sha256']for e in catalog}
for e in catalog:
    if e.get('embedded',True):
        e['embedded']=True;e.setdefault('topic',{'Cartes':'Cartes de référence','SVT':'Schémas de référence','Physique-chimie':'Schémas de référence'}.get(e['category'],'Références'))
        im=Image.open(OUT/e['filename']).convert('RGBA');im.thumbnail((340,220));buf=BytesIO();im.save(buf,format='PNG');tb=buf.getvalue();(OUT/'thumbs'/e['filename']).write_bytes(tb);e['thumbnail_sha256']=hashlib.sha256(tb).hexdigest()
def persist():
    temp=OUT/'catalog.pending.json';temp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(OUT/'catalog.json')
persist()
ordered=[]
for row in itertools.zip_longest(*[[(cat,*t)for t in topics]for cat,topics in TOPICS.items()]):ordered.extend(t for t in row if t)
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
    for category,topic,query in ordered:
        if len(catalog)>=TARGET:break
        count=sum(e['category']==category for e in catalog)
        if count>=CAPS[category]:continue
        params=dict(action='query',format='json',generator='search',gsrsearch=query,gsrnamespace=6,gsrlimit=50,prop='imageinfo',iiprop='url|extmetadata|size|timestamp')
        try:pages=json.loads(get('https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode(params))).get('query',{}).get('pages',{}).values()
        except Exception as e:print('QUERY FAILED',query,type(e).__name__,str(e)[:90],flush=True);continue
        selected=[]
        quota=min(25,CAPS[category]-count,TARGET-len(catalog))
        for page in pages:
            title=page.get('title','');info=page.get('imageinfo',[{}])[0]
            if title in seen_titles or not allowed(title,info):continue
            seen_titles.add(title);selected.append(page)
            if len(selected)>=quota:break
        for entry in pool.map(lambda p:fetch_one(p,category,topic),selected):
            if not entry or entry['sha256'] in seen_hashes:continue
            catalog.append(entry);seen_hashes.add(entry['sha256']);persist()
            print('OK',len(catalog),category,topic,entry['title'][:100],flush=True)
        print('TOPIC',query,'TOTAL',len(catalog),flush=True)
print('COMPLETE',len(catalog),{c:sum(e['category']==c for e in catalog)for c in CAPS},flush=True)
