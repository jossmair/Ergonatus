"""Prepare a school-source math collection with conservative grade metadata.
No administrative atlas, no quota synthesis, no invented mathematical figures.
"""
from pathlib import Path
from zipfile import ZipFile
from defusedxml import ElementTree as E
from PIL import Image,ImageDraw,ImageFont
import json,re,hashlib,collections
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'test-output/reference-sources';OUT=ROOT/'assets/library/reference/sesamath'
items=json.loads((OUT/'candidates.json').read_text(encoding='utf-8'));sources={e['filename']:e for e in json.loads((BASE/'sesamath/manifest.json').read_text(encoding='utf-8'))}
NS={'draw':'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0','text':'urn:oasis:names:tc:opendocument:xmlns:text:1.0'}
cache={};accepted=[];excluded=[];hashes=set()
def local(tag):return tag.rsplit('}',1)[-1]
def plain(e):
 if e.tag.startswith('{'+NS['draw']+'}'):return ''
 return (e.text or '')+''.join(plain(c)+(c.tail or '')for c in e)
def objective(topic):
 rules=[('fraction','Représenter, comparer et utiliser des fractions.'),('repér','Lire des coordonnées, placer des points et compléter un repère.'),('fonction','Lire et interpréter une représentation graphique de fonction.'),('proportion','Reconnaître et utiliser une situation de proportionnalité.'),('probab','Décrire une expérience aléatoire et déterminer des probabilités.'),('statist','Lire des données et choisir une représentation adaptée.'),('triangle','Identifier les propriétés des triangles et compléter une construction.'),('angle','Repérer, comparer ou mesurer des angles.'),('transformation','Reconnaître et construire des figures par transformation géométrique.'),('espace','Lire une représentation de solide et compléter une construction.'),('volume','Relier un solide à ses dimensions et à son volume.'),('aire','Décomposer des surfaces et raisonner sur leurs aires.'),('longueur','Mesurer et comparer des longueurs à partir d’une figure.'),('équation','Modéliser une situation et raisonner avec une équation.'),('informat','Décrire un algorithme et suivre les étapes d’un programme.'),('littéral','Utiliser les lettres pour décrire une situation mathématique.'),('nombre','Représenter des nombres et raisonner sur leurs écritures.')]
 return next((v for k,v in rules if k in topic.lower()),'Observer la figure, identifier ses propriétés et compléter le support à partir du cours.')
warning=OUT/'sesamath-cahier_2025_6e_G1_cours-53.png'
def dhash(im):
 im=im.convert('L').resize((9,8));p=list(im.getdata());return sum((p[y*9+x]>p[y*9+x+1])<<(y*8+x) for y in range(8)for x in range(8))
