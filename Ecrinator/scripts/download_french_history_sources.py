"""Download the public teacher repository for per-document rights review.
Root licence is evidence, not automatic clearance of third-party media.
"""
from pathlib import Path
import requests,json
OUT=Path('test-output/reference-sources');s=requests.Session();s.headers['User-Agent']='Ecrinator college reference curation'
api='https://forge.apps.education.fr/api/v4/projects/5186'
meta=s.get(api+'/repository/commits/main',timeout=45);meta.raise_for_status();commit=meta.json()['id'];(OUT/'forge-history-snapshot.json').write_text(json.dumps(meta.json(),ensure_ascii=False,indent=2),encoding='utf-8')
p=OUT/'forge-history-source.zip'
if not p.exists():
 r=s.get(api+'/repository/archive.zip',params={'sha':commit},timeout=120,stream=True)
 if r.status_code==429:raise SystemExit('Rate limited: '+r.headers.get('Retry-After','60'))
 r.raise_for_status();size=0
 with p.with_suffix('.partial').open('wb')as f:
  for block in r.iter_content(524288):
   size+=len(block)
   if size>128*1024*1024:raise ValueError('Review archive exceeds 128 MiB')
   f.write(block)
 p.with_suffix('.partial').replace(p)
print(commit,p.stat().st_size)
