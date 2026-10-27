from pathlib import Path
import requests,json,re,time,hashlib
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-output/reference-sources';OUT.mkdir(exist_ok=True)
s=requests.Session();s.headers['User-Agent']='Ecrinator school reference library / educational source research'
urls={
'siyavula-read.html':'https://www.siyavula.com/read',
'sesamath-downloads.html':'https://manuel.sesamath.net/index.php?page=telechargement',
'sesamath-license.html':'https://manuel.sesamath.net/index.php?page=faq',
'programmes-cycle4.html':'https://eduscol.education.gouv.fr/4362/enseigner-au-cycle-4',
'programmes-college.html':'https://www.education.gouv.fr/les-programmes-du-college-470408',
'forge-history.json':'https://forge.apps.education.fr/api/v4/projects?search=histoire&simple=true&per_page=100',
'forge-geo.json':'https://forge.apps.education.fr/api/v4/projects?search=geographie&simple=true&per_page=100',
'github-siyavula.json':'https://api.github.com/orgs/Siyavula-books/repos?per_page=100',
'lls-home.html':'https://www.lelivrescolaire.fr/',
'visions-carto-license.html':'https://visionscarto.net/a-propos',
'openstax-history.json':'https://api.github.com/repos/openstax/osbooks-world-history-bundle',
}
for name,url in urls.items():
 try:
  p=OUT/name
  if not p.exists():
   r=s.get(url,timeout=60);r.raise_for_status();p.write_bytes(r.content)
  print(name,p.stat().st_size,flush=True)
 except Exception as e:print('UNAVAILABLE',name,str(e),flush=True)
for filename in ['siyavula-read.html','sesamath-downloads.html','lls-home.html']:
 p=OUT/filename
 if not p.exists():continue
 soup=BeautifulSoup(p.read_bytes(),'html.parser')
 links=[{'text':a.get_text(' ',strip=True),'href':a.get('href','')}for a in soup.find_all('a',href=True)]
 (OUT/(filename+'.links.json')).write_text(json.dumps(links,ensure_ascii=False,indent=2),encoding='utf-8')
 print(filename,[(a['text'],a['href'])for a in links if ('CC-BY' in a['text'] and 'ND'not in a['text'])or re.search('zip|\.odt|mentions|legal|licence',a['href'],re.I)][:30],flush=True)
(OUT/'SOURCE-URLS.json').write_text(json.dumps(urls,ensure_ascii=False,indent=2),encoding='utf-8')
