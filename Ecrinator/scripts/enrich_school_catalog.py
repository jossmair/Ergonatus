"""Restore source lesson titles for more reliable subject indexing."""
from pathlib import Path
from zipfile import ZipFile
from defusedxml import ElementTree as ET
import json,posixpath
root=Path(__file__).resolve().parents[1];out=root/'assets/library';source=root/'test-output/library-collections'
catalog=json.loads((out/'catalog.json').read_text(encoding='utf-8'))
lookup={(e['source_url'].split('/')[4],e['source_url'].split('/blob/',1)[-1].split('/',1)[-1]):e for e in catalog if e['id'].startswith('os-')}
def local(tag):return tag.rsplit('}',1)[-1]
count=0
seen=set()
for repo in ['osbooks-biology-bundle','osbooks-anatomy-physiology','osbooks-university-physics-bundle']:
 with ZipFile(source/(repo+'.zip'))as z:
  for name in sorted(z.namelist()):
   if not name.endswith('/index.cnxml'):continue
   tree=ET.fromstring(z.read(name));title=next((' '.join(n.itertext()).strip()for n in tree if local(n.tag)=='title'),'')
   for n in tree.iter():
    if local(n.tag)!='image' or not n.attrib.get('src'):continue
    path=posixpath.normpath(posixpath.join(posixpath.dirname(name),n.attrib['src'])).split('/',1)[-1]
    key=(repo,path)
    if key in lookup and key not in seen:lookup[key]['module_title']=title;seen.add(key);count+=1
(out/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8');print('Source lesson titles:',count)
