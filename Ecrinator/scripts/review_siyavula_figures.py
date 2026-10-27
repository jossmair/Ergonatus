from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/library/reference/siyavula'
labels={e['id']:e for e in [json.loads(s)for s in (ROOT/'test-output/reference-sources/siyavula-labels.ndjson').read_text(encoding='utf-8').splitlines()]}
rows=json.loads((OUT/'original-candidates.json').read_text(encoding='utf-8'))
selected=[e for e in rows if e['id']in labels and not labels[e['id']].get('text','').strip() and'error'not in labels[e['id']]]
selected.sort(key=lambda e:(e['chapter_en'],e['source_grade'],e['source_image']))
(OUT/'unlabelled-review-index.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf-8')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
for start in range(0,len(selected),24):
 sheet=Image.new('RGB',(1280,1380),'#edf2f8');draw=ImageDraw.Draw(sheet)
 for j,e in enumerate(selected[start:start+24]):
  x=j%4*320;y=j//4*230;im=Image.open(OUT/e['filename']).convert('RGBA');im.thumbnail((300,158));bg=Image.new('RGBA',im.size,'white');bg.alpha_composite(im);sheet.paste(bg.convert('RGB'),(x+(320-im.width)//2,y+3));draw.text((x+8,y+165),e['chapter_en'][:46],font=font,fill='#172b4d');draw.text((x+8,y+182),e['caption_en'][:48],font=font,fill='#172b4d');draw.text((x+8,y+198),e['caption_en'][48:96],font=font,fill='#172b4d');draw.text((x+8,y+215),e['id'],font=font,fill='#52627b')
 sheet.save(OUT/('review-'+str(start//24+1)+'.jpg'),quality=90)
print('Ready for visual review:',len(selected),'figures in',len(range(0,len(selected),24)),'sheets')
