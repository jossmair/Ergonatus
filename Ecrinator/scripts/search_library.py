"""Development-only Commons research; no network code ships in Écrinator."""
from pathlib import Path
import json, time, urllib.request, urllib.parse

queries = {
    'Cartes': ['Blank world map svg', 'France blank map regions svg', 'Europe blank map svg', 'Africa blank map svg', 'Asia blank map svg', 'World physical map', 'France relief map'],
    'SVT': ['Animal Cell Unannotated', 'Plant cell structure fr', 'Prokaryote cell diagram', 'Human heart diagram french', 'Respiratory system complete fr', 'Photosynthesis fr diagram', 'Leaf tissue diagram', 'DNA structure diagram'],
    'Physique-chimie': ['Simple electric circuit svg', 'Series parallel circuit svg', 'States of matter fr', 'Prism spectrum svg', 'Water molecule svg', 'Atom diagram svg', 'Solar system sizes', 'Lens ray diagram svg'],
}
root = Path(__file__).resolve().parents[1]
out = root / 'test-output/library-research'
out.mkdir(parents=True, exist_ok=True)
results = []
for category, terms in queries.items():
    for term in terms:
        params = {'action':'query','format':'json','generator':'search','gsrsearch':term,'gsrnamespace':6,'gsrlimit':3,
                  'prop':'imageinfo','iiprop':'url|extmetadata|size','iiurlwidth':1280}
        url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={'User-Agent':'EcrinatorLibrary/0.8 educational offline catalog'})
        try:
            with urllib.request.urlopen(req, timeout=30) as r: data = json.load(r)
            for page in data.get('query',{}).get('pages',{}).values():
                info = page.get('imageinfo',[{}])[0]
                meta = info.get('extmetadata',{})
                license = meta.get('LicenseShortName',{}).get('value','')
                if license not in ['Public domain','CC0','CC BY 4.0','CC BY-SA 4.0','CC BY 3.0','CC BY-SA 3.0']: continue
                if not info.get('thumburl','').split('?')[0].lower().endswith(('.png','.jpg','.jpeg')): continue
                entry = {'category':category,'query':term,'title':page['title'],'license':license,'info':info}
                if not any(e['title']==entry['title'] for e in results): results.append(entry)
        except Exception as e: print('Skipped',term,type(e).__name__,flush=True)
        time.sleep(.3)
out.joinpath('candidates.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
for i,e in enumerate(results): print(i,e['category'],e['title'],e['license'],flush=True)
