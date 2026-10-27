"""Curate genuine OpenStax figures from CC BY historical source snapshots,
and make country situation maps from public-domain Natural Earth geometry.
Third-party credited figures, photographs and unsupported resources are excluded.
"""
from pathlib import Path,PurePosixPath
from zipfile import ZipFile
from io import BytesIO
from defusedxml import ElementTree as ET
from PIL import Image,ImageDraw,ImageFont
import hashlib,json,math,posixpath,re
import cairosvg
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'test-output/library-collections';OUT=ROOT/'assets/library'
(OUT/'licenses').mkdir(exist_ok=True);(OUT/'thumbs').mkdir(exist_ok=True)
catalog=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'))
ids={e['id']for e in catalog};hashes={e['sha256']for e in catalog};source_hashes={e.get('source_sha256')for e in catalog}
def persist():
 p=OUT/'catalog.pending.json';p.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8');p.replace(OUT/'catalog.json')
def save(image,ident,title,category,topic,author,source,license,proof,version,changes,source_hash='',caption=''):
 image=image.convert('RGBA');image.thumbnail((1400,1400));data=BytesIO();image.save(data,format='PNG',compress_level=6);blob=data.getvalue();digest=hashlib.sha256(blob).hexdigest()
 if digest in hashes or ident in ids:return False
 filename=ident+'.png';(OUT/filename).write_bytes(blob);thumb=image.copy();thumb.thumbnail((340,220));tb=BytesIO();thumb.save(tb,format='PNG',compress_level=6);td=tb.getvalue();(OUT/'thumbs'/filename).write_bytes(td)
 e=dict(id=ident,title=title,category=category,topic=topic,tags=f'{category} {topic} {title} {caption}',filename=filename,author=author,license=license,license_url='https://creativecommons.org/licenses/by/4.0/'if license=='CC BY 4.0'else proof,source_url=source,source_timestamp=version,retrieved='2026-10-24',changes=changes,width=image.width,height=image.height,sha256=digest,thumbnail_sha256=hashlib.sha256(td).hexdigest(),source_sha256=source_hash,caption=caption,license_proof_url=proof,embedded=False)
 catalog.append(e);ids.add(ident);hashes.add(digest);source_hashes.add(source_hash);persist();return True
def deny(url,resource_type):
 if str(url).startswith('data:')and len(str(url))<8_000_000:
  from cairosvg.url import fetch
  return fetch(url,resource_type)
 raise ValueError('External SVG reference')
def topic(text,category):
 text=text.lower()
 pairs=[('membrane','Membranes'),('transport','Échanges cellulaires'),('photosynth','Photosynthèse'),('chromosom','Chromosomes'),('dna','ADN et génétique'),('inherit','Génétique'),('genetic','Génétique'),('ecosystem','Écosystèmes'),('ecolog','Écologie'),('evolut','Évolution'),('flower','Fleurs'),('leaf','Feuilles'),('plant','Végétaux'),('fung','Champignons'),('bacter','Microorganismes'),('virus','Microorganismes'),('heart','Cœur et circulation'),('blood','Sang et circulation'),('respirat','Respiration'),('lung','Respiration'),('digest','Digestion'),('nutrition','Nutrition'),('brain','Cerveau'),('neuron','Neurones'),('nervous','Système nerveux'),('muscle','Muscles'),('bone','Squelette'),('skelet','Squelette'),('tissue','Tissus'),('cell','Cellules'),('animal','Biodiversité'),('eye','Vision'),('ear','Audition'),('skin','Peau'),('electri','Électricité'),('circuit','Circuits électriques'),('capacitor','Condensateurs'),('resistor','Résistances'),('magnet','Magnétisme'),('lens','Lentilles'),('mirror','Miroirs'),('refract','Réfraction'),('reflect','Réflexion'),('light','Lumière'),('optic','Optique'),('wave','Ondes'),('sound','Son'),('temperature','Température'),('heat','Chaleur'),('fluid','Fluides'),('pressure','Pression'),('energy','Énergie'),('power','Puissance'),('force','Forces'),('friction','Frottements'),('motion','Mouvement'),('velocity','Vitesse'),('acceleration','Accélération'),('rotation','Rotation'),('torque','Rotation'),('momentum','Quantité de mouvement'),('oscillat','Oscillations'),('gravity','Gravitation'),('measurement','Mesures'),('vectors','Vecteurs')]
 for word,label in pairs:
  if word in text:return label
 return 'Biologie · notions générales'if category=='SVT'else'Physique · notions générales'
