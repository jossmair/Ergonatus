from pathlib import Path
import requests,json,re
from urllib.parse import urljoin,urlparse,parse_qs
out=Path('test-output/reference-sources');s=requests.Session();s.headers['User-Agent']='Ecrinator curriculum reference research'
urls={
'bioicons-tree.json':'https://api.github.com/repos/duerrsimon/bioicons/git/trees/main?recursive=1',
'siyavula-tech-repo.json':'https://api.github.com/repos/Siyavula/tech-gr7a-eng-workbook',
'siyavula-tech-tree.json':'https://api.github.com/repos/Siyavula/tech-gr7a-eng-workbook/git/trees/master?recursive=1',
}
a=json.loads((out/'sesamath-6e-2025.html.files.json').read_text(encoding='utf-8'));selected=[e['href']for e in a if re.search(r'G[12]_s[12]\.odt',e['href'])][:4]
for i,url in enumerate(selected):urls[f'sesamath-geometry-{i}.odt']=url
for name,url in urls.items():
 try:
  p=out/name
  if not p.exists():r=s.get(url,timeout=90);r.raise_for_status();p.write_bytes(r.content)
  print(name,p.stat().st_size,flush=True)
 except Exception as e:print('UNAVAILABLE',name,str(e),flush=True)
