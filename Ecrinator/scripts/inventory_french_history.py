"""Inventory French teacher geography/history resources; never infer image rights
from a repository licence alone. Saves review metadata, no catalogue publication.
"""
from pathlib import Path
import requests,json,time
OUT=Path('test-output/reference-sources');S=requests.Session();S.headers['User-Agent']='Ecrinator curriculum reference curation'
project=5186;rows=[]
for page in range(1,81):
 p=OUT/('forge-hg-tree-'+str(page)+'.json')
 if p.exists():batch=json.loads(p.read_text(encoding='utf-8'))
 else:
  r=S.get(f'https://forge.apps.education.fr/api/v4/projects/{project}/repository/tree',params=dict(recursive='true',per_page=100,page=page),timeout=60)
  if r.status_code==429:raise SystemExit('Rate limited; stop and honour Retry-After '+r.headers.get('Retry-After','60'))
  r.raise_for_status();batch=r.json();p.write_text(json.dumps(batch,ensure_ascii=False),encoding='utf-8');time.sleep(.3)
 rows.extend(batch)
 if len(batch)<100:break
images=[e for e in rows if e['type']=='blob' and Path(e['path']).suffix.lower()in ['.svg','.png','.jpg','.jpeg','.webp']]
(OUT/'forge-hg-image-inventory.json').write_text(json.dumps(images,ensure_ascii=False,indent=2),encoding='utf-8')
print('Inventoried',len(rows),'files/directories,',len(images),'image candidates; third-party rights still require checking')
