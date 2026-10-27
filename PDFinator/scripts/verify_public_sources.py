"""Verify public sources and their downloaded archive without credentials."""
from pathlib import Path
import hashlib, json, urllib.request
ROOT = Path(__file__).resolve().parents[1]
report = json.loads((ROOT/'release/source-verification.json').read_text())
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'PDFinator-public-source-check'}),timeout=120)
def api(path):
    with get('https://api.github.com/repos/jossmair/PDFinator'+path) as response:
        return json.load(response)
commit = api('/git/commits/'+report['source_commit'])
tree = api('/git/trees/'+commit['tree']['sha']+'?recursive=1')
assert not tree['truncated']
files = {n['path']:n for n in tree['tree'] if n['type']=='blob'}
blocked={'.p12','.pfx','.pem','.key','.jks','.keystore'}
assert not [n for n in files if Path(n).suffix.lower() in blocked]
assert all(n in files for n in ['src/main.rs','src/document.rs','Cargo.toml','Cargo.lock','BUILDING.md','LICENSE-MIT','LICENSE-APACHE'])
expected=json.loads((ROOT/'release-verification-100.json').read_text())['sources']
for name in expected:
    data=(ROOT/name).read_bytes()
    assert files[name]['sha']==hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),name
url='https://github.com/jossmair/PDFinator/releases/download/v1.0.0/PDFinator-1.0.0-sources.zip'
digest=hashlib.sha256()
size=0
with get(url) as response:
    while chunk:=response.read(1024*1024):
        digest.update(chunk)
        size+=len(chunk)
assert digest.hexdigest()==report['source_zip_sha256'] and size==report['source_zip_bytes']
release=api('/releases/tags/v1.0.0')
assert '<!-- PDFINATOR_SOURCES -->' in release['body']
result={'public_sources_verified':True,'public_source_files':len(files),'source_commit':report['source_commit'],
        'source_archive_downloaded':True,'archive_sha256':digest.hexdigest(),'archive_bytes':size,'authentication_used':False}
(ROOT/'release/public-sources-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
