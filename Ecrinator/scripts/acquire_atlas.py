from pathlib import Path
import requests,time,hashlib,json
root=Path(__file__).resolve().parents[1];out=root/'test-output/atlas-sources';out.mkdir(exist_ok=True)
urls={
'admin1.geojson':'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson',
'countries.geojson':'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_0_countries.geojson',
'communes.geojson':'https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/latest/geojson/communes-1000m.geojson',
'communes-metadata.json':'https://unpkg.com/@etalab/decoupage-administratif/data/communes.json',
'ne-terms.html':'https://www.naturalearthdata.com/about/terms-of-use/' }
s=requests.Session();s.headers['User-Agent']='Ecrinator offline school atlas / requested by user'
for filename,url in urls.items():
 p=out/filename
 if p.exists():continue
 r=s.get(url,timeout=180);r.raise_for_status();r.content.decode('utf-8');p.write_bytes(r.content);print(filename,len(r.content),hashlib.sha256(r.content).hexdigest(),flush=True)
(out/'DOWNLOADS.json').write_text(json.dumps(urls,indent=2),encoding='utf-8')
