"""A vector north marker avoids missing arrow glyphs in the map label font."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,hashlib
root=Path(__file__).resolve().parents[1];out=root/'assets/library';path=out/'catalog.json'
catalog=json.loads(path.read_text(encoding='utf-8'));font=ImageFont.truetype(str(root/'assets/fonts/NotoSerif-Variable.ttf'),17)
for e in catalog:
 if not e['id'].startswith('ne-country-'):continue
 image=Image.open(out/e['filename']).convert('RGBA');d=ImageDraw.Draw(image)
 d.rounded_rectangle((1107,78,1185,143),radius=10,fill='#ffffff',outline='#dfebf1',width=1)
 d.text((1146,80),'N',font=font,anchor='mt',fill='#17314d');d.line((1146,128,1146,109),fill='#17314d',width=3);d.polygon([(1146,101),(1139,112),(1153,112)],fill='#17314d')
 p=out/e['filename'];image.save(p,compress_level=6);image.thumbnail((340,220));thumb=out/'thumbs'/e['filename'];image.save(thumb,compress_level=6)
 e['sha256']=hashlib.sha256(p.read_bytes()).hexdigest();e['thumbnail_sha256']=hashlib.sha256(thumb.read_bytes()).hexdigest()
 marker=' Flèche du nord dessinée sans dépendance de glyphe.'
 if marker not in e['changes']:e['changes']+=marker
path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8');print('177 cartes : flèche du nord corrigée')