def local(tag):return tag.rsplit('}',1)[-1]
collections=[('osbooks-biology-bundle','SVT',320,'Biology 2e et Concepts of Biology'),('osbooks-anatomy-physiology','SVT',230,'Anatomy and Physiology'),('osbooks-university-physics-bundle','Physique-chimie',450,'University Physics')]
for repo,category,quota,book in collections:
 meta=json.loads((SRC/(repo+'.json')).read_text());sha=meta['commit'];license=(SRC/(repo+'-LICENSE.txt')).read_text(encoding='utf-8')
 assert 'Attribution 4.0 International'in license and 'NonCommercial'not in license
 (OUT/'licenses'/(repo+'-'+sha[:12]+'.txt')).write_text(license,encoding='utf-8')
 if not __import__('zipfile').is_zipfile(SRC/(repo+'.zip')):print('AWAITING',repo,flush=True);continue
 prefix='os-'+repo.replace('osbooks-','').replace('-bundle','')+'-'
 added=sum(e['id'].startswith(prefix)for e in catalog);topic_counts={}
 for e in catalog:
  if e['id'].startswith(prefix):topic_counts[e['topic']]=topic_counts.get(e['topic'],0)+1
 with ZipFile(SRC/(repo+'.zip'))as archive:
  names=set(archive.namelist())
  for name in sorted(n for n in names if n.endswith('/index.cnxml')):
   if added>=quota:break
   root=ET.fromstring(archive.read(name));titles=[n for n in root if local(n.tag)=='title'];module_title=' '.join(titles[0].itertext())if titles else''
   module_license=[n.attrib.get('url','')for n in root.iter()if local(n.tag)=='license']
   if module_license and not any('/by/4.0'in url for url in module_license):continue
   module_added=0
   for fig in root.iter():
    if local(fig.tag)!='figure' or added>=quota or module_added>=5:continue
    captions=[n for n in fig if local(n.tag)=='caption'];caption=' '.join(' '.join(n.itertext())for n in captions);caption=re.sub(r'\s+',' ',caption).strip()
    alt=' '.join(n.attrib.get('alt','')for n in fig.iter());desc=caption+' '+alt
    if re.search(r'credit|courtesy|photo|micrograph|reproduc|modified|adapted|copyright|NASA|USGS|NOAA|Wikimedia|Shutterstock|©|reproduct|genital|penis|vagina|testicle|pregnan|fetus|foetus|embryo|cancer|cadaver|quantum|relativ|Schr.dinger|Feynman',desc,re.I):continue
    if any(n.attrib.get('url','').startswith(('http:','https:'))for n in fig.iter()):continue
    images=[n for n in fig.iter()if local(n.tag)=='image'and n.attrib.get('src')]
    if len(images)!=1:continue
    image_path=posixpath.normpath(posixpath.join(posixpath.dirname(name),images[0].attrib['src']))
    if image_path not in names or not image_path.lower().endswith(('.svg','.png','.jpg','.jpeg')):continue
    ident='os-'+repo.replace('osbooks-','').replace('-bundle','')+'-'+hashlib.sha256(image_path.encode()).hexdigest()[:16]
    if ident in ids:continue
    info=archive.getinfo(image_path)
    if info.file_size>12*1024*1024:continue
    raw=archive.read(image_path);raw_hash=hashlib.sha256(raw).hexdigest()
    if raw_hash in source_hashes:continue
    theme=topic(module_title+' '+caption,category)
    if topic_counts.get(theme,0)>=45:continue
    try:
     if image_path.lower().endswith('.svg'):
      if b'<script'in raw.lower()or b'<foreignobject'in raw.lower():continue
      tree=cairosvg.parser.Tree(bytestring=raw,url_fetcher=deny);w=float(tree.get('width','1000').replace('px',''));h=float(tree.get('height','700').replace('px',''))
      scale=1200/max(w,h);data=cairosvg.surface.PNGSurface.convert(bytestring=raw,output_width=max(1,round(w*scale)),output_height=max(1,round(h*scale)),url_fetcher=deny);image=Image.open(BytesIO(data))
     else:
      image=Image.open(BytesIO(raw))
      if image.width*image.height>25_000_000:continue
     if min(image.size)<80 or max(image.size)/min(image.size)>7:continue
     figtitle=next((' '.join(n.itertext()).strip()for n in fig if local(n.tag)=='title'),'')
     display=figtitle or caption or alt or module_title
     display=re.sub(r'\s+',' ',display).strip();display=display if len(display)<=105 else display[:102].rsplit(' ',1)[0]+'…'
     source=f'https://github.com/openstax/{repo}/blob/{sha}/'+image_path.split('/',1)[1]
     proof=f'https://github.com/openstax/{repo}/blob/{sha}/LICENSE'
     if save(image,ident,theme+' — '+display,category,theme,f'OpenStax, Rice University — {book}, auteurs et contributeurs du manuel',source,'CC BY 4.0',proof,meta['date'],'PNG adapté pour l’affichage hors ligne, miniature et classement français ; figure sans crédit tiers explicite, issue de la version historique CC BY 4.0 du manuel.',raw_hash,caption):
      added+=1;module_added+=1;topic_counts[theme]=topic_counts.get(theme,0)+1
      if added%20==0:print('BOOK',repo,added,'TOTAL',len(catalog),flush=True)
    except Exception as e:print('SKIP',image_path,type(e).__name__,str(e)[:80],flush=True)
 print('BOOK COMPLETE',repo,added,topic_counts,flush=True)
