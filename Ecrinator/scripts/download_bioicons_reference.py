from pathlib import Path
import requests,json
BASE=Path('test-output/reference-sources');s=requests.Session();s.headers['User-Agent']='Ecrinator educational reference curation'
for name,url in {
'bioicons-icons.json':'https://raw.githubusercontent.com/duerrsimon/bioicons/main/static/icons/icons.json',
'bioicons-authors.json':'https://raw.githubusercontent.com/duerrsimon/bioicons/main/static/icons/authors.json',
'bioicons-categories.json':'https://raw.githubusercontent.com/duerrsimon/bioicons/main/static/icons/categories.json',
'bioicons-source.zip':'https://codeload.github.com/duerrsimon/bioicons/zip/refs/heads/main',
}.items():
 try:
  p=BASE/name
  if not p.exists():r=s.get(url,timeout=180);r.raise_for_status();p.write_bytes(r.content)
  print(name,p.stat().st_size,flush=True)
 except Exception as e:print('UNAVAILABLE',name,str(e),flush=True)
