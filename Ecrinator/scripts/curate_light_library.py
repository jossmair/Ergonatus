"""Create the default, small collège library from licensed downloaded vectors.
Geographic outlines use actual IGN/Etalab and Natural Earth data. No invented borders.
"""
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from collections import Counter
from xml.etree import ElementTree as ET
from shapely.geometry import shape,box,Polygon,MultiPolygon
from shapely.ops import unary_union
from PIL import Image
import json,hashlib,math,re,html,shutil
import cairosvg
from shapely import make_valid,set_precision
def geometry(f):return set_precision(make_valid(shape(f["geometry"])),.00001).buffer(0)
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/library';SRC=ROOT/'test-output/light-sources'
backup=OUT/'catalog-advanced.json'
if not backup.exists():shutil.copyfile(OUT/'catalog.json',backup)
old=json.loads(backup.read_text(encoding='utf-8'));catalog=[e for e in old if e.get('embedded',True)]
for e in catalog:e.update(level='college',kind='Illustration',monochrome=False,unlabelled=('à légender'in e['title']),subjects=[e['category']])
seen={e['sha256']for e in catalog};(OUT/'sources/light').mkdir(parents=True,exist_ok=True);(OUT/'licenses/light').mkdir(parents=True,exist_ok=True)
def deny(url,kind):raise ValueError('External SVG resource forbidden')
def save(svg,ident,title,category,topic,author,license,source,changes,subjects=None,kind='Schéma',proof='',unlabelled=True):
 if isinstance(svg,str):svg=svg.encode('utf-8')
 if len(svg)>2_000_000:raise ValueError('Vector too large')
 tree=ET.fromstring(svg)
 if any(n.tag.rsplit('}',1)[-1]in ['script','foreignObject']for n in tree.iter()):raise ValueError('Unsupported SVG element')
 png=cairosvg.surface.PNGSurface.convert(bytestring=svg,output_width=1050,url_fetcher=deny)
 image=Image.open(BytesIO(png)).convert('RGBA');white=Image.new('RGBA',image.size,'white');white.alpha_composite(image)
 # Two colours, not a large RGB bitmap. Keep the imported source SVG separately.
 image=white.convert('L').point(lambda p:0 if p<200 else 255,mode='1')
 if max(image.size)>1400:image.thumbnail((1400,1400))
 data=BytesIO();image.save(data,format='PNG',optimize=True);data=data.getvalue();sha=hashlib.sha256(data).hexdigest()
 if sha in seen:return
 assert len(data)<160_000,(title,len(data));seen.add(sha);filename=ident+'.png';(OUT/filename).write_bytes(data)
 thumb=image.copy();thumb.thumbnail((300,195));buf=BytesIO();thumb.save(buf,format='PNG',optimize=True);td=buf.getvalue();(OUT/'thumbs'/filename).write_bytes(td)
 (OUT/'sources/light'/(ident+'.svg')).write_bytes(svg)
 catalog.append(dict(id=ident,title=title,category=category,topic=topic,tags=f'{title} {topic} collège noir blanc sans légende à compléter',filename=filename,author=author,license=license,license_url={'CC BY-SA 4.0':'https://creativecommons.org/licenses/by-sa/4.0/','CC BY-SA 3.0':'https://creativecommons.org/licenses/by-sa/3.0/','CC BY-SA 2.5':'https://creativecommons.org/licenses/by-sa/2.5/','CC BY 4.0':'https://creativecommons.org/licenses/by/4.0/','CC BY 3.0':'https://creativecommons.org/licenses/by/3.0/','Public domain':'https://www.naturalearthdata.com/about/terms-of-use/','CC0':'https://creativecommons.org/publicdomain/zero/1.0/','Licence Ouverte 2.0':'https://www.etalab.gouv.fr/licence-ouverte-open-licence/','MIT':'https://opensource.org/license/mit/'}[license],source_url=source,source_timestamp='25/10/2026',changes=changes,width=image.width,height=image.height,sha256=sha,thumbnail_sha256=hashlib.sha256(td).hexdigest(),source_sha256=hashlib.sha256(svg).hexdigest(),license_proof_url=proof or source,embedded=False,level='college',kind=kind,monochrome=True,unlabelled=unlabelled,subjects=subjects or [category]))
