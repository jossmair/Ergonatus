"""Small cached searches for actual school themes; metadata is not publication.
A 429 stops the entire run. No proxy, parallel scrape or cache-busting retries.
"""
from pathlib import Path
import requests,json,time
OUT=Path('test-output/reference-sources/maps');OUT.mkdir(exist_ok=True);s=requests.Session();s.headers['User-Agent']='Ecrinator/0.12 college map curation'
queries=[
('france-relief','France relief map filetype:drawing'),('france-fleuves','France rivers blank map filetype:drawing'),('france-muette','France blank map -locator -departments filetype:drawing'),('france-villes','France cities map filetype:drawing'),
('monde-relief','World physical map filetype:drawing'),('monde-climats','world climate map Koppen filetype:drawing'),('monde-population','World population density map'),('europe-muette','Europe blank political map filetype:drawing'),('mediterranee','Mediterranean map blank filetype:drawing'),
('grece-antique','ancient Greece map fr filetype:drawing'),('rome','Roman empire map French filetype:drawing'),('premiers-etats','Fertile Crescent map French filetype:drawing'),('islam','Islam expansion map fr filetype:drawing'),('medieval','Europe 1000 map fr filetype:drawing'),
('decouvertes','Age of discovery map French filetype:drawing'),('commerce-atlantique','triangular trade map French filetype:drawing'),('revolution','France 1789 map filetype:drawing'),('europe-1815','Europe 1815 map fr filetype:drawing'),('colonisation','colonial empires 1914 map filetype:drawing'),
('alliances-1914','Europe alliances 1914 filetype:drawing'),('front-1914','Western front 1914 1918 map French filetype:drawing'),('ww2-europe','World War II Europe 1942 map fr filetype:drawing'),('guerre-froide','Cold War alliances map French filetype:drawing'),('decolonisation','decolonization Africa map French filetype:drawing'),
('union-europeenne','European Union enlargement map French filetype:drawing'),('mobilites','world migration map filetype:drawing'),('risques','world tectonic plates map French filetype:drawing'),('republiques','France overseas map filetype:drawing')]
all_pages={}
for key,query in queries:
 p=OUT/(key+'.json')
 if p.exists():data=json.loads(p.read_text(encoding='utf-8'))
 else:
  r=s.get('https://commons.wikimedia.org/w/api.php',params=dict(action='query',format='json',generator='search',gsrnamespace=6,gsrlimit=12,gsrsearch=query,prop='imageinfo',iiprop='url|extmetadata',iiurlwidth=1200),timeout=60)
  if r.status_code==429:raise SystemExit('Stop all Commons access; Retry-After '+r.headers.get('Retry-After','60'))
  r.raise_for_status();data=r.json();p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');time.sleep(6)
 for e in data.get('query',{}).get('pages',{}).values():
  item=all_pages.setdefault(str(e['pageid']),dict(e,themes=[]));item['themes'].append(key)
 (OUT/'inventory.json').write_text(json.dumps(list(all_pages.values()),ensure_ascii=False,indent=2),encoding='utf-8')
 print(key,len(data.get('query',{}).get('pages',{})),flush=True)
(OUT/'inventory.json').write_text(json.dumps(list(all_pages.values()),ensure_ascii=False,indent=2),encoding='utf-8')
print('Unique candidate maps',len(all_pages))
