"""Remove extraction artefacts, then expose every remaining figure for review.
This script deliberately does not publish into the shipping catalogue.
"""
from pathlib import Path
from defusedxml import ElementTree as E
from PIL import Image, ImageDraw, ImageFont
import json,re,hashlib,collections

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/library/reference/sesamath'
rows=json.loads((OUT/'school-collection.json').read_text(encoding='utf-8'))
accepted=[];excluded=[];seen=set()
for e in rows:
 vector=E.fromstring((OUT/(e['id']+'.svg')).read_bytes())
 text=' '.join(''.join(vector.itertext()).split())
 reason=None
 if re.search(r'RETENIR|exercice\s+corrig|auto.?éval|savoir.?faire|\bcours\b',text,re.I):
  reason='Editorial banner or heading, not a mathematical figure'
 image=Image.open(OUT/e['filename']).convert('RGB')
 small=image.copy();small.thumbnail((160,160));pixels=list(small.getdata())
 black=sum(max(p)<120 for p in pixels)
 if not reason and e['height']>6*e['width'] and len(text.strip())<=2:
  reason='Narrow page-corner ornament or isolated pagination fragment'
 if not reason and len(text.strip())<3 and black<max(12,len(pixels)*.0008):
  reason='Unlabelled colour ornament without readable mathematical construction'
 if not reason and re.fullmatch(r'[×xX. …\s]+',text):
  reason='Standalone empty arithmetic callout, no usable exercise context'
 if not reason and not re.search(r'[\dA-Za-zÀ-ÿ]',text) and e['width']>6*e['height'] and black<50:
  reason='Empty decorative horizontal field'
 # Deduplicate exactly equal rendered pixels independently of PNG metadata.
 pixel_hash=hashlib.sha256(image.tobytes()+str(image.size).encode()).hexdigest()
 if not reason and pixel_hash in seen:reason='Identical rendered pixels already present'
 if reason:excluded.append(dict(id=e['id'],reason=reason));continue
 seen.add(pixel_hash)
 e=dict(e);e['figure_labels']=text
 accepted.append(e)
accepted.sort(key=lambda e:(e['topic'],','.join(e['grades']),e['cycle'],e['id']))
(OUT/'editorial-review-index.json').write_text(json.dumps(accepted,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'artefact-exclusions.json').write_text(json.dumps(excluded,ensure_ascii=False,indent=2),encoding='utf-8')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
for start in range(0,len(accepted),36):
 sheet=Image.new('RGB',(1440,1440),'#edf2f8');draw=ImageDraw.Draw(sheet)
 for j,e in enumerate(accepted[start:start+36]):
  x=j%6*240;y=j//6*240
  image=Image.open(OUT/e['filename']);image.thumbnail((226,185))
  sheet.paste(image,(x+(240-image.width)//2,y+3))
  draw.text((x+6,y+192),f'{start+j}  '+e['topic'][:27],font=font,fill='#172b4d')
  draw.text((x+6,y+209),('/'.join(e['grades'])or e['cycle'])+' '+e['id'].split('-')[-1],font=font,fill='#52627b')
  draw.text((x+6,y+225),e['figure_labels'][:32],font=font,fill='#52627b')
 sheet.save(OUT/f'editorial-review-{start//36+1}.jpg',quality=92)
print(json.dumps(dict(candidates=len(accepted),excluded=len(excluded),reasons=dict(collections.Counter(e['reason']for e in excluded)),sheets=(len(accepted)+35)//36,shipping_approved=False),ensure_ascii=False,indent=2))
