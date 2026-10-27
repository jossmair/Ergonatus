"""Download small, licensed DATA assets only. No downloaded code is executed."""
from pathlib import Path
import requests,json,time
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-output/light-sources';OUT.mkdir(exist_ok=True)
s=requests.Session();s.headers['User-Agent']='Ecrinator/0.10 school offline illustrations (user requested curation)'
def get(url,path,limit=32*1024*1024):
 path=OUT/path
 if path.exists()and path.stat().st_size>0:return path.read_bytes()
 for attempt in range(3):
  r=s.get(url,timeout=60)
  if r.status_code==429:
   delay=int(r.headers.get('Retry-After','60'));print('Rate limit; waiting',delay,flush=True);time.sleep(delay);continue
  r.raise_for_status();data=r.content
  if len(data)>limit:raise ValueError('Source too large')
  path.write_bytes(data);print(path.name,len(data),flush=True);return data
 raise RuntimeError('Rate limit persisted')
release=json.loads(get('https://api.github.com/repos/hfg-gmuend/openmoji/releases/tags/17.0.0','openmoji-release.json'))
asset=next(a for a in release['assets']if a['name']=='openmoji-svg-black.zip')
get(asset['browser_download_url'],'openmoji-svg-black.zip')
get('https://raw.githubusercontent.com/hfg-gmuend/openmoji/17.0.0/data/openmoji.json','openmoji.json',5*1024*1024)
get('https://raw.githubusercontent.com/hfg-gmuend/openmoji/17.0.0/README.md','openmoji-README.md',1024*1024)
get('https://raw.githubusercontent.com/hfg-gmuend/openmoji/17.0.0/LICENSE.txt','openmoji-LICENSE.txt',1024*1024)
for item in ['departements','regions']:
 get(f'https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/latest/geojson/{item}-1000m.geojson',item+'.geojson',1024*1024)
get('https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/','etalab-contours.html',1024*1024)
get('https://raw.githubusercontent.com/etalab/decoupage-administratif/master/README.md','etalab-README.md',1024*1024)
print('DOWNLOADS COMPLETE',flush=True)