# Public-domain Natural Earth data; one genuine regional situation map per feature.
data_path=SRC/'natural-earth-countries.geojson';data=json.loads(data_path.read_text(encoding='utf-8'));data_hash=hashlib.sha256(data_path.read_bytes()).hexdigest()
(OUT/'licenses'/'natural-earth-terms.html').write_bytes((SRC/'natural-earth-terms.html').read_bytes())
def polys(feature):
 g=feature['geometry'];return g['coordinates']if g['type']=='MultiPolygon'else[g['coordinates']]
def points(feature):return[p for poly in polys(feature)for ring in poly for p in ring]
font_path=ROOT/'assets/fonts/NotoSerif-Variable.ttf'
font=ImageFont.truetype(str(font_path),28);small=ImageFont.truetype(str(font_path),15)
for index,feature in enumerate(data['features']):
 props=feature['properties'];country=props.get('NAME_FR')or props.get('ADMIN')or props.get('NAME');ident='ne-country-'+str(props.get('NE_ID',index))
 if ident in ids:continue
 pts=points(feature);xs=[p[0]for p in pts];ys=[p[1]for p in pts];xmin,xmax,ymin,ymax=min(xs),max(xs),min(ys),max(ys)
 if xmax-xmin>180:xmin,xmax,ymin,ymax=-180,180,-60,85
 else:
  dx=max(2.,(xmax-xmin)*.45);dy=max(2.,(ymax-ymin)*.45);xmin=max(-180,xmin-dx);xmax=min(180,xmax+dx);ymin=max(-85,ymin-dy);ymax=min(85,ymax+dy)
 cosine=max(.2,math.cos(math.radians((ymin+ymax)/2)));scale=min(1100/((xmax-xmin)*cosine),625/(ymax-ymin));cw=(xmax-xmin)*cosine*scale;ch=(ymax-ymin)*scale;ox=(1200-cw)/2;oy=80+(650-ch)/2
 def xy(p):return(ox+(p[0]-xmin)*cosine*scale,oy+(ymax-p[1])*scale)
 image=Image.new('RGB',(1200,800),'#edf6fb');draw=ImageDraw.Draw(image)
 def paint(f,fill):
  for poly in polys(f):
   if not poly:continue
   draw.polygon([xy(p)for p in poly[0]],fill=fill,outline='#a5b5c4',width=1)
   for hole in poly[1:]:draw.polygon([xy(p)for p in hole],fill='#edf6fb',outline='#a5b5c4')
 for neighbor in data['features']:paint(neighbor,'#f8fafb')
 paint(feature,'#2496aa')
 draw.rectangle((0,0,1200,69),fill='white');draw.text((35,14),country,font=font,fill='#17314d');draw.text((1125,85),'N ↑',font=small,fill='#17314d')
 draw.rectangle((0,737,1200,800),fill='white');draw.rectangle((35,757,57,779),fill='#2496aa');draw.text((70,754),'Pays / territoire ciblé',font=small,fill='#17314d');draw.text((630,754),'Natural Earth · carte de situation · 1:110m',font=small,fill='#526980')
 save(image,ident,country+' — carte de situation','Cartes','Pays et territoires','Natural Earth — Tom Patterson, Nathaniel Vaughn Kelso et contributeurs', 'https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson','Public domain','https://www.naturalearthdata.com/about/terms-of-use/','Données récupérées le 24/10/2026','Carte de situation réalisée pour Écrinator depuis les géométries Natural Earth 1:110m ; projection équirectangulaire locale, pays ciblé en bleu.',data_hash,country+' '+str(props.get('CONTINENT','')))
print('COMPLETE',len(catalog),{c:sum(e['category']==c for e in catalog)for c in ['Cartes','SVT','Physique-chimie']},flush=True)
