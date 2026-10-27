"""Enrich textbook provenance from the actual publisher download headings."""
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import parse_qs,urlparse
import json
BASE=Path(__file__).resolve().parents[1]/'test-output/reference-sources'
pages={'sesamath-6e-2025.html':'telechargement_6e_cahier_2025','sesamath-5e-2026.html':'telechargement_5e_cahier_2026','sesamath-cycle4.html':'telechargement_cycle4_2016','sesamath-cycle4-cahier.html':'telechargement_cycle4_cahier_2017'}
manifest=BASE/'sesamath/manifest.json';items=json.loads(manifest.read_text(encoding='utf-8'))
for item in items:
 soup=BeautifulSoup((BASE/item['source']).read_bytes(),'html.parser')
 a=next((a for a in soup.select('a[href]') if item['filename'] in a['href']),None)
 chapter=''
 if a:
  for previous in a.find_all_previous(['h2','h3','h4','h5','h6','strong','b']):
   text=previous.get_text(' ',strip=True)
   if text.startswith('Chapitre'):chapter=text;break
 item['chapter']=chapter
 item['source_page']='https://manuel.sesamath.net/index.php?page='+pages[item['source']]
 item['license']='CC BY-SA 2.0 FR';item['license_url']='https://creativecommons.org/licenses/by-sa/2.0/fr/'
 item['license_proof_url']='https://manuel.sesamath.net/index.php?page=faq'
manifest.write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
print('Metadata updated:',len(items),'chapter headings:',sum(bool(x['chapter'])for x in items))

