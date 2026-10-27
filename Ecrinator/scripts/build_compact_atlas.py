"""Build a compact, attributed school atlas from real geographic geometry.
Individual subdivisions live in an explicitly detailed atlas, distinct from essentials.
"""
from pathlib import Path
from collections import defaultdict,Counter
from io import BytesIO
import json,hashlib,math,html,re,shutil,functools
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely import make_valid
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/library';SRC=ROOT/'test-output/atlas-sources'
catalog=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));catalog=[e for e in catalog if not e['id'].startswith('college-atlas-')];seen={e['sha256']for e in catalog};created=[]
urls=json.loads((SRC/'DOWNLOADS.json').read_text(encoding='utf-8'))
@functools.cache
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rings(g):
 if g.is_empty:return []
 if g.geom_type=='Polygon':return[list(g.exterior.coords)]+[list(r.coords)for r in g.interiors]
 if hasattr(g,'geoms'):return[r for poly in g.geoms for r in rings(poly)]
 return []
def feature_geometry(f):
 g=shape(f['geometry'])
 if not g.is_valid:g=make_valid(g)
 return g

def store(ident,title,topic,geometries,source,author,license,version,style='contour',desc='',priority=1):
 if not geometries:return
 ext=unary_union(geometries)if len(geometries)>1 else geometries[0]
 if ext.is_empty:return
 xmin,ymin,xmax,ymax=ext.bounds
 if ymax-ymin<.000001 or xmax-xmin<.000001:return
 # Local equirectangular outline with latitude compensation; not a navigation map.
 lat=max(-75,min(75,(ymax+ymin)/2));cos=max(.15,math.cos(math.radians(lat)))
 cross=xmax-xmin>180
 paths=[]
 for g in geometries:
  tolerance=max(xmax-xmin,ymax-ymin)/1100
  simple=g.simplify(tolerance,preserve_topology=True)
  for ring in rings(simple):
   if len(ring)<4:continue
   paths.append([((x+360 if cross and x<0 else x)*cos,-y)for x,y,*_ in ring])
 if not paths:return
 pts=[p for ring in paths for p in ring];xx=[p[0]for p in pts];yy=[p[1]for p in pts];x0,x1,y0,y1=min(xx),max(xx),min(yy),max(yy)
 width,height=850,620;scale=min(770/max(.000001,x1-x0),540/max(.000001,y1-y0));ox=(width-(x1-x0)*scale)/2;oy=(height-(y1-y0)*scale)/2
 lines=[[(round(ox+(x-x0)*scale,1),round(oy+(y-y0)*scale,1))for x,y in ring]for ring in paths]
 im=Image.new('1',(width,height),1);draw=ImageDraw.Draw(im)
 # Draw outlines only: internal administrative boundaries remain visible.
 for points in lines:draw.line(points,fill=0,width=2)
 if style=='quadrillage':
  for x in range(50,width,50):
   for y in range(25,height-25,8):draw.line((x,y,x,y+1),fill=0,width=1)
  for y in range(50,height,50):
   for x in range(25,width-25,8):draw.line((x,y,x+1,y),fill=0,width=1)
 if im.getextrema()!=(0,255)and im.getextrema()!=(0,1):return
 buf=BytesIO();im.save(buf,format='PNG',optimize=True);data=buf.getvalue();digest=hashlib.sha256(data).hexdigest()
 if digest in seen:return
 seen.add(digest);filename=ident+'.png';(OUT/filename).write_bytes(data)
 thumb=im.copy();thumb.thumbnail((280,205));buf=BytesIO();thumb.save(buf,format='PNG',optimize=True);td=buf.getvalue();(OUT/'thumbs'/filename).write_bytes(td)
 svg='<svg xmlns="http://www.w3.org/2000/svg" width="850" height="620" viewBox="0 0 850 620"><rect width="850" height="620" fill="white"/><g fill="none" stroke="black" stroke-width="2">'+''.join('<path d="M'+'L'.join(f'{x},{y}'for x,y in ring)+'Z"/>'for ring in lines)+'</g></svg>'
 (OUT/'sources/light'/(ident+'.svg')).write_text(svg,encoding='utf-8')
 e=dict(id=ident,title=title,category='Cartes',topic=topic,tags=f'{title} {topic} collège carte muette sans nom sans légende {desc}',filename=filename,author=author,license=license,license_url='https://www.naturalearthdata.com/about/terms-of-use/'if license=='Public domain'else'https://www.etalab.gouv.fr/licence-ouverte-open-licence/',source_url=source,source_timestamp=version,changes='Fond muet depuis des géométries téléchargées ; simplification adaptée à une petite image monochrome. Projection locale avec compensation de latitude. Contours indicatifs ; source SVG incluse.',width=width,height=height,sha256=digest,thumbnail_sha256=hashlib.sha256(td).hexdigest(),source_sha256=hashlib.sha256(svg.encode()).hexdigest(),license_proof_url='https://www.naturalearthdata.com/about/terms-of-use/'if license=='Public domain'else'https://github.com/datagouv/decoupage-administratif#licence',embedded=True,level='college',kind='Fond de carte',monochrome=True,unlabelled=True,subjects=['Cartes','Histoire-géographie'],priority=priority)
 catalog.append(e);created.append(e)
