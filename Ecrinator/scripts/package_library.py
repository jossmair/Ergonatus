"""Verify all offline assets and create the distributable, data-only ZIP pack."""
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
from PIL import Image,ImageOps,ImageDraw,ImageFont
from io import BytesIO
from collections import Counter
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/library'
catalog=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'))
assert catalog
coordinate_exclusions=set(json.loads((OUT/'reference/sesamath/COORDINATE-EXCLUSIONS.json').read_text(encoding='utf-8'))['ids'])
assert not any(e['id']in coordinate_exclusions for e in catalog), 'Ambiguous cropped labels must stay excluded'
assert all(not e['id'].startswith(('college-atlas-','college-om-','college-departement-','college-region-')) for e in catalog)
assert any(e['id'].startswith('sesamath-') and e.get('grades') for e in catalog)
# Domain-specific, word-boundary matching avoids e.g. "near" becoming Audition.
physics=[(r'capacitor|capacitance','Condensateurs'),(r'resistor|resistance|ohm','Résistances'),(r'circuit|kirchhoff','Circuits électriques'),(r'magnet|induct|solenoid','Magnétisme'),(r'electri|charge|coulomb|potential difference','Électricité'),(r'refract|snell','Réfraction'),(r'reflect|mirror','Réflexion et miroirs'),(r'lens|optic','Optique et lentilles'),(r'light|photon','Lumière'),(r'\bsound\b|acoustic|\bear\b|hearing','Son'),(r'\bwave|interference|diffraction','Ondes'),(r'thermo|temperature|\bheat\b|entropy','Chaleur et température'),(r'fluid|buoyan|bernoulli','Fluides'),(r'pressure|pascal','Pression'),(r'friction','Frottements'),(r'gravit|orbit|planet','Gravitation'),(r'\bforce|newton|tension','Forces'),(r'momentum|collision|impulse','Quantité de mouvement'),(r'\benergy|\bwork\b|\bpower','Énergie et puissance'),(r'torque|rotat|angular','Rotation'),(r'oscillat|pendulum|spring','Oscillations'),(r'vector|component','Vecteurs'),(r'velocity|acceleration|speed|motion|displacement|trajectory','Mouvement'),(r'\bunit|measurement|uncertainty','Mesures et unités')]
biology=[(r'photosynth','Photosynthèse'),(r'chromosom|meiosis|mitosis','Chromosomes et division'),(r'\bdna\b|\brna\b|genetic|inherit|allele|transcription|translation','ADN et génétique'),(r'ecosystem|ecolog|population','Écologie'),(r'evolut|species|phylogen','Évolution et biodiversité'),(r'\bplant|\bleaf|\bflower|\broot|\bstem\b','Végétaux'),(r'bacter|\bvirus|fung|prokary','Microorganismes'),(r'\bheart|cardiac|blood|circulat|arter|vein|capillar','Cœur et circulation'),(r'respirat|\blung|alveol|bronch','Respiration'),(r'digest|stomach|intestin|pancrea|\bliver','Digestion'),(r'brain|cerebr','Cerveau'),(r'neuron|nervous|synap|\bnerve','Système nerveux'),(r'muscle|myosin|actin','Muscles'),(r'\bbone|skelet|joint|cartilage','Squelette'),(r'\beye\b|retin|vision','Vision'),(r'\bear\b|hearing|cochlea','Audition'),(r'\bskin|epiderm|derm','Peau'),(r'\bkidney|renal|nephron|urinary','Reins et excrétion'),(r'immun|lymph|antibod','Immunité'),(r'hormon|endocrin','Hormones'),(r'tissue|epitheli','Tissus'),(r'membrane|diffusion|osmosis','Membranes et échanges'),(r'\bcell|organelle|mitochond|nucleus','Cellules'),(r'metabol|enzyme|nutrition|protein','Nutrition et métabolisme')]
for e in catalog:
 assert all(isinstance(e.get(k),str) for k in ['id','title','category','tags','filename','author','license','license_url','source_url','source_timestamp','changes','sha256']), e['id']
 if e['id'].startswith('os-'):
  text=e.get('caption','')+' '+e['source_url'].rsplit('/',1)[-1]
  rules=physics if e['category']=='Physique-chimie'else biology
  if e['category']=='SVT':rules=[(r'\batom|molecul|chemical|\bwater\b|\bcarbon\b','Atomes et molécules')]+rules
  theme=next((label for part in [e.get('module_title',''),text]for pattern,label in rules if re.search(pattern,part,re.I)), 'Physique · notions générales'if e['category']=='Physique-chimie'else'Biologie · notions générales')
  display=e['title'].split(' — ',1)[-1];e.update(topic=theme,title=theme+' — '+display,tags=theme+' '+display+' '+e.get('caption','')+' '+e.get('module_title',''))
 elif not e.get('topic'):e['topic']='Cartes thématiques'if e['category']=='Cartes'else'Schémas en français'
 # Every item has a compact thumbnail, including the original embedded starter set.
 file=OUT/e['filename'];data=file.read_bytes();assert hashlib.sha256(data).hexdigest()==e['sha256']
 image=Image.open(BytesIO(data));assert image.size==(e['width'],e['height']);assert len(data)<=16*1024*1024
 thumb=OUT/'thumbs'/e['filename']
 if not thumb.is_file():
  small=image.convert('RGBA');small.thumbnail((340,220));small.save(thumb,compress_level=6)
 e['thumbnail_sha256']=hashlib.sha256(thumb.read_bytes()).hexdigest()
 if not e.get('license_url')and e['license']=='Public domain':e['license_url']=e['source_url']
 assert all(e.get(k)for k in ['author','license','source_url','license_url','source_timestamp'])
 assert e['license']in ['CC BY 4.0','CC BY-SA 3.0','CC BY-SA 4.0','CC0','Public domain','CC BY 3.0','CC0 1.0','Public domain / CC0','CC BY-SA 2.0 FR'],e['license']
 assert not any(c in e['filename']for c in '/\\')
