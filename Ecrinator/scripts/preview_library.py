from PIL import Image,ImageDraw
from pathlib import Path
import json
r=Path(__file__).resolve().parents[1]
entries=json.loads((r/'assets/library/catalog.json').read_text(encoding='utf-8'))
out=Image.new('RGB',(1200,((len(entries)+3)//4)*220),'#ecf1f8');d=ImageDraw.Draw(out)
for i,e in enumerate(entries):
    x=(i%4)*300;y=(i//4)*220
    im=Image.open(r/'assets/library'/e['filename']).convert('RGBA');im.thumbnail((280,175))
    out.paste(im,(x+(300-im.width)//2,y+5),im)
    d.text((x+8,y+184),e['title'],fill='#14264b')
    d.text((x+8,y+200),e['license'],fill='#536580')
out.save(r/'test-output/library-contact.png')
