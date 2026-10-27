from pathlib import Path
import requests,json,time
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-output/reference-sources';s=requests.Session();s.headers['User-Agent']='Ecrinator school reference curation'
urls={f'siyavula-grade{g}.epub':f'https://www.siyavula.com/downloads/books/science/Gr{g}_PhysicalSciences_Learner_Eng_CC-BY.epub'for g in [7,8,9]}
urls.update({
'sesamath-script.js':'https://manuel.sesamath.net/_tmp/js_script_1783244576.mini.js',
'lls-legal.html':'https://www.lelivrescolaire.fr/informations/mentions-legales',
'openstax-history-search.json':'https://api.github.com/search/repositories?q=org%3Aopenstax+history&per_page=30',
'forge-prof-history-tree.json':'https://forge.apps.education.fr/api/v4/projects/5186/repository/tree?recursive=true&per_page=100',
'forge-prof-history-license.json':'https://forge.apps.education.fr/api/v4/projects/5186?license=true',
'forge-college-history-tree.json':'https://forge.apps.education.fr/api/v4/projects/9592/repository/tree?recursive=true&per_page=100',
'forge-college-history-license.json':'https://forge.apps.education.fr/api/v4/projects/9592?license=true',
'forge-hg-manuel-tree.json':'https://forge.apps.education.fr/api/v4/projects/7857/repository/tree?recursive=true&per_page=100',
'forge-hg-manuel-license.json':'https://forge.apps.education.fr/api/v4/projects/7857?license=true',
})
for name,url in urls.items():
 try:
  p=OUT/name
  if not p.exists():r=s.get(url,timeout=180);r.raise_for_status();p.write_bytes(r.content)
  print(name,p.stat().st_size,flush=True)
 except Exception as e:print('UNAVAILABLE',name,str(e),flush=True)
(OUT/'DOWNLOAD-URLS-2.json').write_text(json.dumps(urls,ensure_ascii=False,indent=2),encoding='utf-8')