def rings(g):
 if g.is_empty:return []
 if g.geom_type=='Polygon':return[list(g.exterior.coords),*[list(r.coords)for r in g.interiors]]
 if hasattr(g,'geoms'):return[r for poly in g.geoms for r in rings(poly)]
 return []
def project(x,y,france=False):
 if not france:return(x,-y)
 phi=math.radians(y);e=.0818191910428;n=.725607765053267;iso=math.log(math.tan(math.pi/4+phi/2)*((1-e*math.sin(phi))/(1+e*math.sin(phi)))**(e/2));r=11754255.426096*math.exp(-n*iso);gamma=n*math.radians(x-3)
 return(700000+r*math.sin(gamma),-(12655612.049876-r*math.cos(gamma)))
def map_svg(geometries,viewport=None,france=False,grid=False):
 geoms=[g.intersection(box(*viewport))if viewport else g for g in geometries];allrings=[r for g in geoms for r in rings(g)];pts=[project(x,y,france)for ring in allrings for x,y,*_ in ring]
 if not pts:return None
 xmin,xmax=min(p[0]for p in pts),max(p[0]for p in pts);ymin,ymax=min(p[1]for p in pts),max(p[1]for p in pts);w,h=1050,790;scale=min(950/max(.001,xmax-xmin),690/max(.001,ymax-ymin));ox=(w-(xmax-xmin)*scale)/2;oy=(h-(ymax-ymin)*scale)/2
 chunks=['<svg xmlns="http://www.w3.org/2000/svg" width="1050" height="790" viewBox="0 0 1050 790">','<rect width="1050" height="790" fill="white"/>']
 if grid:
  for x in range(75,1000,75):chunks.append(f'<path d="M{x} 35V755" stroke="black" stroke-width=".6" stroke-dasharray="2 5"/>')
  for y in range(75,755,75):chunks.append(f'<path d="M35 {y}H1015" stroke="black" stroke-width=".6" stroke-dasharray="2 5"/>')
 for g in geoms:
  path=[]
  for ring in rings(g):
   p=[project(x,y,france)for x,y,*_ in ring];path.append('M'+'L'.join(f'{ox+(x-xmin)*scale:.2f},{oy+(y-ymin)*scale:.2f}'for x,y in p)+'Z')
  chunks.append('<path d="'+' '.join(path)+'" fill="white" fill-rule="evenodd" stroke="black" stroke-width="1.2" stroke-linejoin="round"/>')
 chunks.append('</svg>');return ''.join(chunks)
def geo_save(geometries,ident,title,topic,france=False,viewport=None,grid=False,official=True):
 svg=map_svg(geometries,viewport,france,grid)
 if svg:save(svg,ident,title,'Cartes',topic,'IGN / Etalab — contours administratifs 2026'if official else'Natural Earth — Tom Patterson, Nathaniel Vaughn Kelso et contributeurs','Licence Ouverte 2.0'if official else'Public domain','https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/2026/geojson/'if official else'https://www.naturalearthdata.com/','Fond scolaire sans noms, tracé depuis les géométries téléchargées ; rendu monochrome, simplification 1000 m pour la France, généralisation 1:110m pour le monde.',subjects=['Histoire-géographie','Cartes'],kind='Fond de carte',proof='https://github.com/datagouv/decoupage-administratif#licence'if official else'https://www.naturalearthdata.com/about/terms-of-use/')