admin=json.loads((SRC/'admin1.geojson').read_text(encoding='utf-8'))['features'];countries=json.loads((SRC/'countries.geojson').read_text(encoding='utf-8'))['features'];country_names={f['properties'].get('ADM0_A3'):f['properties'].get('NAME_FR')or f['properties'].get('NAME')for f in countries}
# 4,500+ real regional outlines, a detailed world atlas rather than fictitious copies.
for i,f in enumerate(admin):
 p=f['properties'];code=p.get('adm0_a3');country=country_names.get(code)or p.get('admin')or'Pays';name=p.get('name_fr')or p.get('name')or p.get('iso_3166_2')or str(i)
 try:store('college-atlas-region-'+str(i),f'{country} · {name} — contour régional',f'Atlas détaillé · {country}',[feature_geometry(f)],urls['admin1.geojson'],'Natural Earth — Tom Patterson, Nathaniel Vaughn Kelso et contributeurs','Public domain','Source géographique SHA-256 '+sha(SRC/'admin1.geojson'),desc=f'{p.get("name","")} {p.get("admin","")} {p.get("iso_3166_2","")}',priority=3)
 except Exception as e:print('SKIP REGION',i,str(e),flush=True)
 if i%500==0:print('REGIONS',i,'created',len(created),flush=True)
# Country outline and administrative divisions: two distinct classroom tasks.
by_country=defaultdict(list)
for f in admin:by_country[f['properties'].get('adm0_a3')].append(feature_geometry(f))
for i,f in enumerate(countries):
 p=f['properties'];name=p.get('NAME_FR')or p.get('NAME')or str(i);code=p.get('ADM0_A3');g=feature_geometry(f)
 store('college-atlas-pays-'+str(i),f'{name} — fond de carte muet','Monde · pays et territoires',[g],urls['countries.geojson'],'Natural Earth et contributeurs','Public domain','Source géographique SHA-256 '+sha(SRC/'countries.geojson'),priority=1)
 if len(by_country[code])>1:store('college-atlas-pays-regions-'+str(i),f'{name} — subdivisions sans noms','Monde · découpages administratifs',by_country[code],urls['admin1.geojson'],'Natural Earth et contributeurs','Public domain','Source géographique SHA-256 '+sha(SRC/'admin1.geojson'),priority=2)
print('COUNTRIES DONE',len(created),flush=True)
# France from official Etalab commune geometry and arrondissement membership.
metadata=json.loads((SRC/'communes-metadata.json').read_text(encoding='utf-8'));lookup={e['code']:e for e in metadata if e.get('type')=='commune-actuelle'}
communes=json.loads((SRC/'communes.geojson').read_text(encoding='utf-8'))['features'];by_dep=defaultdict(list);by_arr=defaultdict(list);arr_info={}
for f in communes:
 p=f['properties'];m=lookup.get(p['code']);g=feature_geometry(f);by_dep[p['departement']].append(g)
 if m and m.get('arrondissement'):
  by_arr[m['arrondissement']].append(g)
  if m.get('rangChefLieu',0)>=3:arr_info[m['arrondissement']]=m['nom']
dep_meta=json.loads((ROOT/'test-output/light-sources/departements.geojson').read_text(encoding='utf-8'))['features'];dep_names={f['properties']['code']:f['properties']['nom']for f in dep_meta}
for code,geoms in by_arr.items():
 name=arr_info.get(code,'arrondissement '+code)
 store('college-atlas-fr-arr-'+code,f'France · {name} — arrondissement {code}','France · arrondissements',[unary_union(geoms)],urls['communes.geojson'],'IGN / Etalab — contours et découpage administratif','Licence Ouverte 2.0','Contours et regroupements téléchargés le 25/10/2026',desc=name,priority=2)
for code,geoms in by_dep.items():
 name=dep_names.get(code,code)
 store('college-atlas-fr-communes-'+code,f'{name} ({code}) — communes sans noms','France · communes par département',geoms,urls['communes.geojson'],'IGN / Etalab — contours administratifs','Licence Ouverte 2.0','Géométries SHA-256 '+sha(SRC/'communes.geojson'),priority=1)
 arrs=[unary_union(gs)for arr,gs in by_arr.items()if arr[:-1]==code]
 if arrs:store('college-atlas-fr-arrondissements-'+code,f'{name} ({code}) — arrondissements sans noms','France · arrondissements par département',arrs,urls['communes.geojson'],'IGN / Etalab — contours et découpage administratif','Licence Ouverte 2.0','Contours et regroupements téléchargés le 25/10/2026',priority=1)
print('FRANCE DONE',len(created),flush=True)
(OUT/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
proof={'downloads':{name:{'url':url,'sha256':sha(SRC/name)}for name,url in urls.items()if(SRC/name).is_file()},'maps':len(created),'projection':'Local equirectangular with latitude compensation','simplification':'bounding box span / 1100; topology preserved','license':'Natural Earth public domain; Etalab Licence Ouverte 2.0'}
(OUT/'sources/light/atlas-provenance.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copyfile(SRC/'ne-terms.html',OUT/'licenses/light/natural-earth-terms.html')
font=ImageFont.truetype(str(ROOT/'assets/fonts/NotoSerif-Variable.ttf'),13);sample=created[::max(1,len(created)//20)][:20];sheet=Image.new('RGB',(1000,850),'#f0f4f8');d=ImageDraw.Draw(sheet)
for i,e in enumerate(sample):
 x=i%4*250;y=i//4*170;im=Image.open(OUT/e['filename']).convert('RGB');im.thumbnail((230,135));sheet.paste(im,(x+10,y+5));d.text((x+10,y+143),e['title'][:29],font=font,fill='black')
sheet.save(ROOT/'test-output/atlas-preview.jpg')
print(json.dumps(dict(created=len(created),total=len(catalog),image_bytes=sum((OUT/e['filename']).stat().st_size for e in created),categories=dict(Counter(e['category']for e in catalog))),ensure_ascii=False),flush=True)
