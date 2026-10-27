from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
OUT=Path('assets/library/reference/maps');rows=json.loads((OUT/'candidates.json').read_text(encoding='utf-8'));font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
for start in range(0,len(rows),12):
 sheet=Image.new('RGB',(1440,1380),'#edf2f8');d=ImageDraw.Draw(sheet)
 for j,e in enumerate(rows[start:start+12]):
  x=j%3*480;y=j//3*345;im=Image.open(OUT/e['filename']);im.thumbnail((460,285));sheet.paste(im,(x+(480-im.width)//2,y+3));d.text((x+8,y+294),e['title'][:56],font=font,fill='#172b4d');d.text((x+8,y+313),e['id']+' · '+e['language'],font=font,fill='#52627b')
 sheet.save(OUT/('review-'+str(start//12+1)+'.jpg'),quality=92)
print(len(rows),'maps in review sheets')