departments=json.loads((SRC/'departements.geojson').read_text(encoding='utf-8'))['features'];regions=json.loads((SRC/'regions.geojson').read_text(encoding='utf-8'))['features']
metropole=[f for f in regions if len(str(f['properties']['code']))==2 and not str(f['properties']['code']).startswith('0')];metropole=[f for f in metropole if shape(f['geometry']).bounds[0]>-10 and shape(f['geometry']).bounds[2]<15]
deps=[f for f in departments if len(str(f['properties']['code']))==2]
region_geoms=[geometry(f)for f in metropole];dep_geoms=[geometry(f)for f in deps];whole=unary_union(region_geoms)
for key,geometries,label in [('contour',[whole],'Contour seul'),('regions',region_geoms,'Régions'),('departements',dep_geoms,'Départements')]:
 geo_save(geometries,'college-france-'+key,'France métropolitaine — '+label,'France · fonds vierges',True)
 geo_save(geometries,'college-france-'+key+'-grille','France métropolitaine — '+label+' et quadrillage','France · fonds vierges',True,grid=True)
for f in metropole:
 code=str(f['properties']['code']);name=f['properties']['nom'];g=geometry(f);inside=[geometry(d)for d in deps if geometry(d).intersects(g)and geometry(d).intersection(g).area>.03]
 geo_save([g],'college-region-'+code,name+' — contour à compléter','France · régions',True)
 if inside:geo_save([d.intersection(g)for d in inside],'college-region-'+code+'-departements',name+' — départements sans noms','France · régions',True)
for f in deps:
 code=str(f['properties']['code']);name=f['properties']['nom'];g=geometry(f)
 geo_save([g],'college-departement-'+code,name+' — contour à compléter','France · départements',True)
# Overseas contours remain in their own view; never mix latitudes into the mainland map.
for f in regions:
 if f in metropole:continue
 geo_save([geometry(f)],'college-outremer-'+str(f['properties']['code']),f['properties']['nom']+' — contour vierge','France · outre-mer')
world=json.loads((ROOT/'test-output/library-collections/natural-earth-countries.geojson').read_text(encoding='utf-8'))['features'];wg=[geometry(f)for f in world]
for slug,title,extent in [('monde','Monde',(-180,-58,180,85)),('europe','Europe',(-25,33,45,72)),('mediterranee','Méditerranée',(-12,25,42,50)),('afrique','Afrique',(-20,-36,53,38)),('asie','Asie',(25,-11,155,75)),('amerique-nord','Amérique du Nord',(-170,5,-50,78)),('amerique-sud','Amérique du Sud',(-83,-57,-33,15)),('proche-orient','Proche-Orient',(20,10,62,45))]:
 for borders in [False,True]:geo_save(wg if borders else[unary_union(wg)],'college-fond-'+slug+('-frontieres'if borders else'-contours'),title+' — '+('frontières actuelles sans noms'if borders else'contours sans frontières'),'Monde · fonds vierges',viewport=extent,official=False)
