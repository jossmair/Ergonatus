"""Acquire two individually licensed French history maps for visual selection."""
from pathlib import Path
from PIL import Image
from bs4 import BeautifulSoup
import requests,json,time,hashlib,re
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/library/reference/maps-next';OUT.mkdir(exist_ok=True)
selection=[('Empire carolingien 814-fr.svg','L’empire carolingien en 814','5e','L’Europe carolingienne'),('France in 1789.svg','La France et ses provinces en 1789','4e','La France avant la Révolution')]
session=requests.Session();session.headers['User-Agent']='Ecrinator/0.12 school reference library curation'
def get(url,**kwargs):
 response=session.get(url,timeout=90,**kwargs)
 if response.status_code==429:raise SystemExit('All Wikimedia requests stopped. Retry-After: '+response.headers.get('Retry-After','60'))
 response.raise_for_status();return response
cache=OUT/'metadata.json'
if not cache.exists():
 data=get('https://commons.wikimedia.org/w/api.php',params=dict(action='query',format='json',titles='|'.join('File:'+e[0]for e in selection),prop='imageinfo',iiprop='url|extmetadata|timestamp|sha1',iiurlwidth=1400)).json();cache.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');time.sleep(5)
pages={p['title'].removeprefix('File:'):p for p in json.loads(cache.read_text(encoding='utf-8'))['query']['pages'].values()}
entries=[]
for name,title,grade,topic in selection:
 page=pages[name];info=page['imageinfo'][0];meta=info['extmetadata'];short=meta['LicenseShortName']['value'];license_url=meta.get('LicenseUrl',{}).get('value','')
 if 'public domain'in short.lower():license='Public domain';license_url=info['descriptionurl']+'#Licensing'
 else:
  assert re.search(r'creativecommons.org/licenses/by-sa/4.0',license_url),short
  license='CC BY-SA 4.0'
 ident='reference-map-'+str(page['pageid']);raw=OUT/(ident+'-download.bin')
 if not raw.exists():raw.write_bytes(get(info['thumburl']).content);time.sleep(4)
 original=OUT/(ident+'-original.svg')
 if not original.exists():original.write_bytes(get(info['url']).content);time.sleep(4)
 image=Image.open(raw).convert('RGBA');white=Image.new('RGBA',image.size,'white');white.alpha_composite(image);image=white.convert('RGB');file=OUT/(ident+'.jpg');image.save(file,quality=94,subsampling=0,optimize=True)
 thumb=image.copy();thumb.thumbnail((300,190));thumb.save(OUT/(ident+'-thumb.jpg'),quality=90,optimize=True)
 author=BeautifulSoup(meta['Artist']['value'],'html.parser').get_text(' ',strip=True)
 if name.startswith('Empire carolingien'):author+=' ; Romain0 (version française)'
 e=dict(id=ident,title=title,category='Cartes',subjects=['Histoire-géographie'],topic=topic,curriculum_theme=topic,learning_objective='Identifier les espaces représentés, lire les repères et expliquer la légende à partir du cours.',grades=[grade],cycle='',domain='history',educational_use='À étudier',kind='Carte expliquée',language='fr',unlabelled=False,monochrome=False,filename=file.name,width=image.width,height=image.height,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),author=author,license=license,license_url=license_url,source_url=info['descriptionurl'],license_proof_url=info['descriptionurl']+'#Licensing',source_timestamp=info['timestamp'],source_sha1=info['sha1'],changes='Aperçu Wikimedia composé sur fond blanc et compressé en JPEG qualité 94 sans sous-échantillonnage chromatique.',review_status='Contrôle visuel requis',tags=title+' '+topic)
 entries.append(e)
(OUT/'candidates.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8')
print([(e['id'],e['title'],e['license'])for e in entries])
