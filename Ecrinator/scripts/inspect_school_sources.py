from pathlib import Path
from zipfile import ZipFile
from defusedxml import ElementTree as ET
import json
r=Path(__file__).resolve().parents[1]/'test-output/library-collections'
for path in r.glob('*.zip'):
 print(path.name,flush=True)
 with ZipFile(path)as z:
  for name in z.namelist():
   if name.endswith('index.cnxml'):
    tree=ET.fromstring(z.read(name))
    for f in tree.iter():
     if f.tag.split('}')[-1]=='figure':print(name,ET.tostring(f,encoding='unicode')[:2500]);break
    else:continue
    break
 print((r/(path.stem+'-LICENSE.txt')).read_text(encoding='utf-8')[:500])
d=json.loads((r/'natural-earth-countries.geojson').read_text(encoding='utf-8'))
print(len(d['features']),list(d['features'][0]['properties'].items())[:12]);print({k:v for k,v in d['features'][0]['properties'].items()if 'FR'in k})