assert len({e['id']for e in catalog})==len(catalog)
assert len({e['sha256']for e in catalog})==len(catalog)
catalog_text=json.dumps(catalog,ensure_ascii=False,indent=2)
if (OUT/'catalog.json').read_text(encoding='utf-8')!=catalog_text:(OUT/'catalog.json').write_text(catalog_text,encoding='utf-8')
sources=OUT/'sources';sources.mkdir(exist_ok=True)
for p in (ROOT/'test-output/library-collections').glob('*.json'):
 if p.name!='natural-earth-countries.geojson':shutil.copyfile(p,sources/p.name)
shutil.copyfile(ROOT/'test-output/library-collections/natural-earth-countries.geojson',sources/'natural-earth-countries.geojson')
header='# Bibliothèque scolaire Écrinator — collections sélectionnées\n\nCartes historiques et géographiques, schémas scientifiques sans légende,\nfigures mathématiques et illustrations littéraires. Chaque fichier conserve\nson auteur, sa source et sa licence : domaine public, CC BY ou CC BY-SA.\nLes gravures sont des œuvres anciennes à étudier, pas des schémas scientifiques.\nSources consultables au clic droit, sans ajout automatique sur la page.\nFonctionnement hors ligne ; aucune validation enseignante revendiquée.\nLe pack de plusieurs milliers de ressources et la couverture de toutes les\nmatières restent en préparation. Les corpus non sélectionnés sont exclus.\n\n'
rows=[]
for e in catalog:
 rows.append(f"- **{e['filename']}** — {e['author']} · {e['license']}\n  Source : {e['source_url']}\n  Version : {e['source_timestamp']}\n  Licence : {e['license_url']}\n  Preuve : {e.get('license_proof_url',e['source_url'])}\n  Adaptations : {e['changes']}\n")
(OUT/'ATTRIBUTION.md').write_text(header+'\n'.join(rows),encoding='utf-8')
(OUT/'LIRE-MOI.txt').write_text(f'Bibliothèque Écrinator — {len(catalog)} images hors ligne.\n\n'+header.replace('# ','')+'\nLes images et miniatures sont intégrées à l’exécutable. Cette archive de ressources est facultative. Le logiciel vérifie chaque image par SHA-256. Aucun téléchargement au lancement.\n',encoding='utf-8')
pack=OUT/'library.pending.eclib'
names=['catalog.json','ATTRIBUTION.md','LIRE-MOI.txt']+[e['filename']for e in catalog]+['thumbs/'+e['filename']for e in catalog]
names += [p.relative_to(OUT).as_posix() for p in (OUT/'licenses').glob('*') if p.is_file()]
# Source vectors belong only to current entries, never the rejected atlas.
for e in catalog:
 p=OUT/'sources/light'/(e['id']+'.svg')
 if p.is_file(): names.append(p.relative_to(OUT).as_posix())
with ZipFile(pack,'w',ZIP_DEFLATED,compresslevel=9)as z:
 for name in sorted(set(names)):
  info=ZipInfo(name,(2026,10,24,0,0,0));info.compress_type=ZIP_DEFLATED
  z.writestr(info,(OUT/name).read_bytes())
 info=ZipInfo('pack.json',(2026,10,24,0,0,0));info.compress_type=ZIP_DEFLATED
 z.writestr(info,json.dumps(dict(version=1,images=len(catalog),catalog_sha256=hashlib.sha256((OUT/'catalog.json').read_bytes()).hexdigest())))
with ZipFile(pack)as z:assert z.testzip()is None
def file_hash(path):
 digest=hashlib.sha256()
 with path.open('rb')as file:
  for block in iter(lambda:file.read(1024*1024),b''):digest.update(block)
 return digest.hexdigest()
assert pack.stat().st_size < 160*1024*1024, 'Source archive exceeds the 160 MiB budget for the reviewed collections'
target=OUT/'library.eclib'
# Windows readers can hold the pack open. A reproducible, identical build does
# not need to replace it (and must not interrupt an application using it).
if target.is_file()and file_hash(target)==file_hash(pack):pack.unlink()
else:pack.replace(target)
# Visual QA sheets: real samples from every source family.
font=ImageFont.truetype(str(ROOT/'assets/fonts/NotoSerif-Variable.ttf'),13)
for prefix in ['os-biology-','os-anatomy-physiology-','os-university-physics-','ne-country-']:
 group=[e for e in catalog if e['id'].startswith(prefix)];sample=group[::max(1,len(group)//20)][:20]
 sheet=Image.new('RGB',(1000,900),'#f1f5fa');d=ImageDraw.Draw(sheet)
 for i,e in enumerate(sample):
  x=(i%4)*250;y=(i//4)*180;im=Image.open(OUT/e['filename']).convert('RGBA');im.thumbnail((230,140));bg=Image.new('RGBA',(230,140),'white');bg.alpha_composite(im,((230-im.width)//2,(140-im.height)//2));sheet.paste(bg.convert('RGB'),(x+10,y+5));d.text((x+10,y+148),e['topic'][:28],font=font,fill='#17314d')
 sheet.save(ROOT/'test-output'/('library-qa-'+prefix.strip('-')+'.jpg'))
summary=dict(images=len(catalog),categories=dict(Counter(e['category']for e in catalog)),topics=len({e['topic']for e in catalog}),bytes=target.stat().st_size,sha256=file_hash(target))
(ROOT/'test-output/library-pack.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=False))