# Actual OpenMoji BLACK vectors, pinned to release 17.0.0. Not anatomical diagrams.
groups=[('SVT','Le vivant',{'1F52C':'Microscope','1F9EC':'ADN','1F9EB':'Boîte de Petri','1F331':'Jeune pousse','1F332':'Arbre résineux','1F333':'Arbre feuillu','1F334':'Palmier','1F335':'Cactus','1F337':'Tulipe','1F338':'Fleur','1F339':'Rose','1F33B':'Tournesol','1F33C':'Fleur à pétales','1F33D':'Maïs','1F33E':'Épi','1F33F':'Feuilles','2618':'Trèfle','1F341':'Feuille','1F342':'Feuille tombée','1F343':'Feuille au vent','1F344':'Champignon','1F9A0':'Microbe','1F9B4':'Os','1F9B7':'Dent','1F441':'Œil','1F442':'Oreille','1F9E0':'Cerveau','1FAC0':'Cœur anatomique','1FAC1':'Poumons','1F4A7':'Goutte d’eau','1F30B':'Volcan','1F30D':'Globe Europe et Afrique','1F319':'Croissant de Lune','2600':'Soleil','2601':'Nuage','1F327':'Pluie','2744':'Flocon','1F41C':'Fourmi','1F41D':'Abeille','1F98B':'Papillon','1F40C':'Escargot','1F41B':'Chenille','1FAB1':'Ver','1F41E':'Coccinelle','1F577':'Araignée','1F438':'Grenouille','1F422':'Tortue','1F40D':'Serpent','1F41F':'Poisson','1F426':'Oiseau','1F40E':'Cheval','1F404':'Vache','1F411':'Mouton','1F407':'Lapin','1F408':'Chat','1F415':'Chien','1F43F':'Écureuil','1F987':'Chauve-souris'}),
('Physique-chimie','Matériel et phénomènes',{'1F9EA':'Tube à essai','2697':'Alambic','1F9F2':'Aimant','1F50B':'Pile','1FAAB':'Pile déchargée','1F50C':'Prise électrique','1F4A1':'Ampoule','1F321':'Thermomètre','1F525':'Flamme','1F9CA':'Glaçons','2696':'Balance','1F526':'Lampe de poche','1F506':'Lumière','1F308':'Arc-en-ciel','1F9EF':'Extincteur','1F97D':'Lunettes de protection','1F97C':'Blouse','26A1':'Électricité','2622':'Radioactivité','2623':'Risque biologique','26A0':'Attention','1F6B0':'Robinet','1F9F4':'Flacon','1F6E2':'Récipient','1F9FC':'Savon'}),
('Technologie','Objets et techniques',{'2699':'Engrenage','1F527':'Clé','1F528':'Marteau','1FA9B':'Tournevis','1F529':'Vis et écrou','1F6E0':'Outils','1F5DC':'Étau','1F5A5':'Ordinateur','1F4BB':'Ordinateur portable','2328':'Clavier','1F5B1':'Souris','1F5A8':'Imprimante','1F4BE':'Disquette','1F4BF':'Disque','1F916':'Robot','1F4F7':'Appareil photo','1F50D':'Loupe','1F9F0':'Boîte à outils','1F3ED':'Usine','1F3D7':'Grue','1F6F0':'Satellite','1F680':'Fusée','1F6B2':'Vélo','1F697':'Voiture','1F3E0':'Maison','1F4F1':'Téléphone'}),
('Éducation musicale','Instruments et musique',{'1F3B5':'Note de musique','1F3B6':'Notes de musique','1F3BC':'Partition','1F3B9':'Piano','1F3B8':'Guitare','1F3BA':'Trompette','1F3BB':'Violon','1F3B7':'Saxophone','1FA88':'Flûte','1F941':'Tambour','1FA98':'Percussions','1F3A4':'Microphone','1F3A7':'Casque','1FA97':'Accordéon','1FA95':'Banjo','1FA89':'Harpe'}),
('Arts plastiques','Arts et objets à dessiner',{'1F3A8':'Palette','1F58C':'Pinceau','1F58D':'Crayon de couleur','270F':'Crayon','1F58A':'Stylo','1F58B':'Plume','1F4D0':'Équerre','1F4CF':'Règle','2702':'Ciseaux','1F9F5':'Fil','1F9F6':'Laine','1F5BC':'Cadre','1F3AD':'Masques de théâtre','1F3FA':'Amphore','1F5FF':'Sculpture','1FAA8':'Pierre'}),
('EMC','Vivre ensemble',{'1F91D':'Coopération','1F54A':'Colombe','1F5F3':'Vote','1F4AC':'Parole','1F465':'Groupe','1F3DB':'Institution','1F3EB':'École','1F6B8':'Passage piéton','1F6A6':'Feu de circulation','1F6D1':'Arrêt','267B':'Recyclage','1F30E':'Planète'}),
('Français','Lire et raconter',{'1F4D6':'Livre ouvert','1F4DA':'Livres','1F4D3':'Cahier','1F4DD':'Prise de notes','1F4DC':'Parchemin','1F5DE':'Journal','1F4F0':'Article','1F3F0':'Château','1F451':'Couronne','1F5DD':'Clé','1F56F':'Bougie','1F381':'Cadeau','1F3D9':'Ville','1F332':'Forêt'}),
('Langues','Objets du quotidien',{'1F34E':'Pomme','1F350':'Poire','1F34C':'Banane','1F34A':'Orange','1F353':'Fraise','1F347':'Raisin','1F955':'Carotte','1F345':'Tomate','1F954':'Pomme de terre','1F35E':'Pain','1F9C0':'Fromage','1F95A':'Œuf','1F95B':'Lait','1F375':'Tasse','1F37D':'Assiette','1F374':'Couverts','1F392':'Sac à dos','1F453':'Lunettes','1F455':'Tee-shirt','1F456':'Pantalon','1F9E3':'Écharpe','1F9E4':'Gants','1F9E6':'Chaussettes','1F9E5':'Manteau','1F45E':'Chaussure','1F452':'Chapeau','1F68C':'Bus','1F682':'Train','2708':'Avion','1F6A2':'Bateau','1F6E3':'Route','1F3D6':'Plage','1F3D4':'Montagne','1F3DC':'Désert','1F6CF':'Lit','1FA91':'Chaise','1F6AA':'Porte','1FA9F':'Fenêtre','1F4A4':'Sommeil','1F567':'Horloge','1F9F3':'Valise'})]
meta={e['hexcode']:e for e in json.loads((SRC/'openmoji.json').read_text(encoding='utf-8'))};z=ZipFile(SRC/'openmoji-svg-black.zip');available=set(z.namelist())
for category,topic,entries in groups:
 for code,title in entries.items():
  file=code+'.svg'
  if file not in available:continue
  info=meta.get(code,{});svg=z.read(file);subjects=[category,'Anglais','Espagnol','Allemand','Langues']
  save(svg,'college-om-'+code.lower(),title+' — dessin à légender',category,topic,'OpenMoji — '+info.get('openmoji_author','HfG Schwäbisch Gmünd et contributeurs'),'CC BY-SA 4.0',f'https://github.com/hfg-gmuend/openmoji/blob/17.0.0/black/svg/{file}','SVG noir officiel téléchargé ; rendu PNG bicolore compact. Pictogramme pédagogique, pas un schéma anatomique détaillé.',subjects,kind='Pictogramme',proof='https://github.com/hfg-gmuend/openmoji/tree/17.0.0#license')
