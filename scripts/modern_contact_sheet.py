from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
root=Path(__file__).resolve().parents[1];out=root/'docs/validation/modern-2026-10-24'
names=['hub','claviernator','precisionator','transcrinator-final-ready','redactor','lector','scanator','corrector','traductor-rempli','calculinator','communicator','planinator-rempli','organisator','memorinator-rempli','applinator-widget-clair','temporator-visuel-clair']
sheet=Image.new('RGB',(1600,1160),'#E9EFF6');d=ImageDraw.Draw(sheet)
for i,name in enumerate(names):
    im=Image.open(out/(name+'.png')).convert('RGBA');im.thumbnail((380,250))
    x=(i%4)*400+10;y=(i//4)*290+30
    sheet.paste(im,(x,y),im);d.text((x,y-20),name,fill='#1E3149')
sheet.save(out/'contact-final.png')
from json import loads
themes=loads((root/'docs/SATELLITES_ASSEMBLY.json').read_text())
keys=['ergonatus','claviernator','precisionator','transcrinator','redactor','scanator','ecrinator','organisator','lector','applinator','temporator','concentrator','pdfinator','calculinator','communicator','memorinator','planinator','traductor','corrector']
sheet=Image.new('RGB',(1000,480),'#F6F9FD');d=ImageDraw.Draw(sheet)
for i,key in enumerate(keys):
    im=Image.open(root/'assets/orbs/clear'/(key+'.png'));im.thumbnail((70,70));x=i%5*200+65;y=i//5*120
    sheet.paste(im,(x,y),im);d.text((x-25,y+78),key,fill='#1E3149')
sheet.save(out/'orbs-claires.png')
