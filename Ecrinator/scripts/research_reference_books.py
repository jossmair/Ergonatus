from pathlib import Path
import requests,json
from bs4 import BeautifulSoup
out=Path('test-output/reference-sources');s=requests.Session();s.headers['User-Agent']='Ecrinator school reference library'
for key,url in {
'siyavula-repos.json':'https://api.github.com/orgs/Siyavula/repos?per_page=100',
'sesamath-6e-2025.html':'https://manuel.sesamath.net/index.php?page=telechargement_6e_cahier_2025',
'sesamath-5e-2026.html':'https://manuel.sesamath.net/index.php?page=telechargement_5e_cahier_2026',
'sesamath-cycle4.html':'https://manuel.sesamath.net/index.php?page=telechargement_cycle4_2016',
'sesamath-cycle4-cahier.html':'https://manuel.sesamath.net/index.php?page=telechargement_cycle4_cahier_2017',
'history-book-license.json':'https://api.github.com/repos/openstax/osbooks-world-history/contents/LICENSE',
'history-book-license-commits.json':'https://api.github.com/repos/openstax/osbooks-world-history/commits?path=LICENSE&per_page=100',
}.items():
 try:
  p=out/key
  if not p.exists():r=s.get(url,timeout=60);r.raise_for_status();p.write_bytes(r.content)
  print(key,p.stat().st_size,flush=True)
  if key.startswith('sesamath'):
   soup=BeautifulSoup(p.read_bytes(),'html.parser');links=[{'text':a.get_text(' ',strip=True),'href':a['href']}for a in soup.select('a[href]')if any(x in a['href'] for x in ['.zip','.odt','.pdf','.sxw'])];(out/(key+'.files.json')).write_text(json.dumps(links,ensure_ascii=False,indent=2),encoding='utf-8');print('FILES',links[:5],flush=True)
 except Exception as e:print('UNAVAILABLE',key,str(e),flush=True)
