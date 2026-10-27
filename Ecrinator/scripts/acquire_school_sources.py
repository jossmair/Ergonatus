"""Fetch pinned, openly licensed source collections. Never executes downloaded code."""
from pathlib import Path
import json,time,urllib.request
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-output/library-collections';OUT.mkdir(exist_ok=True)
UA='Ecrinator/0.9 local offline school catalogue'
def fetch(url,path,limit=600*1024*1024):
 if path.exists():return
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':UA}),timeout=90)as source,path.open('wb')as target:
  count=0
  while chunk:=source.read(1024*1024):
   count+=len(chunk)
   if count>limit:raise ValueError('Collection too large')
   target.write(chunk)
 print('DOWNLOADED',path.name,path.stat().st_size,flush=True)
for repo in ['osbooks-biology-bundle','osbooks-university-physics-bundle','osbooks-anatomy-physiology']:
 try:
  request=urllib.request.Request(f'https://api.github.com/repos/openstax/{repo}/commits?until=2024-12-31T23:59:59Z&per_page=1',headers={'User-Agent':UA})
  with urllib.request.urlopen(request,timeout=45)as r:commits=json.load(r)
  if not commits:continue
  sha=commits[0]['sha'];meta={'repository':repo,'commit':sha,'date':commits[0]['commit']['committer']['date'],'source':f'https://github.com/openstax/{repo}/tree/{sha}'}
  fetch(f'https://raw.githubusercontent.com/openstax/{repo}/{sha}/LICENSE',OUT/(repo+'-LICENSE.txt'),1024*1024)
  license=(OUT/(repo+'-LICENSE.txt')).read_text(encoding='utf-8')
  if 'NonCommercial' in license or 'Attribution 4.0' not in license:print('REJECT LICENSE',repo,flush=True);continue
  (OUT/(repo+'.json')).write_text(json.dumps(meta,indent=2),encoding='utf-8')
  fetch(f'https://codeload.github.com/openstax/{repo}/zip/{sha}',OUT/(repo+'.zip'))
 except Exception as e:print('FAILED',repo,type(e).__name__,str(e),flush=True)
 time.sleep(2)
fetch('https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson',OUT/'natural-earth-countries.geojson',16*1024*1024)
fetch('https://www.naturalearthdata.com/about/terms-of-use/',OUT/'natural-earth-terms.html',1024*1024)
