from pathlib import Path
import json,urllib.request,zipfile
r=Path(__file__).resolve().parents[1]/'test-output/library-collections';meta=json.loads((r/'osbooks-biology-bundle.json').read_text());sha=meta['commit']
out=r/'osbooks-biology-bundle.complete.zip';partial=out.with_suffix('.part')
url=f'https://codeload.github.com/openstax/osbooks-biology-bundle/zip/{sha}'
with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Ecrinator/0.9 local educational catalogue'}),timeout=120)as source,partial.open('wb')as dest:
 count=0
 while chunk:=source.read(1024*1024):
  count+=len(chunk)
  if count>2*1024**3:raise ValueError('Archive exceeds 2 GiB bound')
  dest.write(chunk)
  if count%(100*1024*1024)==0:print('DOWNLOADED MiB',count//1024//1024,flush=True)
assert zipfile.is_zipfile(partial)
partial.replace(r/'osbooks-biology-bundle.zip')
print('COMPLETE',count,flush=True)
