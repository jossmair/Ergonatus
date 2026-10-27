from pathlib import Path
import requests,json
s=requests.Session();s.headers['User-Agent']='Ecrinator/0.12 college reference library source review'
p=Path('test-output/reference-sources/commons-geohistory-search.json')
params=dict(action='query',format='json',generator='search',gsrnamespace=6,gsrlimit=40,gsrsearch='intitle:map intitle:1914 -intitle:locator',prop='imageinfo',iiprop='url|extmetadata',iiurlwidth=1200)
r=s.get('https://commons.wikimedia.org/w/api.php',params=params,timeout=60)
print('Status',r.status_code)
if r.status_code==429:raise SystemExit('Stop all Commons requests; Retry-After '+r.headers.get('Retry-After','60'))
r.raise_for_status();p.write_text(json.dumps(r.json(),ensure_ascii=False,indent=2),encoding='utf-8')
for e in r.json().get('query',{}).get('pages',{}).values():
 info=e.get('imageinfo',[{}])[0];m=info.get('extmetadata',{});print(e['title'],m.get('LicenseShortName',{}).get('value','?'))
