"""One meaningful Doré illustration per fable; no ornamental tails or duplicate crops."""
from pathlib import Path
from zipfile import ZipFile
from bs4 import BeautifulSoup
from PIL import Image,ImageDraw,ImageFont
from io import BytesIO
import json,hashlib,posixpath,re
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'test-output/reference-sources';OUT=ROOT/'assets/library/reference/literature';OUT.mkdir(exist_ok=True)
z=ZipFile(BASE/'dore-fables-50316.epub');translations=json.loads((OUT.parent/'dore-french-titles.json').read_text(encoding='utf-8'))
def clean(s):return ' '.join(s.split()).strip(' .')
def next_title(im):
 p=im.find_next('p',class_='fable')
 while p is not None and (clean(p.get_text(' ',strip=True)).startswith('FABLE ') or clean(p.get_text(' ',strip=True))not in translations):p=p.find_next('p',class_='fable')
 return clean(p.get_text(' ',strip=True))if p else None
choices={}
for file in z.namelist():
 if not file.endswith(('.html','.xhtml')):continue
 soup=BeautifulSoup(z.read(file),'html.parser')
 for im in soup.find_all('img',src=True):
  src=im['src'];plate='_plate_'in src;head='_head_'in src
  if not plate and not head:continue
  parent=im.find_parent('div');cap=parent.find('p',class_='cap')if parent else None;title=clean(cap.get_text(' ',strip=True))if cap else None
  if title not in translations:title=next_title(im)if head else None
  if title not in translations:continue
  path=posixpath.normpath(posixpath.join(posixpath.dirname(file),src))
  if path not in z.namelist():continue
  raw=z.read(path);image=Image.open(BytesIO(raw));score=(1 if plate else 0,image.width*image.height)
  if title not in choices or score>choices[title]['score']:choices[title]=dict(path=path,html=file,score=score,raw=raw)
entries=[]
for title,choice in choices.items():
 raw=choice['raw'];im=Image.open(BytesIO(raw));im.thumbnail((1100,1100));im=im.convert('RGB');ident='dore-fable-'+hashlib.sha256(choice['path'].encode()).hexdigest()[:16];file=OUT/(ident+'.jpg');im.save(file,quality=88,optimize=True)
 thumb=im.copy();thumb.thumbnail((270,180));thumb.save(OUT/(ident+'-thumb.jpg'),quality=84,optimize=True)
 small=im.copy();small.thumbnail((100,100));mono=all(max(p)-min(p)<12 for p in small.getdata())
 entries.append(dict(id=ident,title=translations[title],category='Français',subjects=['Français','Arts plastiques'],topic='Fables · La Fontaine et Doré',curriculum_theme='Ruses, récits et portée critique de la fable',learning_objective='Mettre en relation une fable et son illustration ; identifier les personnages, la situation et la portée critique.',grades=['6e','5e'],educational_use='À étudier',kind='Œuvre',language='zxx',monochrome=mono,unlabelled=True,filename=file.name,width=im.width,height=im.height,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),thumbnail_sha256=hashlib.sha256((OUT/(ident+'-thumb.jpg')).read_bytes()).hexdigest(),author='Gustave Doré et graveurs de l’édition ancienne',license='Public domain',license_url='https://www.gutenberg.org/ebooks/50316',source_url='https://www.gutenberg.org/ebooks/50316',license_proof_url='https://www.gutenberg.org/ebooks/50316',source_timestamp='Édition ancienne · Gustave Doré (1832–1883)',source_image=choice['path'],source_html=choice['html'],source_sha256=hashlib.sha256(raw).hexdigest(),source_caption_en=title,caption='Illustration ancienne de la fable « '+translations[title]+' ». Le titre français est fourni pour le classement.',tags=translations[title]+' '+title+' gravure fable La Fontaine Gustave Doré',changes='Réduction de résolution et compression JPEG pour affichage scolaire ; composition conservée. Une illustration sélectionnée par fable.',review_status='Source bibliographique et domaine public vérifiés ; contrôle visuel requis'))
(OUT/'candidates.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
for start in range(0,len(entries),24):
 sheet=Image.new('RGB',(1200,1320),'#edf2f8');draw=ImageDraw.Draw(sheet)
 for j,e in enumerate(entries[start:start+24]):
  x=j%4*300;y=j//4*220;im=Image.open(OUT/(e['id']+'-thumb.jpg'));sheet.paste(im,(x+(300-im.width)//2,y+3));draw.text((x+8,y+187),e['title'][:42],font=font,fill='#172b4d');draw.text((x+8,y+204),e['id'],font=font,fill='#52627b')
 sheet.save(OUT/('review-'+str(start//24+1)+'.jpg'),quality=90)
print('Fables:',len(entries),'unique illustrations;',round(sum((OUT/e['filename']).stat().st_size for e in entries)/1024/1024,1),'MiB')
