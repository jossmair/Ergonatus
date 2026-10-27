"""Build a labelled inspection sheet; source artwork is never modified."""
from pathlib import Path
import sys,json,hashlib
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from shared.ui.theme import APP_THEMES
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18)
sheet=Image.new('RGB',(1200,7*230),'#101820');draw=ImageDraw.Draw(sheet);records=[]
for index,(key,theme) in enumerate(APP_THEMES.items()):
    path=ROOT/'assets/backgrounds'/f'{key}.png'
    with Image.open(path) as image:
        image.load();width,height=image.size
        assert width>=1024 and height>=600,(key,image.size)
        preview=image.convert('RGB');preview.thumbnail((384,192))
        x=8+(index%3)*400;y=(index//3)*230
        sheet.paste(preview,(x,y));draw.text((x,y+194),theme['name']+'  '+theme['accent'],font=font,fill='white')
        records.append(dict(app=key,width=width,height=height,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
sheet.save(ROOT/'docs/validation/backgrounds-gallery.jpg',quality=90)
(ROOT/'docs/validation/backgrounds.json').write_text(json.dumps(records,indent=2))
print('21 fonds vérifiés ; planche de contrôle enregistrée.')
