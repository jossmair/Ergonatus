"""Download attributed historical SVG basemaps, respecting Wikimedia rate limits."""
from pathlib import Path
import requests,json,time
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'test-output/history-sources';out.mkdir(exist_ok=True)
s=requests.Session();s.headers['User-Agent']='Ecrinator/0.11 offline school atlas, user requested'
def get(url,params=None):
 time.sleep(3);r=s.get(url,params=params,timeout=60)
 for attempt in range(3):
  if r.status_code!=429:break
  wait=int(r.headers.get('Retry-After','60'))
  if wait>45:raise RuntimeError('Rate limited; long cooldown: '+str(wait))
  print('Server cooldown',max(10,wait),'seconds',flush=True);time.sleep(max(10,wait));r=s.get(url,params=params,timeout=60)
 if r.status_code==429:raise RuntimeError('Rate limited; stopped after bounded retries')
 r.raise_for_status();return r
cache=out/'catalog-api.json'
if not cache.exists():
 data=get('https://commons.wikimedia.org/w/api.php',dict(action='query',generator='categorymembers',gcmtitle='Category:Blank SVG maps of Europe for historical use',gcmtype='file',gcmlimit=100,prop='imageinfo',iiprop='url|size|timestamp|extmetadata',format='json')).json();cache.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
records=json.loads((out/'records.json').read_text(encoding='utf-8'))if(out/'records.json').exists()else[]
try:
 for p in sorted(json.loads(cache.read_text(encoding='utf-8')).get('query',{}).get('pages',{}).values(), key=lambda p: (next((i for i,x in enumerate(['1914','1920','1939','1956','1815','1789'])if x in p['title']),99),p['title'])):
  info=p.get('imageinfo',[{}])[0];lic=info.get('extmetadata',{}).get('LicenseShortName',{}).get('value','');ident=str(p['pageid'])
  if not p['title'].endswith('.svg')or info.get('size',99999999)>3_000_000 or lic not in ['CC BY-SA 4.0','CC BY-SA 3.0','CC BY-SA 2.5','CC BY 4.0','CC BY 3.0','CC0','Public domain']:continue
  if any(e['id']==ident for e in records):continue
  try:blob=get(info['url']).content
  except RuntimeError as error:
   if 'long cooldown' in str(error):raise
   print('SKIP FILE after cooldown',p['title'],str(error),flush=True);time.sleep(10);continue
  (out/(ident+'.svg')).write_bytes(blob)
  records.append(dict(id=ident,title=p['title'],info=info,license=lic))
  (out/'records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
  print(p['title'],lic,flush=True)
except Exception as e: print('SOURCE PAUSE',str(e),flush=True)
print('Historic maps downloaded:',len(records),flush=True)
