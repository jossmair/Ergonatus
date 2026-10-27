"""Acquire a named set of curriculum maps, each with individual Commons rights.
Stops all requests on 429; cache makes subsequent runs incremental.
"""
from pathlib import Path
import requests,json,time,hashlib,re
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'test-output/reference-sources/maps';OUT=ROOT/'assets/library/reference/maps';OUT.mkdir(exist_ok=True)
s=requests.Session();s.headers['User-Agent']='Ecrinator/0.12 school reference library curation'
selection=json.loads((OUT.parent/'map-selection.json').read_text(encoding='utf-8'));metadata={}
def request(url,**kwargs):
 r=s.get(url,timeout=90,**kwargs)
 if r.status_code==429:raise SystemExit('Stop all Wikimedia access; Retry-After '+r.headers.get('Retry-After','60'))
 r.raise_for_status();return r
for start in range(0,len(selection),25):
 p=BASE/('selected-metadata-'+str(start)+'.json')
 if not p.exists():
  r=request('https://commons.wikimedia.org/w/api.php',params=dict(action='query',format='json',titles='|'.join('File:'+e['source_name']for e in selection[start:start+25]),prop='imageinfo',iiprop='url|extmetadata|timestamp|sha1',iiurlwidth=1400));p.write_text(json.dumps(r.json(),ensure_ascii=False,indent=2),encoding='utf-8');time.sleep(6)
 data=json.loads(p.read_text(encoding='utf-8'))
 for page in data.get('query',{}).get('pages',{}).values():metadata[page['title'].removeprefix('File:').replace('_',' ')]=page
entries=[];excluded=[]
for selected in selection:
 name=selected['source_name'].replace('_',' ');page=metadata.get(name)
 if not page or 'missing'in page or not page.get('imageinfo'):excluded.append(dict(name=name,reason='Source file not found'));continue
 info=page['imageinfo'][0];meta=info.get('extmetadata',{});short=meta.get('LicenseShortName',{}).get('value','');url=meta.get('LicenseUrl',{}).get('value','');license=None
 if 'public domain'in short.lower():license='Public domain';url=info['descriptionurl']+'#Licensing'
 elif short.lower().startswith('cc0'):license='CC0 1.0';url='https://creativecommons.org/publicdomain/zero/1.0/'
 else:
  match=re.search(r'creativecommons.org/licenses/(by(?:-sa)?)/([0-9.]+)',url)
  if match:license=('CC BY-SA 'if match[1]=='by-sa'else'CC BY ')+match[2]
 if not license:excluded.append(dict(name=name,reason='Licence not in the allowed set',license=short,url=url));continue
 author=BeautifulSoup(meta.get('Artist',{}).get('value',''),'html.parser').get_text(' ',strip=True)
 if not author:excluded.append(dict(name=name,reason='Author missing'));continue
 ident='reference-map-'+str(page['pageid']);rawpath=OUT/(ident+'-download.bin')
 if not rawpath.exists():
  raster=info.get('thumburl',info['url']);r=request(raster)
  if len(r.content)>12*1024*1024:excluded.append(dict(name=name,reason='Raster preview too large'));continue
  rawpath.write_bytes(r.content);time.sleep(3)
 try:im=Image.open(BytesIO(rawpath.read_bytes()));im.load()
 except Exception as error:excluded.append(dict(name=name,reason='Raster decode: '+str(error)));continue
 if max(im.size)>1800:im.thumbnail((1800,1800))
 im=im.convert('RGBA');white=Image.new('RGBA',im.size,'white');white.alpha_composite(im);im=white.convert('RGB');file=OUT/(ident+'.png');im.save(file,optimize=True);thumb=im.copy();thumb.thumbnail((300,190));thumb.save(OUT/(ident+'-thumb.png'),optimize=True)
 proof=OUT/(ident+'-rights.json');proof.write_text(json.dumps(page,ensure_ascii=False,indent=2),encoding='utf-8')
 if info['url'].lower().endswith('.svg'):
  vector=OUT/(ident+'-original.svg')
  if not vector.exists():
   r=request(info['url'])
   if len(r.content)<=12*1024*1024:vector.write_bytes(r.content)
   time.sleep(3)
 small=im.copy();small.thumbnail((100,100));mono=all(max(p)-min(p)<12 for p in small.getdata())
 e=dict(selected);e.update(id=ident,filename=file.name,kind='Fond de carte'if selected['educational_use']=='À compléter'else'Carte expliquée',unlabelled=selected['educational_use']=='À compléter',monochrome=mono,width=im.width,height=im.height,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),thumbnail_sha256=hashlib.sha256((OUT/(ident+'-thumb.png')).read_bytes()).hexdigest(),author=author,license=license,license_url=url,source_url=info['descriptionurl'],license_proof_url=info['descriptionurl']+'#Licensing',source_timestamp=info.get('timestamp',''),source_sha1=info.get('sha1',''),caption=BeautifulSoup(meta.get('ImageDescription',{}).get('value',''),'html.parser').get_text(' ',strip=True)[:1200],changes='Aperçu raster produit par Wikimedia puis PNG optimisé ; carte, couleurs, légende et limites conservées.',review_status='Licence individuelle vérifiée ; contrôle visuel requis')
 entries.append(e);(OUT/'candidates.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8');print('ACQUIRED',name,license,flush=True)
(OUT/'exclusions.json').write_text(json.dumps(excluded,ensure_ascii=False,indent=2),encoding='utf-8');print('Maps acquired',len(entries),'excluded',len(excluded))
