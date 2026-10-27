"""Import genuinely dated historical basemaps, with attribution per source file."""
from pathlib import Path
from io import BytesIO
from xml.etree import ElementTree as ET
from PIL import Image
import json,hashlib,html,re,cairosvg
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/library';SRC=ROOT/'test-output/history-sources'
records=json.loads((SRC/'records.json').read_text(encoding='utf-8'))if(SRC/'records.json').exists()else[]
catalog=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));catalog=[e for e in catalog if not e['id'].startswith('college-history-')];seen={e['sha256']for e in catalog};added=0
clean=lambda v:html.unescape(re.sub('<[^>]+>',' ',v)).strip()
def deny(url,kind):raise ValueError('External references not allowed')
for record in records:
 try:
  ident='college-history-'+record['id'];filename=ident+'.png';raw=(SRC/(record['id']+'.svg')).read_bytes();tree=ET.fromstring(raw)
  for parent in tree.iter():
   for node in list(parent):
    if node.tag.rsplit('}',1)[-1]in ['text','image','script','foreignObject']:parent.remove(node)
  for node in tree.iter():
   tag=node.tag.rsplit('}',1)[-1]
   if tag in ['path','polygon','polyline','line','ellipse','circle']:
    node.set('style',node.get('style','')+';fill:none!important;stroke:#111!important;stroke-width:0.55!important')
  svg=ET.tostring(tree);png=cairosvg.surface.PNGSurface.convert(bytestring=svg,output_width=1050,url_fetcher=deny);im=Image.open(BytesIO(png)).convert('RGBA');bg=Image.new('RGBA',im.size,'white');bg.alpha_composite(im);im=bg.convert('L').point(lambda v:0 if v<200 else 255,mode='1');buf=BytesIO();im.save(buf,format='PNG',optimize=True);data=buf.getvalue();digest=hashlib.sha256(data).hexdigest()
  if digest in seen:continue
  seen.add(digest);(OUT/filename).write_bytes(data);small=im.copy();small.thumbnail((300,195));buf=BytesIO();small.save(buf,format='PNG',optimize=True);td=buf.getvalue();(OUT/'thumbs'/filename).write_bytes(td);(OUT/'sources/light'/(ident+'.svg')).write_bytes(svg)
  info=record['info'];meta=info['extmetadata'];author=clean(meta.get('Artist',{}).get('value','Wikimedia Commons'));lic=record['license'];source='https://commons.wikimedia.org/wiki/'+record['title'].replace(' ','_');dates=re.findall(r'\b(?:[5-9]\d\d|1\d{3}|20\d\d)\b',record['title']);when='–'.join(dates)or'époque indiquée dans la source';title='Europe · '+when+' — fond historique sans légende';lic_url=meta.get('LicenseUrl',{}).get('value')or{'CC BY-SA 4.0':'https://creativecommons.org/licenses/by-sa/4.0/','CC BY-SA 3.0':'https://creativecommons.org/licenses/by-sa/3.0/','CC BY-SA 2.5':'https://creativecommons.org/licenses/by-sa/2.5/','CC BY 4.0':'https://creativecommons.org/licenses/by/4.0/','CC BY 3.0':'https://creativecommons.org/licenses/by/3.0/','CC0':'https://creativecommons.org/publicdomain/zero/1.0/','Public domain':source}[lic]
  catalog.append(dict(id=ident,title=title,category='Cartes',topic='Histoire · Europe',tags=f'{title} {record["title"]} histoire carte historique Europe médiévale moderne contemporaine',filename=filename,author=author,license=lic,license_url=lic_url,source_url=source,source_timestamp=info.get('timestamp',''),changes='Fond historique téléchargé ; texte retiré et traits convertis en noir sur blanc pour un usage scolaire. Géométrie de la carte source conservée. L’époque vient du fichier original, sans modifier ses frontières.',width=im.width,height=im.height,sha256=digest,thumbnail_sha256=hashlib.sha256(td).hexdigest(),source_sha256=hashlib.sha256(raw).hexdigest(),license_proof_url=source,embedded=True,level='college',kind='Fond de carte',monochrome=True,unlabelled=True,subjects=['Cartes','Histoire-géographie'],priority=0))
  added+=1
 except Exception as error:print('SKIP',record['title'],str(error))
(OUT/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8');(OUT/'sources/light/historical-provenance.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8');print('Historical basemaps imported:',added,'total:',len(catalog))
