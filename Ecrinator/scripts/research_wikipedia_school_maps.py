from pathlib import Path
import requests,json,time,re
OUT=Path('test-output/reference-sources/maps');s=requests.Session();s.headers['User-Agent']='Ecrinator/0.12 college reference map review'
articles=['Empire romain','Expansion de l’islam','Grandes découvertes','Colonisation','Première Guerre mondiale','Seconde Guerre mondiale','Guerre froide','Décolonisation','Révolution française','Géographie de la France','Géographie de l’Europe','Union européenne','Croissant fertile','Grèce antique','Traites négrières','Répartition de la population mondiale']
found={}
for title in articles:
 p=OUT/('wikipedia-fr-'+re.sub(r'[^a-zA-Z0-9]+','-',title)+'.json')
 if p.exists():data=json.loads(p.read_text(encoding='utf-8'))
 else:
  r=s.get('https://fr.wikipedia.org/w/api.php',params=dict(action='parse',format='json',page=title.replace('’',"'"),prop='images',redirects=1),timeout=60)
  if r.status_code==429:raise SystemExit('Stop all Wikimedia access; Retry-After '+r.headers.get('Retry-After','60'))
  r.raise_for_status();data=r.json();p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');time.sleep(6)
 for name in data.get('parse',{}).get('images',[]):
  if not name.lower().endswith(('.svg','.png','.jpg','.jpeg'))or any(w in name.lower()for w in ['flag','logo','blason','coat_of','icon','wikimedia','wikiquote','symbol','armoirie']):continue
  if re.search(r'map|carte|empire|europe|world|expan|conqu|islam|néolith|population|koppen|climat|migrat|colon|greece|grece|mondial|meridian',name,re.I):found.setdefault(name,[]).append(title)
 (OUT/'wikipedia-fr-map-files.json').write_text(json.dumps(found,ensure_ascii=False,indent=2),encoding='utf-8');print(title,len(data.get('parse',{}).get('images',[])),flush=True)
print('Map filenames',len(found))
