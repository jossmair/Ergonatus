"""Polite download of small, explicitly licensed maps and unlabelled diagrams."""
from pathlib import Path
import requests,json,time,re
root=Path(__file__).resolve().parents[1];out=root/'test-output/light-sources/commons';out.mkdir(exist_ok=True)
s=requests.Session();s.headers['User-Agent']='Ecrinator/0.10 school offline curation (user requested)'
queries=[('Cartes','France','incategory:"SVG blank maps of France"'),('Cartes','Histoire','intitle:"blank" Europe 1914 filetype:drawing'),('Cartes','Histoire','intitle:"Europe 1789" filetype:drawing'),('Cartes','Histoire','intitle:"Roman Empire" intitle:"blank" filetype:drawing'),('SVT','Schémas à légender','intitle:"unlabeled" filetype:drawing'),('SVT','Schémas à légender','intitle:"unlabelled" filetype:drawing'),('Physique-chimie','Circuits simples','intitle:"simple circuit" filetype:drawing'),('Physique-chimie','Schémas à compléter','intitle:"unlabeled" physics filetype:drawing')]
records=json.loads((out/'records.json').read_text(encoding='utf-8')) if (out/'records.json').exists() else []
def get(url,params=None):
 time.sleep(1.3);r=s.get(url,params=params,timeout=45)
 if r.status_code==429:raise RuntimeError('Wikimedia demande une pause ; aucun nouvel essai pendant son délai.')
 r.raise_for_status();return r
for category,topic,query in queries:
 cache=out/('query-'+str(queries.index((category,topic,query)))+'.json')
 try:
  if not cache.exists():cache.write_text(get('https://commons.wikimedia.org/w/api.php',dict(action='query',generator='search',gsrsearch=query,gsrnamespace=6,gsrlimit=20,prop='imageinfo',iiprop='url|size|timestamp|extmetadata',format='json')).text,encoding='utf-8')
  for page in json.loads(cache.read_text(encoding='utf-8')).get('query',{}).get('pages',{}).values():
   info=page.get('imageinfo',[{}])[0];meta=info.get('extmetadata',{});lic=meta.get('LicenseShortName',{}).get('value','')
   title=page['title'];key=str(page['pageid'])
   if not title.lower().endswith('.svg')or info.get('size',9_000_000)>1_200_000 or lic not in ['Public domain','CC0','CC BY 4.0','CC BY-SA 4.0','CC BY-SA 3.0','CC BY-SA 2.5','CC BY 3.0']:continue
   if category=='SVT'and not re.search('unlabel|blank|without.labels|no.labels',title,re.I):continue
   if any(x['id']==key for x in records):continue
   path=out/(key+'.svg')
   if not path.exists():
    blob=get(info['url']).content
    if len(blob)>1_200_000:continue
    path.write_bytes(blob)
   record=dict(id=key,title=title,category=category,topic=topic,info=info);records.append(record)
   (out/'records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
   print('DOWNLOADED',title,flush=True)
 except Exception as e:
  print('SOURCE PAUSE',str(e),flush=True)
  if 'pause'in str(e):break
print('COMMONS',len(records),flush=True)