# A small set of verified Commons vectors: retain historic dates and source metadata.
commons=SRC/'commons/records.json'
if commons.exists():
 for e in json.loads(commons.read_text(encoding='utf-8')):
  try:
   raw=(SRC/'commons'/(e['id']+'.svg')).read_bytes();tree=ET.fromstring(raw)
   for parent in tree.iter():
    for child in list(parent):
     if child.tag.rsplit('}',1)[-1]in ['text','title','desc']:parent.remove(child)
   clean=lambda value:html.unescape(re.sub('<[^>]+>',' ',value)).strip()
   fields=e['info']['extmetadata'];lic=fields['LicenseShortName']['value'];author=clean(fields.get('Artist',{}).get('value','Wikimedia Commons'))
   title=e['title'][5:].removesuffix('.svg');svg=ET.tostring(tree)
   save(svg,'college-commons-'+e['id'],title,e['category'],'Histoire · fonds historiques'if re.search(r'17\d\d|18\d\d|19\d\d',title)else'France · fonds vierges',author,lic,'https://commons.wikimedia.org/wiki/'+e['title'].replace(' ','_'),'SVG téléchargé, textes retirés quand présents ; rendu monochrome compact, contours et géométrie conservés.',subjects=['Cartes','Histoire-géographie'],kind='Fond de carte',proof='https://commons.wikimedia.org/wiki/'+e['title'].replace(' ','_'))
  except Exception as error:print('COMMONS SKIP',e['title'],str(error),flush=True)
for filename in ['openmoji-LICENSE.txt','openmoji-README.md','etalab-README.md']:
 shutil.copyfile(SRC/filename,OUT/'licenses/light'/filename)
for filename in ['departements.geojson','regions.geojson','openmoji-release.json']:
 shutil.copyfile(SRC/filename,OUT/'sources/light'/filename)
(OUT/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
print('LIGHT CATALOG',len(catalog),dict(Counter(e['category']for e in catalog)),flush=True)
