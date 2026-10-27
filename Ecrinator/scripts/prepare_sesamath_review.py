"""Prepare review sheets, not a silently approved shipping catalogue.
Native SVGs retain original mathematical labels and measurements.
"""
from pathlib import Path
from zipfile import ZipFile
from defusedxml import ElementTree as E
from PIL import Image,ImageDraw,ImageFont
from io import BytesIO
import json,re,hashlib
from xml.etree import ElementTree as XML
import cairosvg
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'test-output/reference-sources';OUT=ROOT/'assets/library/reference/sesamath';OUT.mkdir(parents=True,exist_ok=True)
SOURCES={e['filename']:e for e in json.loads((BASE/'sesamath/manifest.json').read_text(encoding='utf-8'))}
NS={'draw':'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0','text':'urn:oasis:names:tc:opendocument:xmlns:text:1.0'}
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
items=[];hashes=set();errors=[]
manifests=sorted((BASE/'sesamath-vectors').glob('*/manifest.json'))
for manifest in manifests:
 data=json.loads(manifest.read_text(encoding='utf-8'));src=SOURCES[data['source']['filename']]
 tree=E.fromstring(ZipFile(BASE/'sesamath'/src['filename']).read('content.xml'));parents={c:p for p in tree.iter() for c in p}
 shapes={e.get('{'+NS['draw']+'}name'):e for e in tree.findall('.//draw:g',NS)}
 for fig in data['figures']:
  svg=manifest.parent/fig['file'];raw=svg.read_bytes()
  # Writer sometimes exports the original anchor offset as enormous empty SVG bounds.
  # Correct the vector viewport from the actual UNO group size, never redraw geometry.
  vector=XML.fromstring(raw);box=[float(v) for v in vector.get('viewBox','').split()]
  fixed=False
  if len(box)==4:
   for axis,size in [(0,fig['width']),(1,fig['height'])]:
    if box[axis+2]>size*1.5:
     box[axis]=max(0,box[axis+2]-size-100);box[axis+2]=size+200;fixed=True
   if fixed:
    vector.set('viewBox',' '.join(str(v)for v in box));vector.set('width',str(box[2]));vector.set('height',str(box[3]));raw=XML.tostring(vector,encoding='utf-8')
  normalized=OUT/('sesamath-'+src['filename'].removesuffix('.odt')+'-'+str(fig['shape_index'])+'.svg');normalized.write_bytes(raw)
  sha=hashlib.sha256(raw).hexdigest()
  if sha in hashes:continue
  hashes.add(sha)
  ident='sesamath-'+src['filename'].removesuffix('.odt')+'-'+str(fig['shape_index']);png=OUT/(ident+'.png')
  element=shapes.get(fig['shape_name']);context=''
  if element is not None:
   p=parents.get(element)
   while p is not None:
    text=' '.join(''.join(p.itertext()).split())
    if len(text)>25:
     context=text[:700];break
    p=parents.get(p)
  try:
   if not png.exists() or fixed:
    ratio=fig['width']/fig['height'];w=min(1400,max(400,round(fig['width']/10)));h=max(120,round(w/ratio))
    if h>1400:w=round(w*1400/h);h=1400
    rendered=cairosvg.svg2png(bytestring=raw,output_width=w,output_height=h)
    im=Image.open(BytesIO(rendered)).convert('RGBA');bg=Image.new('RGBA',im.size,'white');bg.alpha_composite(im);bg.convert('RGB').save(png,optimize=True)
   im=Image.open(png)
   gray=im.convert('L');hist=gray.histogram()
   if sum(hist[:240]) < max(60,im.width*im.height*.0008):
    errors.append(dict(file=str(svg),error='Rejected empty or almost blank figure'));continue
   thumb=im.copy();thumb.thumbnail((280,155));thumb.save(OUT/(ident+'-thumb.png'),optimize=True)
   label=src.get('chapter','').split(' : ',1)[-1] or src['filename']
   items.append(dict(id=ident,title=label+' · '+src['label'].strip(' :')+' · figure '+str(fig['shape_index']),filename=png.name,vector_source=str(normalized.relative_to(ROOT)).replace('\\','/'),original_vector_source=str(svg.relative_to(ROOT)).replace('\\','/'),category='Mathématiques',subjects=['Mathématiques'],grades=src['grades'],topic=label,curriculum_theme=label,learning_objective=context or 'Étudier ou compléter la figure dans son exercice source.',caption=context,kind='Figure mathématique',language='fr',source_url=src['url'],source_page=src['source_page'],source_figure=fig['shape_name'],author='Association Sésamath',license=src['license'],license_url=src['license_url'],license_proof_url=src['license_proof_url'],review_status='À vérifier visuellement',width=im.width,height=im.height,sha256=hashlib.sha256(png.read_bytes()).hexdigest()))
  except Exception as error:errors.append(dict(file=str(svg),error=str(error)))
(OUT/'candidates.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
# Contact sheets grouped by source chapter: useful for visual editorial review.
for start in range(0,min(len(items),288),24):
 sheet=Image.new('RGB',(1200,1080),'#edf2f8');draw=ImageDraw.Draw(sheet)
 for j,item in enumerate(items[start:start+24]):
  x=(j%4)*300;y=(j//4)*180;im=Image.open(OUT/(item['id']+'-thumb.png'));sheet.paste(im,(x+(300-im.width)//2,y))
  draw.text((x+7,y+157),item['topic'][:39],font=font,fill='#172b4d');draw.text((x+7,y+170),item['id'].removeprefix('sesamath-')[:42],font=font,fill='#172b4d')
 sheet.save(OUT/('review-'+str(start//24+1)+'.jpg'),quality=87)
(OUT/'report.json').write_text(json.dumps(dict(candidates=len(items),source_documents=len(manifests),errors=errors,shipping_approved=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('Prepared',len(items),'candidates; rendering errors',len(errors),'not yet approved for shipping')
