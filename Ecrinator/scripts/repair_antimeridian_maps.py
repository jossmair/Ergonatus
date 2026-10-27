"""Render compact regional extents for countries crossing the date line."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,math,hashlib
root=Path(__file__).resolve().parents[1];out=root/'assets/library'
catalog=json.loads((out/'catalog.json').read_text(encoding='utf-8'));lookup={e['id']:e for e in catalog}
data=json.loads((root/'test-output/library-collections/natural-earth-countries.geojson').read_text(encoding='utf-8'))
font=ImageFont.truetype(str(root/'assets/fonts/NotoSerif-Variable.ttf'),28);small=ImageFont.truetype(str(root/'assets/fonts/NotoSerif-Variable.ttf'),15)
def polys(f):return f['geometry']['coordinates']if f['geometry']['type']=='MultiPolygon'else[f['geometry']['coordinates']]
for feature in data['features']:
 pts=[p for poly in polys(feature)for ring in poly for p in ring]
 if max(p[0]for p in pts)-min(p[0]for p in pts)<180:continue
 center=math.degrees(math.atan2(sum(math.sin(math.radians(p[0]))for p in pts),sum(math.cos(math.radians(p[0]))for p in pts)))
 def lon(x):return(x-center+180)%360-180
 xs=[lon(p[0])for p in pts];ys=[p[1]for p in pts]
 if max(xs)-min(xs)>180:continue
 dx=max(2.,(max(xs)-min(xs))*.45);dy=max(2.,(max(ys)-min(ys))*.45);xmin,xmax=min(xs)-dx,max(xs)+dx;ymin,ymax=max(-85,min(ys)-dy),min(85,max(ys)+dy)
 cosine=max(.2,math.cos(math.radians((ymin+ymax)/2)));scale=min(1100/((xmax-xmin)*cosine),625/(ymax-ymin));ox=(1200-(xmax-xmin)*cosine*scale)/2;oy=80+(650-(ymax-ymin)*scale)/2
 def xy(p):return(ox+(p[0]-xmin)*cosine*scale,oy+(ymax-p[1])*scale)
 def ring_points(ring):
  points=[]
  for x,y,*rest in ring:
   x=lon(x)
   if points:
    while x-points[-1][0]>180:x-=360
    while x-points[-1][0]<-180:x+=360
   points.append((x,y))
  shift=round(sum(p[0]for p in points)/len(points)/360)*360
  return[(x-shift,y)for x,y in points]
 image=Image.new('RGB',(1200,800),'#edf6fb');draw=ImageDraw.Draw(image)
 def paint(f,fill):
  for poly in polys(f):
   if not poly:continue
   draw.polygon([xy(p)for p in ring_points(poly[0])],fill=fill,outline='#a5b5c4',width=1)
   for ring in poly[1:]:draw.polygon([xy(p)for p in ring_points(ring)],fill='#edf6fb')
 for f in data['features']:paint(f,'#f8fafb')
 paint(feature,'#2496aa');country=feature['properties']['NAME_FR'];ident='ne-country-'+str(feature['properties']['NE_ID']);e=lookup[ident]
 draw.rectangle((0,0,1200,69),fill='white');draw.text((35,14),country,font=font,fill='#17314d');draw.text((1125,85),'N ↑',font=small,fill='#17314d');draw.rectangle((0,737,1200,800),fill='white');draw.rectangle((35,757,57,779),fill='#2496aa');draw.text((70,754),'Pays / territoire ciblé',font=small,fill='#17314d');draw.text((630,754),'Natural Earth · carte de situation · 1:110m',font=small,fill='#526980')
 path=out/e['filename'];image.convert('RGBA').save(path,compress_level=6);image.thumbnail((340,220));thumb=out/'thumbs'/e['filename'];image.convert('RGBA').save(thumb,compress_level=6)
 e['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();e['thumbnail_sha256']=hashlib.sha256(thumb.read_bytes()).hexdigest();e['changes']+=' Longitude recentrée sur le pays pour éviter une carte mondiale au passage de l’antiméridien.'
 print(country,ident)
(out/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