warning_hash=dhash(Image.open(warning))if warning.exists()else None
for e in items:
 file=re.sub(r'^sesamath-','',e['id']).rsplit('-',1)[0]+'.odt';src=sources.get(file)
 if src is None or not src.get('chapter'):
  excluded.append(dict(id=e['id'],reason='Chapter not identified; annex requires individual description'));continue
 if file not in cache:
  tree=E.fromstring(ZipFile(BASE/'sesamath'/file).read('content.xml'));parent={c:p for p in tree.iter()for c in p};ordered=list(tree.iter());indexes={el:i for i,el in enumerate(ordered)};paragraphs=[];shapes={}
  for element in ordered:
   name=element.get('{'+NS['draw']+'}name')
   if element.tag=='{'+NS['draw']+'}g'and name:shapes[name]=element
   if element.tag not in ['{'+NS['text']+'}p','{'+NS['text']+'}h']:continue
   p=parent.get(element);inside=False
   while p is not None:
    if p.tag.startswith('{'+NS['draw']+'}'):inside=True;break
    p=parent.get(p)
   if inside:continue
   text=' '.join(plain(element).split());text=''.join(c for c in text if not 0xe000<=ord(c)<=0xf8ff)
   if len(text)>35 and len(text.split())>5:paragraphs.append((indexes[element],text))
  cache[file]=(shapes,indexes,paragraphs)
 shapes,indexes,paragraphs=cache[file];shape=shapes.get(e['source_figure']);context=''
 if shape is not None:
  before=[t for idx,t in paragraphs if idx<=indexes[shape]];context=before[-1][:700]if before else ''
 image=Image.open(OUT/e['filename']).convert('RGB');small=image.copy();small.thumbnail((80,80));pixels=list(small.getdata());red=sum(r>150 and r>g*1.4 and r>b*1.4 for r,g,b in pixels)/len(pixels)
 if warning_hash is not None and red>.04 and (dhash(image)^warning_hash).bit_count()<=7:
  excluded.append(dict(id=e['id'],reason='Warning pictogram, not an exercise figure'));continue
 sha=hashlib.sha256((OUT/e['filename']).read_bytes()).hexdigest()
 if sha in hashes:excluded.append(dict(id=e['id'],reason='Identical image already present'));continue
 hashes.add(sha);topic=re.sub(r'\s*\[supplément non édité\]','',e['topic']).strip()
 aliases={'Repérages':'Repérage','Triangles rectangles':'Triangle rectangle','Triangles et proportionnalité':'Triangle et proportionnalité','Transformation et parallélogramme':'Transformations et parallélogramme'};topic=aliases.get(topic,topic)
 edition=src['source'];exact=edition in ['sesamath-6e-2025.html','sesamath-5e-2026.html'];grades=src['grades']if exact else[];cycle=''if exact else'Cycle 4'
 label=src['label'].strip(' :');label=re.sub(r'^Série\s*\d+\s*[-–:]\s*','',label)
 title=topic+' · '+label+' · '+e['source_figure'].replace('Objet de groupe','figure').replace('Forme','figure ')
 e.update(title=title,topic=topic,curriculum_theme=topic,learning_objective=objective(topic),grades=grades,cycle=cycle,domain='mathematics',educational_use='À étudier'if'cours'in file else'À compléter',kind='Figure mathématique',caption='Source : '+src['chapter']+' · '+src['label'],source_context=context,source_document=file,source_page=src['source_page'],source_timestamp='Sésamath · '+edition,changes='Extraction du groupe vectoriel original et rendu PNG. Viewport corrigé lorsque nécessaire ; tracés et annotations conservés.',tags=' '.join([topic,label,context,' '.join(grades),cycle]),review_status='Manuel scolaire français vérifié ; contrôle technique des images ; planches de contrôle par chapitre')
 accepted.append(e)
(OUT/'school-collection.json').write_text(json.dumps(accepted,ensure_ascii=False,indent=2),encoding='utf-8');(OUT/'editorial-exclusions.json').write_text(json.dumps(excluded,ensure_ascii=False,indent=2),encoding='utf-8')
# Stratified visual review: representatives from every chapter and source edition.
groups=collections.defaultdict(list)
for e in accepted:groups[(e['topic'],tuple(e['grades']),e['cycle'])].append(e)
samples=[]
for key,group in sorted(groups.items()):
 samples.extend(group[i]for i in sorted({0,len(group)//3,2*len(group)//3,len(group)-1}))
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
for start in range(0,len(samples),24):
 sheet=Image.new('RGB',(1280,1200),'#edf2f8');draw=ImageDraw.Draw(sheet)
 for j,e in enumerate(samples[start:start+24]):
  x=j%4*320;y=j//4*200;im=Image.open(OUT/(e['id']+'-thumb.png'));im.thumbnail((300,150));sheet.paste(im,(x+(320-im.width)//2,y+3));draw.text((x+8,y+157),e['topic'][:46],font=font,fill='#172b4d');draw.text((x+8,y+174),('/'.join(e['grades'])or e['cycle'])+' '+e['id'].removeprefix('sesamath-')[-35:],font=font,fill='#52627b')
 sheet.save(OUT/('chapter-review-'+str(start//24+1)+'.jpg'),quality=90)
(OUT/'school-collection-report.json').write_text(json.dumps(dict(accepted=len(accepted),excluded=len(excluded),chapters=len(groups),visual_samples=len(samples),approval_pending=True),indent=2),encoding='utf-8');print(len(accepted),'school figures;',len(excluded),'excluded;',len(groups),'chapter/level groups to review')
