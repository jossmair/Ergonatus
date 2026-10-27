from pathlib import Path
import requests,json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
OUT=Path('test-output/reference-sources');s=requests.Session();s.headers['User-Agent']='Ecrinator public-domain school illustration curation'
url='https://www.gutenberg.org/ebooks/50316';p=OUT/'dore-fables-source.html'
if not p.exists():r=s.get(url,timeout=60);r.raise_for_status();p.write_bytes(r.content)
soup=BeautifulSoup(p.read_bytes(),'html.parser');links=[a['href']for a in soup.select('a[href]')if '.epub3.images' in a['href']]
assert links,'No illustrated EPUB link'
book=OUT/'dore-fables-50316.epub';download=urljoin(url,links[0])
if not book.exists():
 r=s.get(download,timeout=180)
 if r.status_code==429:raise SystemExit('Stop: '+r.headers.get('Retry-After','60'))
 r.raise_for_status();assert r.content.startswith(b'PK');book.write_bytes(r.content)
(OUT/'dore-fables-provenance.json').write_text(json.dumps(dict(source=url,download=download,illustrator='Gustave Doré (1832–1883)',rights='Public domain in the USA, per publisher; original nineteenth-century engravings by Doré.',biographical_proof='https://catalogue.bnf.fr/ark:/12148/cb30716029z'),ensure_ascii=False,indent=2),encoding='utf-8');print(book.stat().st_size)
