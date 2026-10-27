from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin,parse_qs,urlparse
import requests,json,time,concurrent.futures,threading
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'test-output/reference-sources';OUT=BASE/'sesamath';OUT.mkdir(exist_ok=True)
items=[]
for source,grades in [('sesamath-6e-2025.html',['6e']),('sesamath-5e-2026.html',['5e']),('sesamath-cycle4.html',['5e','4e','3e']),('sesamath-cycle4-cahier.html',['5e','4e','3e'])]:
 soup=BeautifulSoup((BASE/source).read_bytes(),'html.parser')
 for a in soup.select('a[href]'):
  url=urljoin('https://manuel.sesamath.net/index.php',a['href'])
  if '.odt'not in url or '_dys.'in url:continue
  filename=parse_qs(urlparse(url).query).get('file',[''])[0].split('/')[-1]
  if not filename.endswith('.odt'):continue
  row=a.find_parent('li');label=row.get_text(' ',strip=True)if row else filename
  items.append(dict(filename=filename,url=url,grades=grades,source_page='https://manuel.sesamath.net/index.php?page='+source.removeprefix('sesamath-').removesuffix('.html'),label=label,source=source))
items=list({x['filename']:x for x in items}.values());print('ODT SOURCES',len(items),flush=True)
def fetch(e):
 p=OUT/e['filename']
 if not p.exists():
  r=requests.get(e['url'],headers={'User-Agent':'Ecrinator school reference library; Sésamath CC BY-SA source curation'},timeout=60)
  if r.status_code==429:raise RuntimeError('Server requests cooldown '+r.headers.get('Retry-After','60'))
  r.raise_for_status()
  if not r.content.startswith(b'PK'):raise ValueError('Not an ODT file')
  p.write_bytes(r.content);time.sleep(.3)
 return e
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
 futures={pool.submit(fetch,e):e for e in items}
 for future in concurrent.futures.as_completed(futures):
  try:results.append(future.result())
  except Exception as error:print('SKIP',futures[future]['filename'],str(error),flush=True)
  if len(results)%25==0:print('DOWNLOADED',len(results),flush=True)
(OUT/'manifest.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8');print('COMPLETE',len(results),flush=True)
